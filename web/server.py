"""本地前台服务：只读访问镜像库，提供 JSON API 与静态页面。

* 只监听 127.0.0.1；连接以 query_only 打开，不向镜像库写入。
* 每个请求独立连接（线程安全）；人员、字典、客户对照等小表缓存在内存，镜像更新后自动重载。
* 客户关联：业务表的 cu_sn 为 "[id:N]" 或客户编号 sn；出库单 cu_sn 为纯数字客户 id。
* 人员：contract.who / gathering_note.who 为姓名；customer.owner / gathering.who / libout.who 为 part；action.who 为 ",M1,M2," 形式。

接口（均为 GET，返回 JSON）：
    /api/meta                       同步状态、字典、人员、可选年份
    /api/overview?year=             经营总览
    /api/orders?...                 订单列表        /api/orders/<id>    订单详情
    /api/customers?...              客户列表        /api/customers/<id> 客户详情
    /api/receivables?...            计划回款（应收）
    /api/receipts?...               回款记录
    /api/actions?...                工作日志（行动记录）
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, urlparse

from sync.store import col_name

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = logging.getLogger("xtools.web")

CANCELLED = "3"  # contract.status 意外中止：金额统计时剔除
OPEN_PLAN = ("2", "4")  # gathering.status 未回 / 部分回款
DICT_FIELDS = {
    "contract": ["status", "type", "confirm", "st_send", "pay_mode", "payment"],
    "gathering": ["status"],
    "gathering_note": ["type", "ctype", "invoice"],
    "action": ["type", "cale"],
    "customer": ["life", "type", "cu_status", "cu_from", "industry", "rala_rating", "employees"],
    "sendgoods": ["status", "sntype"],
    "contact": ["contype"],
}
_ID_KEY = re.compile(r"^\[id:(\d+)\]$")


def money(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(value: Any) -> bool:
    """形如 YYYY-MM-DD（不判断年份是否合理；年份异常由 Query.date_flag 标记）。"""
    return isinstance(value, str) and bool(_DATE_RE.match(value))


class Lookups:
    """内存中的小表：人员、字典、客户对照、产品、字段中文名。"""

    def __init__(self, conn: sqlite3.Connection):
        self.users: Dict[str, Dict[str, Any]] = {}
        for r in conn.execute("SELECT part, name, status, dept FROM crm_user WHERE _deleted_at IS NULL ORDER BY id"):
            self.users[r["part"]] = {"part": r["part"], "name": r["name"] or r["part"], "active": str(r["status"]) == "0", "dept": r["dept"]}
        self.dicts: Dict[Tuple[str, str], Dict[str, str]] = {}
        for r in conn.execute("SELECT dt, field, key, value FROM dictionaries WHERE dt <> 'user'"):
            self.dicts.setdefault((r["dt"], r["field"]), {})[str(r["key"])] = r["value"] or ""
        self.field_names: Dict[str, Dict[str, str]] = {}
        for r in conn.execute("SELECT dt, field, name FROM field_names"):
            self.field_names.setdefault(r["dt"], {})[r["field"]] = r["name"] or ""
        self.customers: Dict[int, Dict[str, Any]] = {}
        self.key_to_id: Dict[str, int] = {}
        for r in conn.execute("SELECT id, sn, cu_name, m_name, owner, life, type, cu_status, city FROM customer WHERE _deleted_at IS NULL"):
            self.customers[r["id"]] = dict(r)
            if r["sn"]:
                self.key_to_id[r["sn"]] = r["id"]
        self.products: Dict[str, Dict[str, Any]] = {}
        for r in conn.execute("SELECT sn, name, model, unit, class FROM product WHERE _deleted_at IS NULL AND sn <> ''"):
            self.products[r["sn"]] = dict(r)
        self.salespeople: List[Dict[str, Any]] = [
            {"name": r["who"], "orders": r["n"]}
            for r in conn.execute("SELECT who, COUNT(*) n FROM contract WHERE _deleted_at IS NULL AND who <> '' GROUP BY who ORDER BY n DESC")
        ]
        self.loaded_at = time.time()

    # ---- 解析
    def customer_id(self, key: Any, numeric_is_id: bool = False) -> Optional[int]:
        if not key:
            return None
        key = str(key).strip()
        m = _ID_KEY.match(key)
        if m:
            return int(m.group(1))
        if numeric_is_id and key.isdigit():
            return int(key)
        return self.key_to_id.get(key)

    def customer(self, key: Any, numeric_is_id: bool = False) -> Optional[Dict[str, Any]]:
        cid = self.customer_id(key, numeric_is_id)
        if cid is None:
            return {"id": None, "name": str(key), "owner": None} if key else None
        c = self.customers.get(cid)
        if not c:
            return {"id": cid, "name": f"[已删除 {cid}]", "owner": None}
        return {"id": cid, "name": c["cu_name"] or c["m_name"] or f"[id:{cid}]", "owner": self.user_name(c["owner"]), "life": self.text("customer", "life", c["life"])}

    def user_name(self, part: Any) -> str:
        if part is None:
            return ""
        part = str(part).strip()
        u = self.users.get(part)
        return u["name"] if u else part

    def names_from_codes(self, value: Any) -> List[str]:
        """action.who：",M1,M2," → 姓名列表；单个 part 或姓名也兼容。"""
        if not value:
            return []
        parts = [p for p in str(value).split(",") if p.strip()]
        return [self.user_name(p) for p in parts] or [str(value)]

    def text(self, dt_name: str, field: str, key: Any) -> str:
        if key is None or key == "":
            return ""
        return self.dicts.get((dt_name, field), {}).get(str(key), str(key))

    def part_to_name(self, part: str) -> str:
        return self.user_name(part)

    def dict_options(self) -> Dict[str, List[Dict[str, str]]]:
        out: Dict[str, List[Dict[str, str]]] = {}
        for dt_name, fields in DICT_FIELDS.items():
            for f in fields:
                items = self.dicts.get((dt_name, f), {})
                out[f"{dt_name}.{f}"] = [{"key": k, "value": v} for k, v in items.items()]
        return out


class Mirror:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._lookups: Optional[Lookups] = None
        self._stamp: Any = None
        self._checked = 0.0

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = 1")
        return conn

    def stamp(self, conn: sqlite3.Connection) -> Any:
        row = conn.execute("SELECT MAX(last_run_at), SUM(total_rows) FROM sync_state").fetchone()
        return (row[0], row[1]) if row else None

    def lookups(self, conn: sqlite3.Connection) -> Lookups:
        with self._lock:
            now = time.time()
            if self._lookups is None or now - self._checked > 20:
                self._checked = now
                stamp = self.stamp(conn)
                if self._lookups is None or stamp != self._stamp:
                    t0 = time.time()
                    self._lookups = Lookups(conn)
                    self._stamp = stamp
                    logger.info("已加载对照表：客户 %d、人员 %d、产品 %d（%.2fs）", len(self._lookups.customers), len(self._lookups.users),
                                len(self._lookups.products), time.time() - t0)
            return self._lookups


# ---------------------------------------------------------------------- 查询
class Query:
    def __init__(self, conn: sqlite3.Connection, lk: Lookups, params: Dict[str, str]):
        self.conn = conn
        self.lk = lk
        self.p = params
        self.today = dt.date.today()

    # ---- 参数
    def get(self, name: str, default: str = "") -> str:
        return (self.p.get(name) or default).strip()

    def page(self) -> Tuple[int, int, int]:
        size = min(max(_int(self.get("size"), 50), 1), 500)
        page = max(_int(self.get("page"), 1), 1)
        return page, size, (page - 1) * size

    def customer_keys(self, cid: int) -> List[str]:
        keys = [f"[id:{cid}]"]
        c = self.lk.customers.get(cid)
        if c and c.get("sn"):
            keys.append(c["sn"])
        return keys

    def customer_clause(self, alias: str, clauses: List[str], args: List[Any], numeric_is_id: bool = False) -> None:
        cid = _int(self.get("customer_id"), 0)
        if cid:
            keys = [str(cid)] if numeric_is_id else self.customer_keys(cid)
            clauses.append(f"{alias}.cu_sn IN ({','.join('?' * len(keys))})")
            args.extend(keys)

    def name_search_clause(self, alias: str, q: str, args: List[Any]) -> str:
        like = f"%{q}%"
        args.extend([like, like, like, like])
        return (f"({alias}.cu_sn IN (SELECT '[id:' || id || ']' FROM customer WHERE cu_name LIKE ? OR m_name LIKE ?) "
                f"OR {alias}.cu_sn IN (SELECT sn FROM customer WHERE sn <> '' AND (cu_name LIKE ? OR m_name LIKE ?)))")

    def date_clause(self, alias: str, clauses: List[str], args: List[Any], col: str = "date") -> None:
        if self.get("from"):
            clauses.append(f"{alias}.{col} >= ?")
            args.append(self.get("from"))
        if self.get("to"):
            clauses.append(f"{alias}.{col} <= ?")
            args.append(self.get("to"))

    def rows(self, sql: str, args: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(sql, tuple(args))]

    def one(self, sql: str, args: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
        r = self.conn.execute(sql, tuple(args)).fetchone()
        return dict(r) if r else None

    # ---- 元数据
    def meta(self) -> Dict[str, Any]:
        states = self.rows("SELECT dt, total_rows, last_run_at, last_status, last_full_at, last_error FROM sync_state ORDER BY total_rows DESC")
        years = self.one("SELECT MIN(substr(date,1,4)) y0, MAX(substr(date,1,4)) y1 FROM contract WHERE _deleted_at IS NULL AND date LIKE '20__-__-__'") or {}
        y0, y1 = _int(years.get("y0"), self.today.year), _int(years.get("y1"), self.today.year)
        return {
            "today": self.today.isoformat(),
            "synced_at": max([s["last_run_at"] or "" for s in states] or [""]),
            "tables": states,
            "years": list(range(max(y0, 2000), max(y1, self.today.year) + 1))[::-1],
            "dicts": self.lk.dict_options(),
            "users": sorted(self.lk.users.values(), key=lambda u: (not u["active"], u["name"])),
            "salespeople": self.lk.salespeople,
        }

    # ---- 总览
    def overview(self) -> Dict[str, Any]:
        year = _int(self.get("year"), self.today.year)
        y_from, y_to = f"{year}-01-01", f"{year + 1}-01-01"
        py_from = f"{year - 1}-01-01"
        base = "FROM contract o WHERE o._deleted_at IS NULL AND o.status <> ?"
        month = self.today.strftime("%Y-%m")
        ytd_to = self.today.isoformat()
        ytd_prev_to = self.today.replace(year=self.today.year - 1).isoformat() if not (self.today.month == 2 and self.today.day == 29) else f"{self.today.year - 1}-02-28"

        def agg(sql: str, args: Sequence[Any]) -> Dict[str, Any]:
            r = self.one(sql, args) or {}
            return {"count": r.get("n") or 0, "amount": money(r.get("a"))}

        kpi = {
            "month_orders": agg(f"SELECT COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND substr(o.date,1,7) = ?", [CANCELLED, month]),
            "ytd_orders": agg(f"SELECT COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date <= ?", [CANCELLED, f"{self.today.year}-01-01", ytd_to]),
            "ytd_orders_prev": agg(f"SELECT COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date <= ?", [CANCELLED, f"{self.today.year - 1}-01-01", ytd_prev_to]),
            "month_receipts": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND substr(date,1,7) = ?", [month]),
            "ytd_receipts": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? AND date <= ?", [f"{self.today.year}-01-01", ytd_to]),
            "ytd_receipts_prev": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? AND date <= ?", [f"{self.today.year - 1}-01-01", ytd_prev_to]),
            "open_orders": agg("SELECT COUNT(*) n, SUM(CAST(sum AS REAL)) a FROM contract WHERE _deleted_at IS NULL AND status = '1'", []),
            "open_plans": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering WHERE _deleted_at IS NULL AND status IN ('2','4')", []),
            "overdue_plans": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering WHERE _deleted_at IS NULL AND status IN ('2','4') AND date < ?", [ytd_to]),
        }
        monthly: Dict[str, Dict[str, Any]] = {}
        for r in self.rows(f"SELECT substr(o.date,1,7) m, COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date < ? GROUP BY m", [CANCELLED, py_from, y_to]):
            monthly.setdefault(r["m"], {})["orders"] = {"count": r["n"], "amount": money(r["a"])}
        for r in self.rows("SELECT substr(date,1,7) m, COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? AND date < ? GROUP BY m", [py_from, y_to]):
            monthly.setdefault(r["m"], {})["receipts"] = {"count": r["n"], "amount": money(r["a"])}
        series = []
        for yy in (year - 1, year):
            for mm in range(1, 13):
                key = f"{yy}-{mm:02d}"
                d = monthly.get(key, {})
                series.append({"month": key, "orders": d.get("orders", {"count": 0, "amount": 0.0}), "receipts": d.get("receipts", {"count": 0, "amount": 0.0})})
        top_customers = [
            {"customer": self.lk.customer(r["cu_sn"]), "count": r["n"], "amount": money(r["a"])}
            for r in self.rows(f"SELECT o.cu_sn, COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date < ? GROUP BY o.cu_sn ORDER BY a DESC LIMIT 10", [CANCELLED, y_from, y_to])
        ]
        top_sales = [
            {"name": r["who"], "count": r["n"], "amount": money(r["a"])}
            for r in self.rows(f"SELECT o.who, COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date < ? GROUP BY o.who ORDER BY a DESC LIMIT 10", [CANCELLED, y_from, y_to])
        ]
        top_products = []
        for r in self.rows(
            "SELECT g.prod, MAX(g.prod_name) pn, SUM(CAST(g.sum AS REAL)) a, SUM(CAST(g.amount AS REAL)) q, COUNT(DISTINCT g.contract_id) n "
            "FROM contract_goods g JOIN contract o ON o.id = g.contract_id "
            "WHERE o._deleted_at IS NULL AND o.status <> ? AND o.date >= ? AND o.date < ? GROUP BY g.prod ORDER BY a DESC LIMIT 10",
            [CANCELLED, y_from, y_to],
        ):
            prod = self.lk.products.get(r["prod"] or "", {})
            top_products.append({"sn": r["prod"], "name": prod.get("name") or r["pn"] or r["prod"], "model": prod.get("model") or "", "amount": money(r["a"]), "quantity": r["q"], "orders": r["n"]})
        status_mix = [
            {"status": r["status"], "text": self.lk.text("contract", "status", r["status"]), "count": r["n"], "amount": money(r["a"])}
            for r in self.rows("SELECT status, COUNT(*) n, SUM(CAST(sum AS REAL)) a FROM contract WHERE _deleted_at IS NULL AND date >= ? AND date < ? GROUP BY status ORDER BY n DESC", [y_from, y_to])
        ]
        recent = [self.order_row(r) for r in self.enrich_orders(self.rows(self.ORDER_SELECT + " WHERE o._deleted_at IS NULL ORDER BY o.date DESC, o.id DESC LIMIT 8"))]
        year_total = agg(f"SELECT COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date < ?", [CANCELLED, y_from, y_to])
        year_receipts = agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? AND date < ?", [y_from, y_to])
        return {"year": year, "kpi": kpi, "monthly": series, "year_total": year_total, "year_receipts": year_receipts,
                "top_customers": top_customers, "top_sales": top_sales, "top_products": top_products, "status_mix": status_mix, "recent_orders": recent}

    # ---- 订单
    ORDER_SELECT = "SELECT o.* FROM contract o"

    def enrich_orders(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为一页订单补上已回款金额与发货单数（先分页再关联，避免对全表逐行做子查询）。"""
        if not rows:
            return rows
        keys = [str(r["id"]) for r in rows] + [r.get("no_") or "" for r in rows]
        marks = ",".join("?" * len(keys))
        received: Dict[str, float] = {}
        for r in self.conn.execute(f"SELECT co_id, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND co_id IN ({marks}) GROUP BY co_id", keys):
            received[str(r["co_id"])] = money(r["a"])
        shipments: Dict[str, int] = {}
        for r in self.conn.execute(f"SELECT co_id, COUNT(*) n FROM sendgoods WHERE _deleted_at IS NULL AND co_id IN ({marks}) GROUP BY co_id", keys):
            shipments[str(r["co_id"])] = r["n"]
        for row in rows:
            k1, k2 = str(row["id"]), row.get("no_") or ""
            row["received"] = round(received.get(k1, 0.0) + (received.get(k2, 0.0) if k2 != k1 else 0.0), 2)
            row["shipments"] = shipments.get(k1, 0) + (shipments.get(k2, 0) if k2 != k1 else 0)
        return rows

    def order_row(self, r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": r["id"], "no": r.get("no_"), "date": r.get("date"), "end_date": r.get("end_date"), "subject": r.get("subject"),
            "customer": self.lk.customer(r.get("cu_sn")), "amount": money(r.get("sum")), "money_type": r.get("money_type") or "RMB",
            "status": r.get("status"), "status_text": self.lk.text("contract", "status", r.get("status")),
            "confirm_text": self.lk.text("contract", "confirm", r.get("confirm")),
            "st_send": r.get("st_send"), "st_send_text": self.lk.text("contract", "st_send", r.get("st_send")),
            "type_text": self.lk.text("contract", "type", r.get("type")), "who": r.get("who"),
            "received": money(r.get("received")), "shipments": r.get("shipments") or 0, "memo": r.get("memo"),
            "payment_text": self.lk.text("contract", "payment", r.get("payment")), "pay_mode_text": self.lk.text("contract", "pay_mode", r.get("pay_mode")),
            "contact_name": r.get("name"), "mphone": r.get("mphone"), "addr": r.get("addr"),
        }

    def orders(self) -> Dict[str, Any]:
        clauses, args = ["o._deleted_at IS NULL"], []
        q = self.get("q")
        if q:
            args.extend([f"%{q}%", f"%{q}%"])
            clauses.append(f"(o.no_ LIKE ? OR o.subject LIKE ? OR {self.name_search_clause('o', q, args)})")
        self.customer_clause("o", clauses, args)
        if self.get("who"):
            clauses.append("o.who = ?")
            args.append(self.lk.part_to_name(self.get("who")))
        if self.get("status"):
            clauses.append("o.status = ?")
            args.append(self.get("status"))
        if self.get("type"):
            clauses.append("o.type = ?")
            args.append(self.get("type"))
        if self.get("st_send"):
            clauses.append("o.st_send = ?")
            args.append(self.get("st_send"))
        self.date_clause("o", clauses, args)
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = self.one(f"SELECT COUNT(*) n, SUM(CASE WHEN o.status <> '3' THEN CAST(o.sum AS REAL) ELSE 0 END) a FROM contract o{where}", args) or {}
        sort = {"amount": "CAST(o.sum AS REAL) DESC, o.id DESC", "date_asc": "o.date ASC, o.id ASC"}.get(self.get("sort"), "o.date DESC, o.id DESC")
        rows = self.enrich_orders(self.rows(f"{self.ORDER_SELECT}{where} ORDER BY {sort} LIMIT ? OFFSET ?", [*args, size, offset]))
        return {"total": total.get("n") or 0, "amount": money(total.get("a")), "page": page, "size": size, "rows": [self.order_row(r) for r in rows]}

    def order_detail(self, oid: int) -> Optional[Dict[str, Any]]:
        r = self.one(self.ORDER_SELECT + " WHERE o.id = ?", [oid])
        if not r:
            return None
        order = self.order_row(self.enrich_orders([r])[0])
        goods = []
        for g in self.rows("SELECT * FROM contract_goods WHERE contract_id = ? ORDER BY _seq", [oid]):
            prod = self.lk.products.get(g.get("prod") or "", {})
            goods.append({"prod": g.get("prod"), "name": prod.get("name") or g.get("prod_name"), "model": prod.get("model") or g.get("model"),
                          "unit": prod.get("unit"), "sku": g.get("sku"), "batchnum": g.get("batchnum"), "amount": g.get("amount"), "unit_price": money(g.get("un_price")),
                          "sum": money(g.get("sum")), "tax_rate": g.get("tax_rate"), "tax_money": money(g.get("tax_money")), "memo": g.get("memo")})
        receipts = [self.receipt_row(x) for x in self.rows(
            "SELECT * FROM gathering_note WHERE _deleted_at IS NULL AND (co_id = ? OR co_id = ?) ORDER BY date DESC, id DESC", [str(oid), r.get("no_") or ""])]
        plans = [self.plan_row(x) for x in self.rows(
            "SELECT * FROM gathering WHERE _deleted_at IS NULL AND (co_sn = ? OR co_sn = ?) ORDER BY date, serial", [r.get("no_") or "", str(oid)])]
        shipments = []
        for s in self.rows("SELECT s.*, (SELECT COUNT(*) FROM sendgoods_items i WHERE i.sendgoods_id = s.id) items FROM sendgoods s WHERE s._deleted_at IS NULL AND (s.co_id = ? OR s.co_id = ?) ORDER BY s.date DESC, s.id DESC", [str(oid), r.get("no_") or ""]):
            shipments.append({"id": s["id"], "date": s.get("date"), "sn": s.get("sn"), "status_text": self.lk.text("sendgoods", "status", s.get("status")), "who": s.get("who"),
                              "sendcomp": s.get("sendcomp"), "sendcode": s.get("sendcode"), "name": s.get("name"), "addr": s.get("addr"), "items": s.get("items") or 0, "memo": s.get("memo")})
        libouts = []
        for x in self.rows("SELECT l.*, (SELECT COUNT(*) FROM libout_items i WHERE i.libout_id = l.id) items FROM libout l WHERE l._deleted_at IS NULL AND l.co_sn = ? ORDER BY l.date DESC, l.id DESC", [r.get("no_") or ""]):
            libouts.append({"id": x["id"], "date": x.get("date"), "title": x.get("title"), "libname": x.get("libname"), "who": self.lk.user_name(x.get("who")), "items": x.get("items") or 0, "memo": x.get("memo")})
        actions = [self.action_row(a) for a in self.rows(
            "SELECT a.*, k.name AS contact_name FROM action a LEFT JOIN contact k ON k.id = CAST(a.con_id AS INTEGER) WHERE a._deleted_at IS NULL AND a.co_id = ? ORDER BY a.date DESC, a.id DESC LIMIT 30", [str(oid)])]
        extras = self.raw_extras("contract", oid, set(r.keys()) | {"goods"})
        return {"order": order, "goods": goods, "receipts": receipts, "plans": plans, "shipments": shipments, "libouts": libouts, "actions": actions, "extras": extras}

    def raw_extras(self, dt_name: str, rid: int, skip: set) -> List[Dict[str, str]]:
        """原始 JSON 中未进规范化表的非空字段（自定义字段 j1… 等），配字段中文名。"""
        r = self.one("SELECT data FROM raw_records WHERE dt = ? AND id = ?", [dt_name, rid])
        if not r:
            return []
        names = self.lk.field_names.get(dt_name, {})
        out = []
        for k, v in json.loads(r["data"]).items():
            if k in skip or col_name(k) in skip or v in (None, "", "0", 0, [], {}) or isinstance(v, (list, dict)):
                continue
            out.append({"key": k, "name": names.get(k) or k, "value": str(v)})
        return out

    # ---- 客户
    CUSTOMER_LIST_SQL = """
        WITH o AS (SELECT cu_sn, COUNT(*) n, SUM(CAST(sum AS REAL)) amt, MAX(date) last_date FROM contract WHERE _deleted_at IS NULL AND status <> '3' GROUP BY cu_sn),
             r AS (SELECT cu_sn, SUM(CAST(money AS REAL)) amt, MAX(date) last_date FROM gathering_note WHERE _deleted_at IS NULL GROUP BY cu_sn)
        SELECT c.id, c.sn, c.cu_name, c.m_name, c.owner, c.life, c.type, c.cu_status, c.city, c.state, c.industry, c.creatdate, c.moddate, c.tel, c.address,
               COALESCE(o1.n, 0) + COALESCE(o2.n, 0) AS orders,
               COALESCE(o1.amt, 0) + COALESCE(o2.amt, 0) AS order_amount,
               COALESCE(o1.last_date, o2.last_date) AS last_order,
               COALESCE(r1.amt, 0) + COALESCE(r2.amt, 0) AS receipts,
               (SELECT COUNT(*) FROM contact k WHERE k.customer_id = c.id) AS contacts
        FROM customer c
        LEFT JOIN o o1 ON o1.cu_sn = '[id:' || c.id || ']'
        LEFT JOIN o o2 ON c.sn <> '' AND o2.cu_sn = c.sn
        LEFT JOIN r r1 ON r1.cu_sn = '[id:' || c.id || ']'
        LEFT JOIN r r2 ON c.sn <> '' AND r2.cu_sn = c.sn
    """

    def customer_row(self, c: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": c["id"], "sn": c.get("sn"), "name": c.get("cu_name") or c.get("m_name"), "short": c.get("m_name"),
            "owner": self.lk.user_name(c.get("owner")), "owner_part": c.get("owner"),
            "life_text": self.lk.text("customer", "life", c.get("life")), "type_text": self.lk.text("customer", "type", c.get("type")),
            "stage_text": self.lk.text("customer", "cu_status", c.get("cu_status")), "industry_text": self.lk.text("customer", "industry", c.get("industry")),
            "city": c.get("city"), "created": c.get("creatdate"), "modified": c.get("moddate"), "tel": c.get("tel"), "address": c.get("address"),
            "orders": c.get("orders") or 0, "order_amount": money(c.get("order_amount")), "last_order": c.get("last_order"),
            "receipts": money(c.get("receipts")), "contacts": c.get("contacts") or 0,
        }

    def customers(self) -> Dict[str, Any]:
        clauses, args = ["c._deleted_at IS NULL"], []
        q = self.get("q")
        if q:
            clauses.append("(c.cu_name LIKE ? OR c.m_name LIKE ? OR c.sn = ? OR c.id = ?)")
            args.extend([f"%{q}%", f"%{q}%", q, _int(q, -1)])
        for col in ("owner", "life", "type", "cu_status"):
            if self.get(col):
                clauses.append(f"c.{col} = ?")
                args.append(self.get(col))
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = (self.one(f"SELECT COUNT(*) n FROM customer c{where}", args) or {}).get("n") or 0
        sort = {
            "amount": "order_amount DESC, c.id DESC", "name": "c.cu_name COLLATE NOCASE ASC", "created": "c.creatdate DESC, c.id DESC",
            "orders": "orders DESC, c.id DESC",
        }.get(self.get("sort"), "last_order IS NULL, last_order DESC, c.id DESC")
        rows = self.rows(f"{self.CUSTOMER_LIST_SQL}{where} ORDER BY {sort} LIMIT ? OFFSET ?", [*args, size, offset])
        return {"total": total, "page": page, "size": size, "rows": [self.customer_row(c) for c in rows]}

    def customer_detail(self, cid: int) -> Optional[Dict[str, Any]]:
        c = self.one(self.CUSTOMER_LIST_SQL + " WHERE c.id = ?", [cid])
        if not c:
            return None
        keys = self.customer_keys(cid)
        marks = ",".join("?" * len(keys))
        contacts = [
            {"id": k["id"], "name": k.get("name"), "headship": k.get("headship"), "department": k.get("department"), "mphone": k.get("mphone"), "phone": k.get("phone"),
             "email": k.get("email"), "weixin": k.get("weixin"), "remark": k.get("remark")}
            for k in self.rows("SELECT * FROM contact WHERE customer_id = ? ORDER BY _seq", [cid])
        ]
        orders = [self.order_row(r) for r in self.enrich_orders(self.rows(f"{self.ORDER_SELECT} WHERE o._deleted_at IS NULL AND o.cu_sn IN ({marks}) ORDER BY o.date DESC, o.id DESC LIMIT 50", keys))]
        receipts = [self.receipt_row(x) for x in self.rows(f"SELECT * FROM gathering_note WHERE _deleted_at IS NULL AND cu_sn IN ({marks}) ORDER BY date DESC, id DESC LIMIT 50", keys)]
        plans = [self.plan_row(x) for x in self.rows(f"SELECT * FROM gathering WHERE _deleted_at IS NULL AND status IN ('2','4') AND cu_sn IN ({marks}) ORDER BY date", keys)]
        actions = [self.action_row(a) for a in self.rows(
            f"SELECT a.*, k.name AS contact_name FROM action a LEFT JOIN contact k ON k.id = CAST(a.con_id AS INTEGER) WHERE a._deleted_at IS NULL AND a.cu_sn IN ({marks}) ORDER BY a.date DESC, a.id DESC LIMIT 50", keys)]
        yearly = [
            {"year": r["y"], "count": r["n"], "amount": money(r["a"])}
            for r in self.rows(f"SELECT substr(date,1,4) y, COUNT(*) n, SUM(CAST(sum AS REAL)) a FROM contract WHERE _deleted_at IS NULL AND status <> '3' AND cu_sn IN ({marks}) GROUP BY y ORDER BY y", keys)
        ]
        extras = self.raw_extras("customer", cid, set(c.keys()) | {"contact", "cu_name", "m_name", "sn", "owner", "life", "type", "cu_status", "city", "state", "industry", "creatdate", "moddate", "tel", "address"})
        return {"customer": self.customer_row(c), "contacts": contacts, "orders": orders, "receipts": receipts, "open_plans": plans, "actions": actions, "yearly": yearly, "extras": extras}

    # ---- 应收（计划回款）
    def plan_row(self, g: Dict[str, Any]) -> Dict[str, Any]:
        overdue = 0
        if str(g.get("status")) in OPEN_PLAN and _valid_date(g.get("date")):
            try:
                overdue = (self.today - dt.date.fromisoformat(g["date"])).days
            except ValueError:
                overdue = 0
        return {
            "id": g["id"], "date": g.get("date"), "serial": g.get("serial"), "amount": money(g.get("money")),
            "status": g.get("status"), "status_text": self.lk.text("gathering", "status", g.get("status")),
            "who": self.lk.user_name(g.get("who")), "customer": self.lk.customer(g.get("cu_sn")), "order_no": g.get("co_sn"),
            "order_id": self.order_id_by_no(g.get("co_sn")), "memo": g.get("memo"), "overdue_days": max(overdue, 0),
        }

    _no_cache: Dict[str, Optional[int]] = {}

    def order_id_by_no(self, no: Any) -> Optional[int]:
        if not no:
            return None
        no = str(no)
        if no.isdigit():
            return int(no)
        if no not in self._no_cache:
            r = self.one("SELECT id FROM contract WHERE no_ = ?", [no])
            self._no_cache[no] = r["id"] if r else None
        return self._no_cache[no]

    def receivables(self) -> Dict[str, Any]:
        clauses, args = ["g._deleted_at IS NULL"], []
        status = self.get("status", "open")
        if status == "open":
            clauses.append("g.status IN ('2','4')")
        elif status == "overdue":
            clauses.append("g.status IN ('2','4') AND g.date < ?")
            args.append(self.today.isoformat())
        elif status == "done":
            clauses.append("g.status = '1'")
        if self.get("who"):
            clauses.append("g.who = ?")
            args.append(self.get("who"))
        self.customer_clause("g", clauses, args)
        self.date_clause("g", clauses, args)
        q = self.get("q")
        if q:
            args.append(f"%{q}%")
            clauses.append(f"(g.co_sn LIKE ? OR {self.name_search_clause('g', q, args)})")
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = self.one(f"SELECT COUNT(*) n, SUM(CAST(g.money AS REAL)) a FROM gathering g{where}", args) or {}
        today = self.today.isoformat()
        aging = self.one(
            "SELECT "
            "SUM(CASE WHEN g.date >= ? THEN CAST(g.money AS REAL) ELSE 0 END) AS not_due, "
            "SUM(CASE WHEN g.date < ? AND julianday(?) - julianday(g.date) <= 30 THEN CAST(g.money AS REAL) ELSE 0 END) AS d30, "
            "SUM(CASE WHEN julianday(?) - julianday(g.date) > 30 AND julianday(?) - julianday(g.date) <= 90 THEN CAST(g.money AS REAL) ELSE 0 END) AS d90, "
            "SUM(CASE WHEN julianday(?) - julianday(g.date) > 90 AND julianday(?) - julianday(g.date) <= 365 THEN CAST(g.money AS REAL) ELSE 0 END) AS d365, "
            "SUM(CASE WHEN julianday(?) - julianday(g.date) > 365 THEN CAST(g.money AS REAL) ELSE 0 END) AS d365p "
            f"FROM gathering g{where} AND g.status IN ('2','4')",
            [today] * 8 + list(args),
        ) or {}
        by_who = [
            {"who": self.lk.user_name(r["who"]), "part": r["who"], "count": r["n"], "amount": money(r["a"]), "overdue": money(r["od"])}
            for r in self.rows(
                f"SELECT g.who, COUNT(*) n, SUM(CAST(g.money AS REAL)) a, SUM(CASE WHEN g.date < ? THEN CAST(g.money AS REAL) ELSE 0 END) od FROM gathering g{where} AND g.status IN ('2','4') GROUP BY g.who ORDER BY a DESC LIMIT 15",
                [today, *args])
        ]
        sort = {"amount": "CAST(g.money AS REAL) DESC", "date_desc": "g.date DESC, g.id DESC"}.get(self.get("sort"), "g.date ASC, g.id ASC")
        rows = self.rows(f"SELECT g.* FROM gathering g{where} ORDER BY {sort} LIMIT ? OFFSET ?", [*args, size, offset])
        return {"total": total.get("n") or 0, "amount": money(total.get("a")), "page": page, "size": size,
                "aging": {k: money(aging.get(k)) for k in ("not_due", "d30", "d90", "d365", "d365p")}, "by_who": by_who, "rows": [self.plan_row(g) for g in rows]}

    # ---- 回款记录
    def receipt_row(self, n: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": n["id"], "date": n.get("date"), "amount": money(n.get("money")), "money_type": n.get("money_type") or "RMB",
            "type_text": self.lk.text("gathering_note", "type", n.get("type")), "ctype_text": self.lk.text("gathering_note", "ctype", n.get("ctype")),
            "invoice_text": self.lk.text("gathering_note", "invoice", n.get("invoice")), "serial": n.get("serial"),
            "who": n.get("who"), "owner": n.get("owner"), "customer": self.lk.customer(n.get("cu_sn")),
            "order_id": _int(n.get("co_id"), 0) or None, "order_no": n.get("order_no"), "memo": n.get("memo"),
        }

    def receipts(self) -> Dict[str, Any]:
        clauses, args = ["n._deleted_at IS NULL"], []
        if self.get("who"):
            clauses.append("n.who = ?")
            args.append(self.lk.part_to_name(self.get("who")))
        self.customer_clause("n", clauses, args)
        self.date_clause("n", clauses, args)
        if self.get("type"):
            clauses.append("n.type = ?")
            args.append(self.get("type"))
        q = self.get("q")
        if q:
            args.extend([f"%{q}%", f"%{q}%"])
            clauses.append(f"(n.memo LIKE ? OR n.co_id IN (SELECT CAST(id AS TEXT) FROM contract WHERE no_ LIKE ?) OR {self.name_search_clause('n', q, args)})")
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = self.one(f"SELECT COUNT(*) n, SUM(CAST(n.money AS REAL)) a FROM gathering_note n{where}", args) or {}
        by_month = [{"month": r["m"], "count": r["n"], "amount": money(r["a"])} for r in self.rows(
            f"SELECT substr(n.date,1,7) m, COUNT(*) n, SUM(CAST(n.money AS REAL)) a FROM gathering_note n{where} GROUP BY m ORDER BY m DESC LIMIT 24", args)][::-1]
        by_who = [{"who": r["who"], "count": r["n"], "amount": money(r["a"])} for r in self.rows(
            f"SELECT n.who, COUNT(*) n, SUM(CAST(n.money AS REAL)) a FROM gathering_note n{where} GROUP BY n.who ORDER BY a DESC LIMIT 15", args)]
        rows = self.rows(
            f"SELECT n.*, (SELECT no_ FROM contract c WHERE c.id = CAST(n.co_id AS INTEGER)) AS order_no FROM gathering_note n{where} ORDER BY n.date DESC, n.id DESC LIMIT ? OFFSET ?",
            [*args, size, offset])
        return {"total": total.get("n") or 0, "amount": money(total.get("a")), "page": page, "size": size, "by_month": by_month, "by_who": by_who,
                "rows": [self.receipt_row(n) for n in rows]}

    # ---- 工作日志（行动记录）
    def date_flag(self, value: Any) -> str:
        """日期质量标记：future = 晚于今天（录入错误，如 2224-06-12）；invalid = 空或格式异常；正常为空串。"""
        if not _valid_date(value):
            return "invalid"
        return "future" if value > self.today.isoformat() else ""

    def action_row(self, a: Dict[str, Any]) -> Dict[str, Any]:
        subject, content = a.get("subject") or "", a.get("content") or ""
        return {
            "id": a["id"], "date": a.get("date"), "end_date": a.get("endate"), "date_flag": self.date_flag(a.get("date")),
            "cale_text": self.lk.text("action", "cale", a.get("cale")),
            "type": a.get("type"), "type_text": self.lk.text("action", "type", a.get("type")), "who": self.lk.names_from_codes(a.get("who")),
            "customer": self.lk.customer(a.get("cu_sn")), "contact": a.get("contact_name"), "subject": subject,
            "content": content if content != subject else "", "order_id": _int(a.get("co_id"), 0) or None,
        }

    def actions(self) -> Dict[str, Any]:
        clauses, args = ["a._deleted_at IS NULL"], []
        if self.get("who"):
            clauses.append("(',' || a.who || ',') LIKE ?")
            args.append(f"%,{self.get('who')},%")
        if self.get("type"):
            clauses.append("a.type = ?")
            args.append(self.get("type"))
        if self.get("cale"):
            clauses.append("a.cale = ?")
            args.append(self.get("cale"))
        self.customer_clause("a", clauses, args)
        self.date_clause("a", clauses, args)
        q = self.get("q")
        if q:
            args.extend([f"%{q}%", f"%{q}%"])
            clauses.append(f"(a.subject LIKE ? OR a.content LIKE ? OR {self.name_search_clause('a', q, args)})")
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = (self.one(f"SELECT COUNT(*) n FROM action a{where}", args) or {}).get("n") or 0
        by_type = [{"type": r["type"], "text": self.lk.text("action", "type", r["type"]) or "未分类", "count": r["n"]}
                   for r in self.rows(f"SELECT a.type, COUNT(*) n FROM action a{where} GROUP BY a.type ORDER BY n DESC", args)]
        by_day = [{"date": r["d"], "count": r["n"]} for r in self.rows(
            f"SELECT a.date d, COUNT(*) n FROM action a{where} AND a.date LIKE '____-__-__' AND a.date <= ? GROUP BY a.date ORDER BY d DESC LIMIT 62", [*args, self.today.isoformat()])][::-1]
        who_counts: Dict[str, int] = {}
        for r in self.rows(f"SELECT a.who, COUNT(*) n FROM action a{where} GROUP BY a.who", args):
            for code in [p for p in str(r["who"] or "").split(",") if p.strip()] or [str(r["who"] or "")]:
                who_counts[code] = who_counts.get(code, 0) + r["n"]
        by_who = [{"who": self.lk.user_name(k), "part": k, "count": v} for k, v in sorted(who_counts.items(), key=lambda kv: -kv[1])[:20]]
        rows = self.rows(
            f"SELECT a.*, k.name AS contact_name FROM action a LEFT JOIN contact k ON k.id = CAST(a.con_id AS INTEGER){where} ORDER BY a.date DESC, a.id DESC LIMIT ? OFFSET ?",
            [*args, size, offset])
        return {"total": total, "page": page, "size": size, "by_type": by_type, "by_day": by_day, "by_who": by_who, "rows": [self.action_row(a) for a in rows]}


# ---------------------------------------------------------------------- HTTP
ROUTES: List[Tuple[re.Pattern, Callable[[Query, re.Match], Any]]] = [
    (re.compile(r"^/api/meta$"), lambda q, m: q.meta()),
    (re.compile(r"^/api/overview$"), lambda q, m: q.overview()),
    (re.compile(r"^/api/orders$"), lambda q, m: q.orders()),
    (re.compile(r"^/api/orders/(\d+)$"), lambda q, m: q.order_detail(int(m.group(1)))),
    (re.compile(r"^/api/customers$"), lambda q, m: q.customers()),
    (re.compile(r"^/api/customers/(\d+)$"), lambda q, m: q.customer_detail(int(m.group(1)))),
    (re.compile(r"^/api/receivables$"), lambda q, m: q.receivables()),
    (re.compile(r"^/api/receipts$"), lambda q, m: q.receipts()),
    (re.compile(r"^/api/actions$"), lambda q, m: q.actions()),
]


class Handler(BaseHTTPRequestHandler):
    mirror: Mirror  # 由 make_server 注入
    server_version = "xtools-web/0.4"

    def log_message(self, fmt: str, *args: Any) -> None:  # 访问日志降级为 debug
        logger.debug("%s " + fmt, self.address_string(), *args)

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        path = url.path
        if path in ("/", "/index.html"):
            return self.send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if path.startswith("/static/") and "/../" not in path:
            return self.send_file(STATIC_DIR / path[len("/static/"):], None)
        for pattern, func in ROUTES:
            m = pattern.match(path)
            if m:
                params = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=False).items()}
                return self.send_api(func, m, params)
        self.send_json({"error": "not found"}, 404)

    def send_api(self, func: Callable, m: re.Match, params: Dict[str, str]) -> None:
        t0 = time.time()
        conn = None
        try:
            conn = self.mirror.connect()
            lk = self.mirror.lookups(conn)
            result = func(Query(conn, lk, params), m)
            if result is None:
                return self.send_json({"error": "not found"}, 404)
            self.send_json(result)
            logger.info("%s %s %.0fms", self.path.split("?")[0], json.dumps(params, ensure_ascii=False) if params else "", (time.time() - t0) * 1000)
        except sqlite3.Error as exc:
            logger.exception("数据库错误 %s", self.path)
            self.send_json({"error": f"数据库错误：{exc}"}, 500)
        except Exception as exc:  # noqa: BLE001
            logger.exception("接口异常 %s", self.path)
            self.send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
        finally:
            if conn is not None:
                conn.close()

    def send_json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: Optional[str]) -> None:
        try:
            path = path.resolve()
            if STATIC_DIR.resolve() not in path.parents and path != STATIC_DIR.resolve():
                raise FileNotFoundError(path)
            data = path.read_bytes()
        except (FileNotFoundError, IsADirectoryError):
            return self.send_json({"error": "not found"}, 404)
        if content_type is None:
            content_type = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                            ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}.get(path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def make_server(db_path: str | Path, host: str = "127.0.0.1", port: int = 8790) -> ThreadingHTTPServer:
    mirror = Mirror(db_path)
    handler = type("BoundHandler", (Handler,), {"mirror": mirror})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
