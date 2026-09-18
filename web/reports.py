"""本地前台 0.5：分析类查询（销售分析、客户分析、业务员看板、产品与库存、采购与付款、现金流、联系人）。

以 mixin 形式并入 web.server.Query：依赖 Query 的 conn / lk / p / today / get / rows / one / page / customer_keys /
customer_clause / date_clause / name_search_clause / order_row / enrich_orders / receipt_row / plan_row / action_row / enrich_actions。

口径：
* 订单金额统计一律不含“意外中止”（status=3）；按产品 / 分类 / 大类维度或带产品筛选时用订单明细金额（contract_goods.sum）。
* 多币种：采购单、付款计划、订单按单据的 money_rate（每 100 外币折合人民币）折算；RMB 的 money_rate 为 100。
* 客户 = 订单 cu_sn 解析出的客户 id（"[id:N]" 或客户编号 sn）。
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Sequence, Tuple

CANCELLED = "3"
OPEN_PLAN_SQL = "IN ('2','4')"
# 折算人民币：money_rate 为每 100 外币的人民币价（RMB 为 100）
RMB_EXPR = "(CASE WHEN COALESCE({t}.money_type,'') IN ('', 'RMB') OR COALESCE({t}.money_rate,'') = '' THEN CAST({t}.money AS REAL) ELSE CAST({t}.money AS REAL) * CAST({t}.money_rate AS REAL) / 100.0 END)"
ORDER_RMB_EXPR = "(CASE WHEN COALESCE(o.money_type,'') IN ('', 'RMB') OR COALESCE(o.money_rate,'') = '' THEN CAST(o.sum AS REAL) ELSE CAST(o.sum AS REAL) * CAST(o.money_rate AS REAL) / 100.0 END)"
CID_EXPR = ("CASE WHEN {t}.cu_sn LIKE '[id:%]' THEN CAST(substr({t}.cu_sn, 5, length({t}.cu_sn) - 5) AS INTEGER) "
            "ELSE (SELECT s.id FROM customer s WHERE s.sn = {t}.cu_sn AND s.sn <> '' LIMIT 1) END")
SALES_DIMS = ("who", "customer", "product", "class", "group", "region", "type", "month")
# 订单明细 / 采购明细里的产品引用：产品编号 sn，或产品没有编号时为 "[id:N]"；统一按 product.id 关联
PRODUCT_KEY = "(CASE WHEN {g}.prod LIKE '[id:%]' THEN CAST(substr({g}.prod, 5, length({g}.prod) - 5) AS INTEGER) ELSE (SELECT s.id FROM product s WHERE s.sn = {g}.prod AND s.sn <> '' LIMIT 1) END)"
PRODUCT_JOIN = "LEFT JOIN product p ON p.id = " + PRODUCT_KEY.format(g="g")
PURCHASE_STATUS_FALLBACK = {"0": "待入库", "1": "生成入库单", "2": "部分入库", "3": "全部入库"}
PAY_PLAN_STATUS_FALLBACK = {"0": "未付", "1": "已付"}


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


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def shift_year(day: dt.date, years: int) -> dt.date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 2 月 29 日
        return day.replace(year=day.year + years, day=28)


def months_back(day: dt.date, n: int) -> str:
    """day 往前 n 个月的月份 'YYYY-MM'。"""
    y, m = day.year, day.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    return f"{y}-{m:02d}"


def month_range(last: str, n: int) -> List[str]:
    y, m = int(last[:4]), int(last[5:7])
    out = []
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


class ReportQueries:
    conn: Any
    lk: Any
    p: Dict[str, str]
    today: dt.date

    # ------------------------------------------------------------------ 通用
    def _years(self) -> List[int]:
        raw = self.get("years")
        years = sorted({_int(y) for y in raw.split(",") if _int(y) >= 2000}, reverse=True) if raw else []
        if not years:
            years = [self.today.year, self.today.year - 1, self.today.year - 2]
        return years[:8]

    def _order_scope(self, alias: str, clauses: List[str], args: List[Any]) -> None:
        """销售分析 / 业务员看板共用的订单筛选：业务员、客户、类型、地区、月份。"""
        who = self.get("who")
        if who:
            clauses.append(f"{alias}.who = ?")
            args.append(self.lk.part_to_name(who))
        self.customer_clause(alias, clauses, args)
        if self.get("type"):
            clauses.append(f"{alias}.type = ?")
            args.append(self.get("type"))
        if self.get("state"):
            args.extend([self.get("state"), self.get("state")])
            clauses.append(f"({alias}.cu_sn IN (SELECT '[id:' || id || ']' FROM customer WHERE state = ?) OR {alias}.cu_sn IN (SELECT sn FROM customer WHERE sn <> '' AND state = ?))")
        if self.get("owner"):
            args.extend([self.get("owner"), self.get("owner")])
            clauses.append(f"({alias}.cu_sn IN (SELECT '[id:' || id || ']' FROM customer WHERE owner = ?) OR {alias}.cu_sn IN (SELECT sn FROM customer WHERE sn <> '' AND owner = ?))")
        if self.get("month"):
            clauses.append(f"substr({alias}.date, 1, 7) = ?")
            args.append(self.get("month")[:7])

    def _line_filters(self, clauses: List[str], args: List[Any]) -> bool:
        """产品层筛选（明细模式）：prod / class / group。返回是否用到。"""
        used = False
        if self.get("prod"):
            prod = self.lk.product(self.get("prod"))
            clauses.append("p.id = ?")
            args.append(prod["id"] if prod else -1)
            used = True
        if self.get("class"):
            clauses.append("COALESCE(p.class, '') = ?")
            args.append(self.get("class"))
            used = True
        if self.get("group"):
            titles = self.lk.classes_in_group(self.get("group"))
            if titles:
                clauses.append(f"COALESCE(p.class, '') IN ({','.join('?' * len(titles))})")
                args.extend(titles)
            else:
                clauses.append("COALESCE(p.class, '') = ''")
            used = True
        return used

    # ------------------------------------------------------------------ 销售分析
    def sales(self) -> Dict[str, Any]:
        by = self.get("by", "who")
        if by not in SALES_DIMS:
            by = "who"
        years = self._years()
        ytd = self.get("ytd") in ("1", "true", "on")
        limit = min(max(_int(self.get("limit"), 60), 1), 5000)
        marks = ",".join("?" * len(years))
        clauses = ["o._deleted_at IS NULL", f"o.status <> '{CANCELLED}'", f"substr(o.date, 1, 4) IN ({marks})"]
        args: List[Any] = [str(y) for y in years]
        if ytd:
            clauses.append("substr(o.date, 6, 5) <= ?")
            args.append(self.today.strftime("%m-%d"))
        self._order_scope("o", clauses, args)
        line_filters = self._line_filters(clauses, args)
        line_mode = by in ("product", "class", "group") or line_filters
        where = " WHERE " + " AND ".join(clauses)
        if line_mode:
            base = f"FROM contract_goods g JOIN contract o ON o.id = g.contract_id {PRODUCT_JOIN}" + where
            agg = "COUNT(DISTINCT o.id) n, SUM(CAST(g.sum AS REAL)) a, SUM(CAST(g.amount AS REAL)) q"
        else:
            base = "FROM contract o" + where
            agg = f"COUNT(*) n, SUM({ORDER_RMB_EXPR}) a, NULL q"
        dim_sql = {
            "who": "o.who", "customer": "o.cu_sn", "region": "o.cu_sn", "type": "o.type", "month": "substr(o.date, 6, 2)",
            "product": "COALESCE('#' || p.id, g.prod)", "class": "COALESCE(p.class, '')", "group": "COALESCE(p.class, '')",
        }[by]
        extra = ", MAX(g.prod_name) pn" if by == "product" else ""
        raw = self.rows(f"SELECT {dim_sql} k, substr(o.date, 1, 4) y, {agg}{extra} {base} GROUP BY k, y", args)

        # 折叠到展示行：客户 / 地区 / 大类在 Python 里归并
        rows: Dict[Any, Dict[str, Any]] = {}
        for r in raw:
            key, label, sub, extra_fields = r["k"], r["k"], "", {}
            if by == "customer":
                cust = self.lk.customer(r["k"]) or {"id": None, "name": str(r["k"]), "owner": None}
                key = cust["id"] if cust["id"] is not None else f"?{r['k']}"
                label, sub, extra_fields = cust["name"], cust.get("owner") or "", {"id": cust["id"], "customer": cust}
            elif by == "region":
                cid = self.lk.customer_id(r["k"])
                state = str((self.lk.customers.get(cid) or {}).get("state") or "0") if cid else "0"
                key = state
                label, sub = self.lk.state_name(state), self.lk.state_cities(state)
                extra_fields = {"state": state}
            elif by == "group":
                key = self.lk.class_group(r["k"])
                label = key
            elif by == "class":
                key = r["k"] or ""
                label, sub = key or "（未分类）", self.lk.class_group(key)
            elif by == "product":
                prod = self.lk.product(r["k"]) or {}
                key = prod.get("id") or r["k"] or "?"
                label = prod.get("name") or r.get("pn") or r["k"] or "（无编码）"
                sub = " ".join(x for x in [prod.get("sn") or ("" if prod else r["k"] or ""), prod.get("model") or ""] if x)
                extra_fields = {"id": prod.get("id"), "sn": prod.get("sn") or "", "model": prod.get("model") or "", "unit": prod.get("unit") or "", "class": prod.get("class") or ""}
            elif by == "type":
                label = self.lk.text("contract", "type", r["k"]) or "（无类型）"
            elif by == "month":
                key = r["k"] or "??"
                label = f"{int(key)} 月" if key.isdigit() else "（无日期）"
            elif by == "who":
                label = r["k"] or "（未填业务员）"
            row = rows.setdefault(key, {"key": key, "name": label, "sub": sub, "cells": {}, "total": 0.0, "count": 0, **extra_fields})
            cell = row["cells"].setdefault(str(r["y"]), {"count": 0, "amount": 0.0, "qty": 0.0})
            cell["count"] += r["n"] or 0
            cell["amount"] = round(cell["amount"] + (r["a"] or 0), 2)
            if r["q"] is not None:
                cell["qty"] = round(cell["qty"] + (r["q"] or 0), 3)
            row["total"] = round(row["total"] + (r["a"] or 0), 2)
            row["count"] += r["n"] or 0
        latest = str(years[0])
        totals = {str(y): {"count": 0, "amount": 0.0, "qty": 0.0} for y in years}
        for row in rows.values():
            for y, cell in row["cells"].items():
                if y in totals:
                    totals[y]["count"] += cell["count"]
                    totals[y]["amount"] = round(totals[y]["amount"] + cell["amount"], 2)
                    totals[y]["qty"] = round(totals[y]["qty"] + cell["qty"], 3)
        if by == "month":
            ordered = sorted(rows.values(), key=lambda r: r["key"])
        else:
            ordered = sorted(rows.values(), key=lambda r: (-(r["cells"].get(latest, {}).get("amount", 0.0)), -r["total"]))
        for row in ordered:  # 最新年份与上一年份的同比
            prev = str(years[1]) if len(years) > 1 else None
            cur_a = row["cells"].get(latest, {}).get("amount", 0.0)
            prev_a = row["cells"].get(prev, {}).get("amount", 0.0) if prev else 0.0
            row["yoy"] = round((cur_a - prev_a) / abs(prev_a) * 100, 1) if prev_a else None
        monthly = self._sales_monthly(base, args, years) if by != "month" else None
        return {
            "by": by, "years": years, "ytd": ytd, "line_mode": line_mode, "total_rows": len(ordered),
            "rows": ordered[:limit], "totals": totals,
            "monthly": monthly if monthly is not None else [{"month": r["key"], "cells": r["cells"]} for r in ordered],
            "filters": self._sales_filter_labels(),
        }

    def _sales_monthly(self, base: str, args: Sequence[Any], years: List[int]) -> List[Dict[str, Any]]:
        agg = "COUNT(DISTINCT o.id) n, SUM(CAST(g.sum AS REAL)) a" if "contract_goods g" in base else f"COUNT(*) n, SUM({ORDER_RMB_EXPR}) a"
        got: Dict[str, Dict[str, Any]] = {}
        for r in self.rows(f"SELECT substr(o.date, 6, 2) k, substr(o.date, 1, 4) y, {agg} {base} GROUP BY k, y", args):
            got.setdefault(r["k"], {})[str(r["y"])] = {"count": r["n"] or 0, "amount": money(r["a"])}
        return [{"month": f"{m:02d}", "cells": {str(y): got.get(f"{m:02d}", {}).get(str(y), {"count": 0, "amount": 0.0}) for y in years}} for m in range(1, 13)]

    def _sales_filter_labels(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        if self.get("who"):
            out["who"] = self.lk.part_to_name(self.get("who"))
        if self.get("customer_id"):
            c = self.lk.customers.get(_int(self.get("customer_id")))
            out["customer_id"] = (c or {}).get("cu_name") or (c or {}).get("m_name") or self.get("customer_id")
        if self.get("prod"):
            out["prod"] = (self.lk.products.get(self.get("prod")) or {}).get("name") or self.get("prod")
        if self.get("class"):
            out["class"] = self.get("class")
        if self.get("group"):
            out["group"] = self.get("group")
        if self.get("state"):
            out["state"] = self.lk.state_name(self.get("state"))
        if self.get("type"):
            out["type"] = self.lk.text("contract", "type", self.get("type"))
        if self.get("owner"):
            out["owner"] = self.lk.user_name(self.get("owner"))
        if self.get("month"):
            out["month"] = self.get("month")
        return out

    # ------------------------------------------------------------------ 客户分析
    def _customer_facts(self, year: int) -> List[Dict[str, Any]]:
        """每个客户的订单事实：首单 / 末单日期、历史单数与金额、本年与上年单数与金额。"""
        y0, y1, p0, p1 = f"{year}-01-01", f"{year}-12-31", f"{year - 1}-01-01", f"{year - 1}-12-31"
        sql = f"""
            SELECT cid, MIN(date) first_date, MAX(date) last_date, COUNT(*) n_all, SUM(amt) a_all,
                   SUM(CASE WHEN date BETWEEN ? AND ? THEN 1 ELSE 0 END) n_y, SUM(CASE WHEN date BETWEEN ? AND ? THEN amt ELSE 0 END) a_y,
                   SUM(CASE WHEN date BETWEEN ? AND ? THEN 1 ELSE 0 END) n_p, SUM(CASE WHEN date BETWEEN ? AND ? THEN amt ELSE 0 END) a_p
            FROM (SELECT {CID_EXPR.format(t='o')} AS cid, o.date AS date, {ORDER_RMB_EXPR} AS amt
                  FROM contract o WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.date LIKE '____-__-__')
            WHERE cid IS NOT NULL GROUP BY cid"""
        return self.rows(sql, [y0, y1, y0, y1, p0, p1, p0, p1])

    def customer_analysis(self) -> Dict[str, Any]:
        year = _int(self.get("year"), self.today.year)
        owner = self.get("owner")
        idle_bucket = self.get("idle", "6-12")
        limit = min(max(_int(self.get("limit"), 100), 1), 5000)
        facts = self._customer_facts(year)
        today = self.today

        def cust(cid: int) -> Dict[str, Any]:
            c = self.lk.customers.get(cid) or {}
            return {"id": cid, "name": c.get("cu_name") or c.get("m_name") or f"[已删除 {cid}]", "owner": self.lk.user_name(c.get("owner")), "owner_part": c.get("owner"),
                    "life_text": self.lk.text("customer", "life", c.get("life")), "city": c.get("city") or ""}

        if owner:
            facts = [f for f in facts if str((self.lk.customers.get(f["cid"]) or {}).get("owner") or "") == owner]
        year_rows = [f for f in facts if (f["n_y"] or 0) > 0]
        prev_rows = [f for f in facts if (f["n_p"] or 0) > 0]
        # ABC 分层（按本年金额累计占比：A ≤ 80%，B ≤ 95%，C 其余）
        year_rows.sort(key=lambda f: -(f["a_y"] or 0))
        total_y = sum(f["a_y"] or 0 for f in year_rows)
        tiers = {"A": {"tier": "A", "count": 0, "amount": 0.0, "share": 0.0, "limit": 80}, "B": {"tier": "B", "count": 0, "amount": 0.0, "share": 0.0, "limit": 95}, "C": {"tier": "C", "count": 0, "amount": 0.0, "share": 0.0, "limit": 100}}
        tier_rows = []
        cum = 0.0
        for f in year_rows:
            cum += f["a_y"] or 0
            share = cum / total_y * 100 if total_y else 100.0
            tier = "A" if share <= 80 + 1e-9 else ("B" if share <= 95 + 1e-9 else "C")
            if not tier_rows and tier != "A":  # 第一名就超过 80% 时仍归 A
                tier = "A"
            tiers[tier]["count"] += 1
            tiers[tier]["amount"] = round(tiers[tier]["amount"] + (f["a_y"] or 0), 2)
            tier_rows.append({**cust(f["cid"]), "tier": tier, "amount": money(f["a_y"]), "count": f["n_y"], "share": round((f["a_y"] or 0) / total_y * 100, 2) if total_y else 0.0,
                              "cum_share": round(share, 1), "prev_amount": money(f["a_p"]), "first_date": f["first_date"], "last_date": f["last_date"]})
        for t in tiers.values():
            t["share"] = round(t["amount"] / total_y * 100, 1) if total_y else 0.0
        # 新客户：首单在本年
        new_rows = sorted([f for f in facts if (f["first_date"] or "")[:4] == str(year)], key=lambda f: -(f["a_y"] or 0))
        new_prev = sum(1 for f in facts if (f["first_date"] or "")[:4] == str(year - 1))
        new_by_month = [{"month": f"{year}-{m:02d}", "count": 0, "amount": 0.0} for m in range(1, 13)]
        for f in new_rows:
            m = _int((f["first_date"] or "")[5:7], 0)
            if 1 <= m <= 12:
                new_by_month[m - 1]["count"] += 1
                new_by_month[m - 1]["amount"] = round(new_by_month[m - 1]["amount"] + (f["a_y"] or 0), 2)
        # 留存与复购
        retained = [f for f in prev_rows if (f["n_y"] or 0) > 0]
        repeat = [f for f in year_rows if (f["n_y"] or 0) >= 2]
        lost_prev = sorted([f for f in prev_rows if (f["n_y"] or 0) == 0], key=lambda f: -(f["a_p"] or 0))
        # 流失预警：按末单距今天数分档（只看有过订单的客户）
        buckets = [("6-12", "6–12 个月未下单", 182, 365), ("12-24", "1–2 年", 365, 730), ("24-36", "2–3 年", 730, 1095), ("36+", "3 年以上", 1095, 10 ** 6)]
        churn_summary = []
        churn_rows: List[Dict[str, Any]] = []
        for key, label, lo, hi in buckets:
            items = []
            for f in facts:
                try:
                    idle = (today - dt.date.fromisoformat(f["last_date"])).days
                except (TypeError, ValueError):
                    continue
                if lo <= idle < hi:
                    items.append((idle, f))
            churn_summary.append({"key": key, "label": label, "count": len(items), "amount": round(sum(f["a_all"] or 0 for _, f in items), 2)})
            if key == idle_bucket:
                items.sort(key=lambda x: -(x[1]["a_all"] or 0))
                churn_rows = [{**cust(f["cid"]), "last_date": f["last_date"], "idle_days": idle, "count": f["n_all"], "amount": money(f["a_all"]), "first_date": f["first_date"]} for idle, f in items]
        # 按所有者
        by_owner: Dict[str, Dict[str, Any]] = {}
        for cid, c in self.lk.customers.items():
            part = str(c.get("owner") or "")
            if owner and part != owner:
                continue
            acc = by_owner.setdefault(part, {"part": part, "owner": self.lk.user_name(part) or "（无所有者）", "customers": 0, "active": 0, "new": 0, "prev_active": 0, "idle": 0, "amount": 0.0, "prev_amount": 0.0})
            acc["customers"] += 1
        for f in facts:
            part = str((self.lk.customers.get(f["cid"]) or {}).get("owner") or "")
            acc = by_owner.get(part)
            if acc is None:
                continue
            if (f["n_y"] or 0) > 0:
                acc["active"] += 1
                acc["amount"] = round(acc["amount"] + (f["a_y"] or 0), 2)
            if (f["n_p"] or 0) > 0:
                acc["prev_active"] += 1
                acc["prev_amount"] = round(acc["prev_amount"] + (f["a_p"] or 0), 2)
            if (f["first_date"] or "")[:4] == str(year):
                acc["new"] += 1
            try:
                if (today - dt.date.fromisoformat(f["last_date"])).days >= 365:
                    acc["idle"] += 1
            except (TypeError, ValueError):
                pass
        owners = sorted(by_owner.values(), key=lambda a: (-a["amount"], -a["customers"]))
        return {
            "year": year, "owner": owner,
            "kpi": {
                "active": len(year_rows), "prev_active": len(prev_rows), "amount": round(total_y, 2), "prev_amount": round(sum(f["a_p"] or 0 for f in prev_rows), 2),
                "new": len(new_rows), "new_prev": new_prev, "new_amount": round(sum(f["a_y"] or 0 for f in new_rows), 2),
                "retained": len(retained), "retention_rate": round(len(retained) / len(prev_rows) * 100, 1) if prev_rows else None,
                "lost": len(lost_prev), "lost_amount": round(sum(f["a_p"] or 0 for f in lost_prev), 2),
                "repeat": len(repeat), "repeat_rate": round(len(repeat) / len(year_rows) * 100, 1) if year_rows else None,
                "orders_per_customer": round(sum(f["n_y"] or 0 for f in year_rows) / len(year_rows), 2) if year_rows else 0,
                "idle_6_12": churn_summary[0]["count"] if churn_summary else 0,
            },
            "tiers": list(tiers.values()), "tier_rows": tier_rows[:limit], "tier_total": len(tier_rows),
            "new_by_month": new_by_month, "new_rows": [{**cust(f["cid"]), "first_date": f["first_date"], "amount": money(f["a_y"]), "count": f["n_y"]} for f in new_rows[:limit]], "new_total": len(new_rows),
            "lost_rows": [{**cust(f["cid"]), "last_date": f["last_date"], "prev_amount": money(f["a_p"]), "prev_count": f["n_p"]} for f in lost_prev[:limit]], "lost_total": len(lost_prev),
            "churn": {"buckets": churn_summary, "bucket": idle_bucket, "rows": churn_rows[:limit], "total": len(churn_rows)},
            "by_owner": owners,
        }

    # ------------------------------------------------------------------ 业务员看板
    def salesperson(self) -> Optional[Dict[str, Any]]:
        who = self.get("who")
        if not who:
            return None
        part = who if who in self.lk.users else (self.lk.name_to_part.get(who) or who)
        name = self.lk.part_to_name(part)
        user = self.lk.users.get(part) or {"part": part, "name": name, "active": True, "dept": ""}
        year = _int(self.get("year"), self.today.year)
        y0, y1 = f"{year}-01-01", f"{year}-12-31"
        cutoff = min(self.today, dt.date(year, 12, 31)).isoformat()  # 同期截止：本年为今天，往年为年底
        p_cut = shift_year(dt.date.fromisoformat(cutoff), -1).isoformat()
        p0 = f"{year - 1}-01-01"

        def agg(sql: str, args: Sequence[Any]) -> Dict[str, Any]:
            r = self.one(sql, args) or {}
            return {"count": r.get("n") or 0, "amount": money(r.get("a"))}

        base_o = f"FROM contract o WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.who = ?"
        kpi = {
            "orders": agg(f"SELECT COUNT(*) n, SUM({ORDER_RMB_EXPR}) a {base_o} AND o.date BETWEEN ? AND ?", [name, y0, cutoff]),
            "orders_prev": agg(f"SELECT COUNT(*) n, SUM({ORDER_RMB_EXPR}) a {base_o} AND o.date BETWEEN ? AND ?", [name, p0, p_cut]),
            "orders_year": agg(f"SELECT COUNT(*) n, SUM({ORDER_RMB_EXPR}) a {base_o} AND o.date BETWEEN ? AND ?", [name, y0, y1]),
            "receipts": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND who = ? AND date BETWEEN ? AND ?", [name, y0, cutoff]),
            "receipts_prev": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND who = ? AND date BETWEEN ? AND ?", [name, p0, p_cut]),
            "open_orders": agg(f"SELECT COUNT(*) n, SUM({ORDER_RMB_EXPR}) a FROM contract o WHERE o._deleted_at IS NULL AND o.status = '1' AND o.who = ?", [name]),
            "open_plans": agg(f"SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering WHERE _deleted_at IS NULL AND status {OPEN_PLAN_SQL} AND who = ?", [part]),
            "overdue_plans": agg(f"SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering WHERE _deleted_at IS NULL AND status {OPEN_PLAN_SQL} AND who = ? AND date < ?", [part, self.today.isoformat()]),
            "customers_owned": sum(1 for c in self.lk.customers.values() if str(c.get("owner") or "") == part),
            "customers_active": (self.one(f"SELECT COUNT(DISTINCT o.cu_sn) n {base_o} AND o.date BETWEEN ? AND ?", [name, y0, y1]) or {}).get("n") or 0,
            "customers_new": self._new_customers_won(name, y0, y1),
            "actions": (self.one("SELECT COUNT(*) n FROM action WHERE _deleted_at IS NULL AND (',' || who || ',') LIKE ? AND date BETWEEN ? AND ?", [f"%,{part},%", y0, y1]) or {}).get("n") or 0,
            "actions_month": (self.one("SELECT COUNT(*) n FROM action WHERE _deleted_at IS NULL AND (',' || who || ',') LIKE ? AND substr(date, 1, 7) = ?", [f"%,{part},%", self.today.strftime('%Y-%m')]) or {}).get("n") or 0,
            "last_action": (self.one("SELECT MAX(date) d FROM action WHERE _deleted_at IS NULL AND (',' || who || ',') LIKE ? AND date <= ?", [f"%,{part},%", self.today.isoformat()]) or {}).get("d"),
        }
        months = [f"{year}-{m:02d}" for m in range(1, 13)]
        series = {m: {"month": m, "orders": {"count": 0, "amount": 0.0}, "receipts": {"count": 0, "amount": 0.0}, "actions": 0} for m in months}
        for r in self.rows(f"SELECT substr(o.date, 1, 7) m, COUNT(*) n, SUM({ORDER_RMB_EXPR}) a {base_o} AND o.date BETWEEN ? AND ? GROUP BY m", [name, y0, y1]):
            if r["m"] in series:
                series[r["m"]]["orders"] = {"count": r["n"], "amount": money(r["a"])}
        for r in self.rows("SELECT substr(date, 1, 7) m, COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND who = ? AND date BETWEEN ? AND ? GROUP BY m", [name, y0, y1]):
            if r["m"] in series:
                series[r["m"]]["receipts"] = {"count": r["n"], "amount": money(r["a"])}
        for r in self.rows("SELECT substr(date, 1, 7) m, COUNT(*) n FROM action WHERE _deleted_at IS NULL AND (',' || who || ',') LIKE ? AND date BETWEEN ? AND ? GROUP BY m", [f"%,{part},%", y0, y1]):
            if r["m"] in series:
                series[r["m"]]["actions"] = r["n"]
        top_customers = [{"customer": self.lk.customer(r["cu_sn"]), "count": r["n"], "amount": money(r["a"])}
                         for r in self.rows(f"SELECT o.cu_sn, COUNT(*) n, SUM({ORDER_RMB_EXPR}) a {base_o} AND o.date BETWEEN ? AND ? GROUP BY o.cu_sn ORDER BY a DESC LIMIT 10", [name, y0, y1])]
        top_products = []
        for r in self.rows(
            f"SELECT COALESCE('#' || p.id, g.prod) k, MAX(g.prod_name) pn, SUM(CAST(g.sum AS REAL)) a, SUM(CAST(g.amount AS REAL)) q, COUNT(DISTINCT o.id) n FROM contract_goods g JOIN contract o ON o.id = g.contract_id {PRODUCT_JOIN} "
            f"WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.who = ? AND o.date BETWEEN ? AND ? GROUP BY k ORDER BY a DESC LIMIT 10", [name, y0, y1]):
            prod = self.lk.product(r["k"]) or {}
            top_products.append({"id": prod.get("id"), "sn": prod.get("sn") or "", "name": prod.get("name") or r["pn"] or r["k"], "model": prod.get("model") or "", "amount": money(r["a"]), "quantity": r["q"], "orders": r["n"]})
        ranking = self.rows(f"SELECT o.who, SUM({ORDER_RMB_EXPR}) a FROM contract o WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.date BETWEEN ? AND ? GROUP BY o.who ORDER BY a DESC", [y0, y1])
        rank = next((i + 1 for i, r in enumerate(ranking) if r["who"] == name), None)
        open_plans = [self.plan_row(g) for g in self.rows(f"SELECT * FROM gathering WHERE _deleted_at IS NULL AND status {OPEN_PLAN_SQL} AND who = ? ORDER BY date LIMIT 30", [part])]
        recent_orders = [self.order_row(r) for r in self.enrich_orders(self.rows(f"SELECT o.* FROM contract o WHERE o._deleted_at IS NULL AND o.who = ? ORDER BY o.date DESC, o.id DESC LIMIT 10", [name]))]
        recent_actions = [self.action_row(a) for a in self.enrich_actions(self.rows(
            "SELECT a.*, k.name AS contact_name FROM action a LEFT JOIN contact k ON k.id = CAST(a.con_id AS INTEGER) WHERE a._deleted_at IS NULL AND (',' || a.who || ',') LIKE ? AND a.date <= ? ORDER BY a.date DESC, a.id DESC LIMIT 10",
            [f"%,{part},%", self.today.isoformat()]))]
        return {"user": {**user, "part": part, "name": name}, "year": year, "cutoff": cutoff, "kpi": kpi, "rank": rank, "rank_of": len(ranking), "monthly": list(series.values()),
                "top_customers": top_customers, "top_products": top_products, "open_plans": open_plans, "recent_orders": recent_orders, "recent_actions": recent_actions}

    def _new_customers_won(self, name: str, y0: str, y1: str) -> int:
        """本年首次下单（全公司口径）且本年向此业务员下过单的客户数。"""
        first_in_year = {r["cid"] for r in self.rows(
            f"SELECT cid FROM (SELECT {CID_EXPR.format(t='o')} cid, MIN(o.date) d FROM contract o WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.date LIKE '____-__-__' GROUP BY cid) "
            "WHERE cid IS NOT NULL AND d BETWEEN ? AND ?", [y0, y1])}
        if not first_in_year:
            return 0
        mine = {r["cid"] for r in self.rows(
            f"SELECT DISTINCT {CID_EXPR.format(t='o')} cid FROM contract o WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.who = ? AND o.date BETWEEN ? AND ?", [name, y0, y1])}
        return len(first_in_year & mine)

    # ------------------------------------------------------------------ 产品与库存
    def _product_window(self) -> Tuple[str, str]:
        """销售统计窗口：months=N（缺省 12）→ 起始日期；0 表示全部。"""
        months = _int(self.get("months"), 12)
        if months <= 0:
            return "1900-01-01", "全部"
        start = months_back(self.today, months - 1) + "-01"
        return start, f"近 {months} 个月"

    PRODUCT_SALES_CTE = (f"WITH s AS (SELECT {PRODUCT_KEY.format(g='g')} pid, COUNT(DISTINCT o.id) n, SUM(CAST(g.sum AS REAL)) a, SUM(CAST(g.amount AS REAL)) q, MAX(o.date) last_date, COUNT(DISTINCT o.cu_sn) cust "
                         f"FROM contract_goods g JOIN contract o ON o.id = g.contract_id WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.date >= ? GROUP BY pid)")

    def product_row(self, r: Dict[str, Any]) -> Dict[str, Any]:
        stock, ldown, lup = _num(r.get("lnum")), _num(r.get("ldown")), _num(r.get("lup"))
        return {
            "id": r.get("id"), "sn": r.get("sn"), "name": r.get("name"), "model": r.get("model"), "sku": r.get("sku"), "unit": r.get("unit"),
            "class": r.get("class") or "", "group": self.lk.class_group(r.get("class") or ""), "price": money(r.get("price")), "cost": money(r.get("costprice")),
            "status": r.get("status"), "manufacturer": r.get("manufacturer"), "mflag": r.get("mflag"),
            "stock": round(stock, 3), "stock_low": ldown > 0 and stock < ldown, "ldown": round(ldown, 3), "lup": round(lup, 3), "ptype": r.get("ptype"),
            "sales_amount": money(r.get("a")), "sales_qty": round(_num(r.get("q")), 3), "sales_orders": r.get("n") or 0, "sales_customers": r.get("cust") or 0, "last_sale": r.get("last_date"),
            "memo": r.get("memo"),
        }

    def products(self) -> Dict[str, Any]:
        start, window = self._product_window()
        clauses, args = ["p._deleted_at IS NULL"], []
        q = self.get("q")
        if q:
            args.extend([f"%{q}%"] * 3)
            clauses.append("(p.sn LIKE ? OR p.name LIKE ? OR p.model LIKE ?)")
        if self.get("class"):
            clauses.append("COALESCE(p.class, '') = ?")
            args.append(self.get("class"))
        if self.get("group"):
            titles = self.lk.classes_in_group(self.get("group"))
            clauses.append(f"COALESCE(p.class, '') IN ({','.join('?' * len(titles))})" if titles else "COALESCE(p.class, '') = ''")
            args.extend(titles)
        if self.get("status"):
            clauses.append("p.status = ?")
            args.append(self.get("status"))
        stock = self.get("stock")
        if stock == "in":
            clauses.append("CAST(p.lnum AS REAL) > 0")
        elif stock == "out":
            clauses.append("COALESCE(CAST(p.lnum AS REAL), 0) <= 0")
        elif stock == "low":
            clauses.append("CAST(p.ldown AS REAL) > 0 AND CAST(p.lnum AS REAL) < CAST(p.ldown AS REAL)")
        elif stock == "unsold":
            clauses.append("CAST(p.lnum AS REAL) > 0 AND s.pid IS NULL")
        elif stock == "sold":
            clauses.append("s.pid IS NOT NULL")
        where = " WHERE " + " AND ".join(clauses)
        base = f"{self.PRODUCT_SALES_CTE} SELECT {{cols}} FROM product p LEFT JOIN s ON s.pid = p.id{where}"
        summary = self.one(base.format(cols=(
            "COUNT(*) n, SUM(CASE WHEN CAST(p.lnum AS REAL) > 0 THEN 1 ELSE 0 END) with_stock, "
            "SUM(CASE WHEN CAST(p.ldown AS REAL) > 0 AND CAST(p.lnum AS REAL) < CAST(p.ldown AS REAL) THEN 1 ELSE 0 END) low, "
            "SUM(CASE WHEN CAST(p.lnum AS REAL) > 0 AND s.pid IS NULL THEN 1 ELSE 0 END) unsold, SUM(CASE WHEN s.pid IS NOT NULL THEN 1 ELSE 0 END) sold, "
            "SUM(s.a) amount, SUM(s.q) qty")), [start, *args]) or {}
        by_class: Dict[str, Dict[str, Any]] = {}
        for r in self.rows(base.format(cols="COALESCE(p.class, '') k, COUNT(*) n, SUM(CASE WHEN CAST(p.lnum AS REAL) > 0 THEN 1 ELSE 0 END) ws, SUM(s.a) a, SUM(s.q) q, SUM(s.n) o") + " GROUP BY k", [start, *args]):
            g = self.lk.class_group(r["k"])
            acc = by_class.setdefault(g, {"group": g, "products": 0, "with_stock": 0, "amount": 0.0, "qty": 0.0, "classes": 0})
            acc["products"] += r["n"] or 0
            acc["with_stock"] += r["ws"] or 0
            acc["amount"] = round(acc["amount"] + (r["a"] or 0), 2)
            acc["qty"] = round(acc["qty"] + (r["q"] or 0), 3)
            acc["classes"] += 1
        page, size, offset = self.page()
        sort = {
            "qty": "s.q DESC NULLS LAST, p.sn", "orders": "s.n DESC NULLS LAST, p.sn", "stock": "CAST(p.lnum AS REAL) DESC, p.sn", "name": "p.name COLLATE NOCASE, p.sn",
            "last": "s.last_date DESC NULLS LAST, p.sn", "price": "CAST(p.price AS REAL) DESC, p.sn", "sn": "p.sn, p.id",
        }.get(self.get("sort"), "s.a DESC NULLS LAST, CAST(p.lnum AS REAL) DESC, p.sn")
        rows = self.rows(base.format(cols="p.*, s.n, s.a, s.q, s.last_date, s.cust") + f" ORDER BY {sort} LIMIT ? OFFSET ?", [start, *args, size, offset])
        return {"total": summary.get("n") or 0, "page": page, "size": size, "window": window, "window_start": start,
                "summary": {"with_stock": summary.get("with_stock") or 0, "low": summary.get("low") or 0, "unsold": summary.get("unsold") or 0, "sold": summary.get("sold") or 0,
                            "amount": money(summary.get("amount")), "qty": round(_num(summary.get("qty")), 3)},
                "by_group": sorted(by_class.values(), key=lambda a: -a["amount"]), "rows": [self.product_row(r) for r in rows]}

    def product_detail(self) -> Optional[Dict[str, Any]]:
        """按 id（优先）或编号 sn 查看产品；产品没有编号时明细里以 "[id:N]" 引用。"""
        prod = self.lk.product(f"[id:{self.get('id')}]" if self.get("id") else self.get("sn"))
        if not prod:
            return None
        pid, keys = prod["id"], [prod.get("sn") or "", f"[id:{prod['id']}]"]
        start, window = self._product_window()
        r = self.one(f"{self.PRODUCT_SALES_CTE} SELECT p.*, s.n, s.a, s.q, s.last_date, s.cust FROM product p LEFT JOIN s ON s.pid = p.id WHERE p.id = ?", [start, pid])
        if not r:
            return None
        base = f"FROM contract_goods g JOIN contract o ON o.id = g.contract_id WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND g.prod IN (?, ?)"
        yearly = [{"year": x["y"], "count": x["n"], "amount": money(x["a"]), "qty": round(_num(x["q"]), 3)} for x in self.rows(
            f"SELECT substr(o.date, 1, 4) y, COUNT(DISTINCT o.id) n, SUM(CAST(g.sum AS REAL)) a, SUM(CAST(g.amount AS REAL)) q {base} AND o.date LIKE '____-__-__' GROUP BY y ORDER BY y", keys)]
        m_start = months_back(self.today, 23) + "-01"
        got = {x["m"]: x for x in self.rows(f"SELECT substr(o.date, 1, 7) m, COUNT(DISTINCT o.id) n, SUM(CAST(g.sum AS REAL)) a, SUM(CAST(g.amount AS REAL)) q {base} AND o.date >= ? GROUP BY m", [*keys, m_start])}
        monthly = [{"month": m, "count": (got.get(m) or {}).get("n") or 0, "amount": money((got.get(m) or {}).get("a")), "qty": round(_num((got.get(m) or {}).get("q")), 3)} for m in month_range(self.today.strftime("%Y-%m"), 24)]
        top_customers = [{"customer": self.lk.customer(x["cu_sn"]), "count": x["n"], "amount": money(x["a"]), "qty": round(_num(x["q"]), 3), "last_date": x["d"]} for x in self.rows(
            f"SELECT o.cu_sn, COUNT(DISTINCT o.id) n, SUM(CAST(g.sum AS REAL)) a, SUM(CAST(g.amount AS REAL)) q, MAX(o.date) d {base} GROUP BY o.cu_sn ORDER BY a DESC LIMIT 15", keys)]
        lines = [{"order_id": x["id"], "order_no": x["no_"], "date": x["date"], "customer": self.lk.customer(x["cu_sn"]), "who": x["who"], "qty": round(_num(x["amount"]), 3), "unit_price": money(x["un_price"]),
                  "sum": money(x["gsum"]), "status_text": self.lk.text("contract", "status", x["status"]), "batchnum": x["batchnum"], "memo": x["memo"]} for x in self.rows(
            "SELECT o.id, o.no_, o.date, o.cu_sn, o.who, o.status, g.amount, g.un_price, g.sum gsum, g.batchnum, g.memo FROM contract_goods g JOIN contract o ON o.id = g.contract_id "
            "WHERE o._deleted_at IS NULL AND g.prod IN (?, ?) ORDER BY o.date DESC, o.id DESC LIMIT 40", keys)]
        purchases = [{"purchase_id": x["id"], "no": x["no_"], "date": x["date"], "title": x["title"], "supplier": self.lk.supplier(x["cu_id"]), "qty": round(_num(x["num"]), 3), "price": money(x["price"]),
                      "money": money(x["pmoney"]), "money_type": x["money_type"] or "RMB", "who": x["who"]} for x in self.rows(
            "SELECT u.id, u.no_, u.date, u.title, u.cu_id, u.money_type, u.who, i.num, i.price, i.money pmoney FROM purchase_items i JOIN purchase u ON u.id = i.purchase_id "
            "WHERE u._deleted_at IS NULL AND i.prod IN (?, ?) ORDER BY u.date DESC, u.id DESC LIMIT 20", keys)]
        libouts = [{"libout_id": x["id"], "date": x["date"], "title": x["title"], "libname": x["libname"], "customer": self.lk.customer(x["cu_sn"], numeric_is_id=True), "order_no": x["co_sn"],
                    "qty": round(_num(x["num"]), 3), "batchnum": x["batchnum"], "who": self.lk.user_name(x["who"])} for x in self.rows(
            "SELECT l.id, l.date, l.title, l.libname, l.cu_sn, l.co_sn, l.who, i.num, i.batchnum FROM libout_items i JOIN libout l ON l.id = i.libout_id "
            "WHERE l._deleted_at IS NULL AND (CAST(i.pid AS INTEGER) = ? OR i.prod IN (?, ?)) ORDER BY l.date DESC, l.id DESC LIMIT 20", [pid, keys[0] or str(pid), str(pid)])]
        extras = self.raw_extras("product", r["id"], set(r.keys()))
        return {"product": self.product_row(r), "window": window, "yearly": yearly, "monthly": monthly, "top_customers": top_customers, "lines": lines, "purchases": purchases, "libouts": libouts, "extras": extras}

    # ------------------------------------------------------------------ 采购与付款
    def purchase_row(self, r: Dict[str, Any]) -> Dict[str, Any]:
        rmb = _num(r.get("rmb"))
        return {
            "id": r["id"], "no": r.get("no_"), "date": r.get("date"), "title": r.get("title"), "supplier": self.lk.supplier(r.get("cu_id")),
            "type_text": self.lk.text_known("purchase", "type", r.get("type")), "status0": r.get("status0"), "status0_text": self.lk.text("purchase", "status0", r.get("status0")),
            "status": r.get("status"), "status_text": self.lk.text_or("purchase", "status", r.get("status"), PURCHASE_STATUS_FALLBACK),
            "confirm_text": self.lk.text("purchase", "confirm", r.get("confirm")),
            "money": money(r.get("money")), "money_type": r.get("money_type") or "RMB", "money_rate": r.get("money_rate"), "rmb": round(rmb, 2),
            "before_tax": money(r.get("amount_before_tax")), "paid": money(r.get("backsum")), "who": r.get("who"), "eta": r.get("eta"), "lib": r.get("lib"),
            "items": r.get("items") or 0, "memo": r.get("memo"), "return_yn": r.get("return_yn"),
        }

    def _purchase_where(self) -> Tuple[str, List[Any]]:
        clauses, args = ["u._deleted_at IS NULL"], []
        q = self.get("q")
        if q:
            args.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
            clauses.append("(u.no_ LIKE ? OR u.title LIKE ? OR u.cu_id IN (SELECT CAST(id AS TEXT) FROM customer WHERE cu_name LIKE ? OR m_name LIKE ?))")
        if self.get("supplier_id"):
            clauses.append("u.cu_id = ?")
            args.append(self.get("supplier_id"))
        if self.get("who"):
            clauses.append("u.who = ?")
            args.append(self.lk.part_to_name(self.get("who")))
        for col in ("status", "status0", "type", "money_type", "lib"):
            if self.get(col):
                clauses.append(f"u.{col} = ?")
                args.append(self.get(col))
        self.date_clause("u", clauses, args)
        return " WHERE " + " AND ".join(clauses), args

    def purchases(self) -> Dict[str, Any]:
        where, args = self._purchase_where()
        rmb = RMB_EXPR.format(t="u")
        page, size, offset = self.page()
        total = self.one(f"SELECT COUNT(*) n, SUM({rmb}) a FROM purchase u{where}", args) or {}
        by_currency = [{"money_type": r["money_type"] or "RMB", "count": r["n"], "amount": money(r["a"]), "rmb": money(r["r"])} for r in self.rows(
            f"SELECT u.money_type, COUNT(*) n, SUM(CAST(u.money AS REAL)) a, SUM({rmb}) r FROM purchase u{where} GROUP BY u.money_type ORDER BY r DESC", args)]
        by_month = [{"month": r["m"], "count": r["n"], "rmb": money(r["r"])} for r in self.rows(
            f"SELECT substr(u.date, 1, 7) m, COUNT(*) n, SUM({rmb}) r FROM purchase u{where} GROUP BY m ORDER BY m DESC LIMIT 24", args)][::-1]
        by_supplier = [{"supplier": self.lk.supplier(r["cu_id"]), "count": r["n"], "rmb": money(r["r"]), "currencies": r["c"]} for r in self.rows(
            f"SELECT u.cu_id, COUNT(*) n, SUM({rmb}) r, GROUP_CONCAT(DISTINCT COALESCE(NULLIF(u.money_type, ''), 'RMB')) c FROM purchase u{where} GROUP BY u.cu_id ORDER BY r DESC LIMIT 15", args)]
        sort = {"amount": f"{rmb} DESC, u.id DESC", "date_asc": "u.date ASC, u.id ASC"}.get(self.get("sort"), "u.date DESC, u.id DESC")
        rows = self.rows(f"SELECT u.*, {rmb} rmb, (SELECT COUNT(*) FROM purchase_items i WHERE i.purchase_id = u.id) items FROM purchase u{where} ORDER BY {sort} LIMIT ? OFFSET ?", [*args, size, offset])
        return {"total": total.get("n") or 0, "rmb": money(total.get("a")), "page": page, "size": size, "by_currency": by_currency, "by_month": by_month, "by_supplier": by_supplier,
                "rows": [self.purchase_row(r) for r in rows]}

    def purchase_detail(self, pid: int) -> Optional[Dict[str, Any]]:
        r = self.one(f"SELECT u.*, {RMB_EXPR.format(t='u')} rmb, (SELECT COUNT(*) FROM purchase_items i WHERE i.purchase_id = u.id) items FROM purchase u WHERE u.id = ?", [pid])
        if not r:
            return None
        items = []
        for i in self.rows("SELECT * FROM purchase_items WHERE purchase_id = ? ORDER BY _seq", [pid]):
            prod = self.lk.product(i.get("prod")) or {}
            items.append({"prod": i.get("prod"), "product_id": prod.get("id"), "name": prod.get("name") or i.get("prod_name"), "model": prod.get("model") or i.get("model"), "sku": i.get("sku"), "batchnum": i.get("batchnum"),
                          "qty": round(_num(i.get("num")), 3), "unit": prod.get("unit"), "price": money(i.get("price")), "money": money(i.get("money")), "received": round(_num(i.get("backnum")), 3),
                          "tax_rate": i.get("tax_rate"), "tax_money": money(i.get("tax_money")), "memo": i.get("memo")})
        plans = [self.pay_plan_row(x) for x in self.rows(f"SELECT y.*, {RMB_EXPR.format(t='y')} rmb FROM pay_plan y WHERE y._deleted_at IS NULL AND y.pu_id = ? ORDER BY y.date, y.serial", [str(pid)])]
        returns = [{"id": x["id"], "date": x.get("date"), "subject": x.get("subject"), "return_no": x.get("return_no"), "status": x.get("status"), "money": money(x.get("money")), "money_type": x.get("money_type") or "RMB",
                    "who": x.get("who_name") or x.get("who"), "memo": x.get("memo")} for x in self.rows("SELECT * FROM purchase_return WHERE _deleted_at IS NULL AND pu_id = ? ORDER BY date DESC", [str(pid)])]
        extras = self.raw_extras("purchase", pid, set(r.keys()) | {"puritem", "cu_id", "cu_sn"})
        return {"purchase": self.purchase_row(r), "items": items, "plans": plans, "returns": returns, "extras": extras}

    def pay_plan_row(self, g: Dict[str, Any]) -> Dict[str, Any]:
        overdue = 0
        if str(g.get("status")) == "0" and isinstance(g.get("date"), str) and len(g["date"]) == 10:
            try:
                overdue = (self.today - dt.date.fromisoformat(g["date"])).days
            except ValueError:
                overdue = 0
        return {
            "id": g["id"], "date": g.get("date"), "serial": g.get("serial"), "money": money(g.get("money")), "money_type": g.get("money_type") or "RMB", "rmb": round(_num(g.get("rmb")), 2),
            "status": g.get("status"), "status_text": self.lk.text_or("pay_plan", "status", g.get("status"), PAY_PLAN_STATUS_FALLBACK),
            "type_text": self.lk.text_known("pay_plan", "type", g.get("type")), "ctype_text": self.lk.text_known("pay_plan", "ctype", g.get("ctype")),
            "who": g.get("who"), "owner": g.get("owner"), "supplier": self.lk.customer(g.get("cu_sn")), "purchase_id": _int(g.get("pu_id"), 0) or None, "purchase_no": g.get("purchase_no"),
            "purchase_title": g.get("purchase_title"), "exp_date": g.get("exp_date"), "memo": g.get("memo"), "overdue_days": max(overdue, 0), "bill_num": g.get("bill_num"),
        }

    def pay_plans(self) -> Dict[str, Any]:
        clauses, args = ["y._deleted_at IS NULL"], []
        status = self.get("status", "open")
        if status == "open":
            clauses.append("y.status = '0'")
        elif status == "overdue":
            clauses.append("y.status = '0' AND y.date < ?")
            args.append(self.today.isoformat())
        elif status == "done":
            clauses.append("y.status = '1'")
        if self.get("who"):
            clauses.append("(y.who = ? OR y.owner = ?)")
            args.extend([self.lk.part_to_name(self.get("who"))] * 2)
        self.customer_clause("y", clauses, args)
        if self.get("supplier_id"):
            keys = self.customer_keys(_int(self.get("supplier_id")))
            clauses.append(f"y.cu_sn IN ({','.join('?' * len(keys))})")
            args.extend(keys)
        if self.get("purchase_id"):
            clauses.append("y.pu_id = ?")
            args.append(self.get("purchase_id"))
        self.date_clause("y", clauses, args)
        q = self.get("q")
        if q:
            args.extend([f"%{q}%", f"%{q}%"])
            clauses.append(f"(y.memo LIKE ? OR y.pu_id IN (SELECT CAST(id AS TEXT) FROM purchase WHERE no_ LIKE ?) OR {self.name_search_clause('y', q, args)})")
        where = " WHERE " + " AND ".join(clauses)
        rmb = RMB_EXPR.format(t="y")
        page, size, offset = self.page()
        total = self.one(f"SELECT COUNT(*) n, SUM({rmb}) a FROM pay_plan y{where}", args) or {}
        by_currency = [{"money_type": r["money_type"] or "RMB", "count": r["n"], "amount": money(r["a"]), "rmb": money(r["r"])} for r in self.rows(
            f"SELECT y.money_type, COUNT(*) n, SUM(CAST(y.money AS REAL)) a, SUM({rmb}) r FROM pay_plan y{where} GROUP BY y.money_type ORDER BY r DESC", args)]
        overdue = self.one(f"SELECT COUNT(*) n, SUM({rmb}) a FROM pay_plan y{where} AND y.status = '0' AND y.date < ?", [*args, self.today.isoformat()]) or {}
        by_month = [{"month": r["m"], "count": r["n"], "rmb": money(r["r"]), "open_rmb": money(r["o"])} for r in self.rows(
            f"SELECT substr(y.date, 1, 7) m, COUNT(*) n, SUM({rmb}) r, SUM(CASE WHEN y.status = '0' THEN {rmb} ELSE 0 END) o FROM pay_plan y{where} GROUP BY m ORDER BY m DESC LIMIT 24", args)][::-1]
        sort = {"amount": f"{rmb} DESC", "date_desc": "y.date DESC, y.id DESC"}.get(self.get("sort"), "y.date ASC, y.id ASC")
        rows = self.rows(f"SELECT y.*, {rmb} rmb, u.no_ purchase_no, u.title purchase_title FROM pay_plan y LEFT JOIN purchase u ON u.id = CAST(y.pu_id AS INTEGER){where} ORDER BY {sort} LIMIT ? OFFSET ?", [*args, size, offset])
        return {"total": total.get("n") or 0, "rmb": money(total.get("a")), "page": page, "size": size, "by_currency": by_currency, "by_month": by_month,
                "overdue": {"count": overdue.get("n") or 0, "rmb": money(overdue.get("a"))}, "rows": [self.pay_plan_row(g) for g in rows]}

    def cashflow(self) -> Dict[str, Any]:
        """近 N 个月：订单额、回款、采购额、已付付款计划、未付付款计划（按计划月份），均折算人民币。"""
        n = min(max(_int(self.get("months"), 24), 3), 120)
        months = month_range(self.today.strftime("%Y-%m"), n)
        start = months[0] + "-01"
        out = {m: {"month": m, "sales": 0.0, "receipts": 0.0, "purchases": 0.0, "paid": 0.0, "open": 0.0, "orders": 0, "purchase_orders": 0} for m in months}

        def fill(sql: str, key: str, count_key: Optional[str] = None) -> None:
            for r in self.rows(sql, [start]):
                if r["m"] in out:
                    out[r["m"]][key] = money(r["a"])
                    if count_key:
                        out[r["m"]][count_key] = r["n"]

        fill(f"SELECT substr(o.date, 1, 7) m, COUNT(*) n, SUM({ORDER_RMB_EXPR}) a FROM contract o WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.date >= ? GROUP BY m", "sales", "orders")
        fill("SELECT substr(date, 1, 7) m, COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? GROUP BY m", "receipts")
        fill(f"SELECT substr(u.date, 1, 7) m, COUNT(*) n, SUM({RMB_EXPR.format(t='u')}) a FROM purchase u WHERE u._deleted_at IS NULL AND u.date >= ? GROUP BY m", "purchases", "purchase_orders")
        fill(f"SELECT substr(y.date, 1, 7) m, COUNT(*) n, SUM({RMB_EXPR.format(t='y')}) a FROM pay_plan y WHERE y._deleted_at IS NULL AND y.status = '1' AND y.date >= ? GROUP BY m", "paid")
        fill(f"SELECT substr(y.date, 1, 7) m, COUNT(*) n, SUM({RMB_EXPR.format(t='y')}) a FROM pay_plan y WHERE y._deleted_at IS NULL AND y.status = '0' AND y.date >= ? GROUP BY m", "open")
        upcoming = [{"month": r["m"], "count": r["n"], "rmb": money(r["a"])} for r in self.rows(
            f"SELECT substr(y.date, 1, 7) m, COUNT(*) n, SUM({RMB_EXPR.format(t='y')}) a FROM pay_plan y WHERE y._deleted_at IS NULL AND y.status = '0' AND y.date >= ? GROUP BY m ORDER BY m LIMIT 12",
            [self.today.strftime("%Y-%m") + "-01"])]
        open_total = self.one(f"SELECT COUNT(*) n, SUM({RMB_EXPR.format(t='y')}) a FROM pay_plan y WHERE y._deleted_at IS NULL AND y.status = '0'") or {}
        open_recv = self.one(f"SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering WHERE _deleted_at IS NULL AND status {OPEN_PLAN_SQL}") or {}
        rows = list(out.values())
        return {"months": n, "rows": rows,
                "totals": {k: round(sum(r[k] for r in rows), 2) for k in ("sales", "receipts", "purchases", "paid", "open")},
                "open_payments": {"count": open_total.get("n") or 0, "rmb": money(open_total.get("a"))}, "open_receivables": {"count": open_recv.get("n") or 0, "amount": money(open_recv.get("a"))},
                "upcoming": upcoming}

    # ------------------------------------------------------------------ 联系人
    MISSING_SQL = "COALESCE(k.mphone,'') = '' AND COALESCE(k.phone,'') = '' AND COALESCE(k.weixin,'') = '' AND COALESCE(k.qq,'') = '' AND COALESCE(k.email,'') = ''"

    def contacts(self) -> Dict[str, Any]:
        clauses, args = ["c._deleted_at IS NULL"], []
        q = self.get("q")
        if q:
            args.extend([f"%{q}%"] * 6)
            clauses.append("(k.name LIKE ? OR k.mphone LIKE ? OR k.phone LIKE ? OR k.weixin LIKE ? OR k.email LIKE ? OR c.cu_name LIKE ?)")
        if self.get("owner"):
            clauses.append("c.owner = ?")
            args.append(self.get("owner"))
        if self.get("customer_id"):
            clauses.append("k.customer_id = ?")
            args.append(_int(self.get("customer_id")))
        if self.get("missing") in ("1", "true", "on"):
            clauses.append(self.MISSING_SQL)
        if self.get("headship"):
            clauses.append("k.headship LIKE ?")
            args.append(f"%{self.get('headship')}%")
        where = " WHERE " + " AND ".join(clauses)
        cte = ("WITH la AS (SELECT CAST(con_id AS INTEGER) cid, MAX(date) last_date, COUNT(*) n FROM action WHERE _deleted_at IS NULL AND con_id <> '' AND con_id <> '0' "
               "AND date LIKE '____-__-__' AND date <= ? GROUP BY cid)")
        base = f"{cte} SELECT {{cols}} FROM contact k JOIN customer c ON c.id = k.customer_id LEFT JOIN la ON la.cid = k.id{where}"
        page, size, offset = self.page()
        summary = self.one(base.format(cols=f"COUNT(*) n, SUM(CASE WHEN {self.MISSING_SQL} THEN 1 ELSE 0 END) missing, SUM(CASE WHEN la.cid IS NULL THEN 1 ELSE 0 END) never"), [self.today.isoformat(), *args]) or {}
        by_owner = [{"owner": self.lk.user_name(r["o"]), "part": r["o"], "count": r["n"], "missing": r["m"]} for r in self.rows(
            base.format(cols=f"c.owner o, COUNT(*) n, SUM(CASE WHEN {self.MISSING_SQL} THEN 1 ELSE 0 END) m") + " GROUP BY c.owner ORDER BY m DESC, n DESC LIMIT 15", [self.today.isoformat(), *args])]
        sort = {"last": "la.last_date DESC NULLS LAST, c.cu_name, k._seq", "name": "k.name COLLATE NOCASE, c.cu_name", "actions": "la.n DESC NULLS LAST, c.cu_name"}.get(self.get("sort"), "c.cu_name COLLATE NOCASE, k._seq")
        rows = self.rows(base.format(cols="k.*, c.id customer_id2, c.cu_name, c.m_name, c.owner, la.last_date, la.n actions") + f" ORDER BY {sort} LIMIT ? OFFSET ?", [self.today.isoformat(), *args, size, offset])
        return {"total": summary.get("n") or 0, "missing": summary.get("missing") or 0, "never_contacted": summary.get("never") or 0, "page": page, "size": size, "by_owner": by_owner,
                "rows": [self.contact_row(k) for k in rows]}

    def contact_row(self, k: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": k["id"], "name": k.get("name"), "headship": k.get("headship"), "department": k.get("department"), "mphone": k.get("mphone"), "phone": k.get("phone"),
            "weixin": k.get("weixin"), "qq": k.get("qq"), "email": k.get("email"), "sex": k.get("sex"), "remark": k.get("remark"),
            "missing": not any(k.get(f) for f in ("mphone", "phone", "weixin", "qq", "email")),
            "customer": {"id": k.get("customer_id"), "name": k.get("cu_name") or k.get("m_name") or "", "owner": self.lk.user_name(k.get("owner"))},
            "last_contact": k.get("last_date"), "actions": k.get("actions") or 0,
        }
