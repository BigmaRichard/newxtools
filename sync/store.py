"""P0 只读镜像：SQLite 存储层。

表结构：
    raw_records     原始 JSON（dt + id 主键），含 source_hash / first_seen / updated_at / fetched_at / deleted_at
    sync_state      每表游标：lastid、lasttime、last_full_at、last_run_at、last_status、last_rows、last_error，
                    以及全量拉取断点 full_progress（已写入的最大 id）/ full_started_at（本轮全量开始时间），完成后清空
    dictionaries    数据字典（dt, field, key → value, flag）
    field_names     字段中文名（dt, field → name）
    crm_user 等     规范化表：由 specs.TABLE_SPECS 定义，列名由 JSON 键清洗而来，值一律以文本存储（SQLite 动态类型）
    customer_ext    客户自定义字段：列按首次出现的键动态添加
    v_*             报表视图
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .specs import TABLE_SPECS, TableSpec

_COL_RE = re.compile(r"[^0-9A-Za-z_]")


def col_name(key: str) -> str:
    """JSON 键 → 列名："No." → no_，其余非法字符替换为下划线。"""
    if key == "No.":
        return "no_"
    name = _COL_RE.sub("_", key).strip("_")
    if not name or name[0].isdigit():
        name = "f_" + name
    return name


def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def record_hash(record: Dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def record_id(record: Dict[str, Any]) -> Optional[int]:
    raw = str(record.get("id", "")).strip()
    try:
        return int(raw)
    except ValueError:
        return None


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=120)  # 与同步 / 前台并发时等待写锁
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._ensure_schema()

    # ------------------------------------------------------------------ schema
    def _ensure_schema(self) -> None:
        c = self.conn
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_records (
                dt TEXT NOT NULL, id INTEGER NOT NULL, data TEXT NOT NULL, source_hash TEXT NOT NULL,
                first_seen TEXT NOT NULL, updated_at TEXT NOT NULL, fetched_at TEXT NOT NULL, deleted_at TEXT,
                PRIMARY KEY (dt, id)
            );
            CREATE INDEX IF NOT EXISTS ix_raw_updated ON raw_records (dt, updated_at);
            CREATE TABLE IF NOT EXISTS sync_state (
                dt TEXT PRIMARY KEY, lastid INTEGER DEFAULT 0, lasttime TEXT, last_full_at TEXT, last_run_at TEXT,
                last_status TEXT, last_rows INTEGER DEFAULT 0, last_error TEXT, total_rows INTEGER DEFAULT 0,
                full_progress INTEGER, full_started_at TEXT
            );
            CREATE TABLE IF NOT EXISTS dictionaries (
                dt TEXT NOT NULL, field TEXT NOT NULL, key TEXT NOT NULL, value TEXT, flag TEXT, fetched_at TEXT,
                PRIMARY KEY (dt, field, key)
            );
            CREATE TABLE IF NOT EXISTS field_names (
                dt TEXT NOT NULL, field TEXT NOT NULL, name TEXT, fetched_at TEXT, PRIMARY KEY (dt, field)
            );
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT, mode TEXT, dt TEXT,
                rows INTEGER, inserted INTEGER, updated INTEGER, deleted INTEGER, status TEXT, error TEXT
            );
            """
        )
        # 旧库补列：全量拉取断点（0.3.1 起）
        existing = {r[1] for r in c.execute("PRAGMA table_info(sync_state)")}
        for col, typ in (("full_progress", "INTEGER"), ("full_started_at", "TEXT")):
            if col not in existing:
                c.execute(f"ALTER TABLE sync_state ADD COLUMN {col} {typ}")
        for spec in TABLE_SPECS:
            self._ensure_normalized_table(spec)
        self._ensure_indexes()
        self._ensure_views()
        c.commit()

    #: 规范化表的查询索引（报表视图与本地前台使用）
    INDEXES = {
        "customer": ["sn", "cu_name", "owner", "life"],
        "contract": ["cu_sn", "date", "no_", "who", "status"],
        "contract_goods": ["prod"],
        "gathering_note": ["co_id", "cu_sn", "date", "who"],
        "gathering": ["co_sn", "cu_sn", "date", "status", "who"],
        "action": ["date", "cu_sn", "who"],
        "sendgoods": ["co_id", "cu_sn", "date"],
        "libout": ["co_sn", "cu_sn", "date"],
        "product": ["sn"],
    }

    def _ensure_indexes(self) -> None:
        for table, cols in self.INDEXES.items():
            existing = {r[1] for r in self.conn.execute(f'PRAGMA table_info("{table}")')}
            for col in cols:
                if col in existing:
                    self.conn.execute(f'CREATE INDEX IF NOT EXISTS "ix_{table}_{col}" ON "{table}" ("{col}")')

    def _ensure_normalized_table(self, spec: TableSpec) -> None:
        cols = ", ".join(f'"{col_name(k)}" TEXT' for k in spec.columns)
        cols = (", " + cols) if cols else ""
        self.conn.execute(
            f'CREATE TABLE IF NOT EXISTS "{spec.table}" (id INTEGER PRIMARY KEY{cols}, "_updated_at" TEXT, "_deleted_at" TEXT)'
        )
        for child in spec.children:
            ccols = ", ".join(f'"{col_name(k)}" TEXT' for k in child.columns)
            self.conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{child.table}" (id INTEGER, "{child.parent_col}" INTEGER NOT NULL, {ccols}, "_seq" INTEGER)'
            )
            self.conn.execute(f'CREATE INDEX IF NOT EXISTS "ix_{child.table}_parent" ON "{child.table}" ("{child.parent_col}")')
        # 已存在的表补列（规格新增列时）
        existing = {r[1] for r in self.conn.execute(f'PRAGMA table_info("{spec.table}")')}
        for k in spec.columns:
            if col_name(k) not in existing:
                self.conn.execute(f'ALTER TABLE "{spec.table}" ADD COLUMN "{col_name(k)}" TEXT')
        for child in spec.children:
            existing = {r[1] for r in self.conn.execute(f'PRAGMA table_info("{child.table}")')}
            for k in child.columns:
                if col_name(k) not in existing:
                    self.conn.execute(f'ALTER TABLE "{child.table}" ADD COLUMN "{col_name(k)}" TEXT')

    @staticmethod
    def customer_id_expr(alias: str) -> str:
        """把 cu_sn（"[id:N]" 或客户编号 sn）解析为 customer.id 的 SQL 表达式；两种形式都走索引。"""
        return (f"CASE WHEN {alias}.cu_sn LIKE '[id:%]' THEN CAST(substr({alias}.cu_sn, 5, length({alias}.cu_sn) - 5) AS INTEGER) "
                f"ELSE (SELECT s.id FROM customer s WHERE s.sn = {alias}.cu_sn AND s.sn <> '' LIMIT 1) END")

    def _ensure_views(self) -> None:
        cust_join = "LEFT JOIN customer c ON c.id = " + self.customer_id_expr("{t}")
        views = {
            "v_contract": f"""
                SELECT o.id, o.no_ AS order_no, o.subject, o.cu_sn, c.id AS customer_id, c.cu_name, o.status, o.confirm, o.st_send,
                       CAST(o.sum AS REAL) AS amount, o.who, o.date, o.end_date, o.money_type, o.payment, o.pay_mode, o.memo,
                       o._updated_at
                FROM contract o {cust_join.format(t='o')}
                WHERE o._deleted_at IS NULL""",
            "v_contract_goods": """
                SELECT g.contract_id, o.no_ AS order_no, o.date, o.cu_sn, g.prod, COALESCE(p.name, g.prod_name) AS product_name,
                       COALESCE(p.model, g.model) AS model, CAST(g.amount AS REAL) AS amount, CAST(g.un_price AS REAL) AS unit_price,
                       CAST(g.sum AS REAL) AS amount_sum, CAST(g.tax_money AS REAL) AS tax_money, g.memo
                FROM contract_goods g
                JOIN contract o ON o.id = g.contract_id
                LEFT JOIN product p ON p.sn = g.prod AND p.sn <> ''
                WHERE o._deleted_at IS NULL""",
            "v_receipt": f"""
                SELECT n.id, n.cu_sn, c.id AS customer_id, c.cu_name, n.co_id, n.date, CAST(n.money AS REAL) AS money,
                       n.type, n.invoice, n.serial, n.who, n.memo, n.money_type
                FROM gathering_note n {cust_join.format(t='n')}
                WHERE n._deleted_at IS NULL""",
            "v_monthly_sales": """
                SELECT substr(date, 1, 7) AS month, COUNT(*) AS orders, SUM(CAST(sum AS REAL)) AS amount
                FROM contract WHERE _deleted_at IS NULL AND date IS NOT NULL AND date <> ''
                GROUP BY substr(date, 1, 7) ORDER BY month""",
            "v_monthly_receipt": """
                SELECT substr(date, 1, 7) AS month, COUNT(*) AS receipts, SUM(CAST(money AS REAL)) AS money
                FROM gathering_note WHERE _deleted_at IS NULL AND date IS NOT NULL AND date <> ''
                GROUP BY substr(date, 1, 7) ORDER BY month""",
            "v_customer_overview": """
                SELECT c.id, c.sn, c.cu_name, c.life, c.cu_status, c.owner, c.state, c.city, c.creatdate, c.moddate,
                       (SELECT COUNT(*) FROM contract o WHERE o._deleted_at IS NULL AND (o.cu_sn = '[id:' || c.id || ']' OR (c.sn <> '' AND o.cu_sn = c.sn))) AS orders,
                       (SELECT SUM(CAST(o.sum AS REAL)) FROM contract o WHERE o._deleted_at IS NULL AND (o.cu_sn = '[id:' || c.id || ']' OR (c.sn <> '' AND o.cu_sn = c.sn))) AS order_amount,
                       (SELECT SUM(CAST(n.money AS REAL)) FROM gathering_note n WHERE n._deleted_at IS NULL AND (n.cu_sn = '[id:' || c.id || ']' OR (c.sn <> '' AND n.cu_sn = c.sn))) AS receipt_amount,
                       (SELECT COUNT(*) FROM contact k WHERE k.customer_id = c.id) AS contacts
                FROM customer c WHERE c._deleted_at IS NULL""",
            "v_receivable": """
                SELECT g.id, g.cu_sn, g.co_sn, g.date AS plan_date, g.serial, CAST(g.money AS REAL) AS money, g.status, g.who, g.memo
                FROM gathering g WHERE g._deleted_at IS NULL""",
        }
        for name, sql in views.items():
            self.conn.execute(f"DROP VIEW IF EXISTS {name}")
            self.conn.execute(f"CREATE VIEW {name} AS {sql}")

    # ------------------------------------------------------------------ sync_state
    STATE_FIELDS = ("lastid", "lasttime", "last_full_at", "last_run_at", "last_status", "last_rows", "last_error",
                    "total_rows", "full_progress", "full_started_at")

    def get_state(self, dt_name: str) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM sync_state WHERE dt = ?", (dt_name,)).fetchone()
        if row is None:
            return {"dt": dt_name, "lastid": 0, "lasttime": None, "last_full_at": None, "last_run_at": None,
                    "last_status": None, "last_rows": 0, "last_error": None, "total_rows": 0,
                    "full_progress": None, "full_started_at": None}
        return dict(row)

    def set_state(self, dt_name: str, **fields: Any) -> None:
        state = self.get_state(dt_name)
        state.update(fields)
        state["total_rows"] = self.count_raw(dt_name)
        cols = ("dt", *self.STATE_FIELDS)
        self.conn.execute(
            f"INSERT INTO sync_state ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)}) "
            "ON CONFLICT(dt) DO UPDATE SET " + ", ".join(f"{c}=excluded.{c}" for c in self.STATE_FIELDS),
            state,
        )
        self.conn.commit()

    def checkpoint(self, dt_name: str, **fields: Any) -> None:
        """全量 / 增量拉取过程中的轻量断点（只更新给定列，不重算行数）。"""
        if self.conn.execute("SELECT 1 FROM sync_state WHERE dt = ?", (dt_name,)).fetchone() is None:
            self.set_state(dt_name, **fields)
            return
        self.conn.execute(
            f"UPDATE sync_state SET {', '.join(f'{c} = :{c}' for c in fields)} WHERE dt = :dt",
            {"dt": dt_name, **fields},
        )
        self.conn.commit()

    def min_first_seen(self, dt_name: str) -> Optional[str]:
        row = self.conn.execute("SELECT MIN(first_seen) FROM raw_records WHERE dt = ?", (dt_name,)).fetchone()
        return row[0] if row and row[0] else None

    def all_states(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM sync_state ORDER BY dt")]

    def log_run(self, **fields: Any) -> None:
        keys = ["started_at", "finished_at", "mode", "dt", "rows", "inserted", "updated", "deleted", "status", "error"]
        self.conn.execute(
            f"INSERT INTO sync_log ({', '.join(keys)}) VALUES ({', '.join(':' + k for k in keys)})",
            {k: fields.get(k) for k in keys},
        )
        self.conn.commit()

    # ------------------------------------------------------------------ raw
    def count_raw(self, dt_name: str, include_deleted: bool = False) -> int:
        sql = "SELECT COUNT(*) FROM raw_records WHERE dt = ?" + ("" if include_deleted else " AND deleted_at IS NULL")
        return int(self.conn.execute(sql, (dt_name,)).fetchone()[0])

    def raw_ids(self, dt_name: str, include_deleted: bool = False) -> Set[int]:
        sql = "SELECT id FROM raw_records WHERE dt = ?" + ("" if include_deleted else " AND deleted_at IS NULL")
        return {int(r[0]) for r in self.conn.execute(sql, (dt_name,))}

    def max_raw_id(self, dt_name: str) -> int:
        row = self.conn.execute("SELECT MAX(id) FROM raw_records WHERE dt = ?", (dt_name,)).fetchone()
        return int(row[0] or 0)

    def upsert_raw(self, dt_name: str, records: Iterable[Dict[str, Any]]) -> Tuple[int, int, int, List[Dict[str, Any]]]:
        """写入原始记录；返回 (新增数, 更新数, 未变数, 有变化的记录列表)。"""
        ts = now_iso()
        inserted = updated = unchanged = 0
        changed: List[Dict[str, Any]] = []
        cur = self.conn.cursor()
        for rec in records:
            rid = record_id(rec)
            if rid is None:
                continue
            h = record_hash(rec)
            row = cur.execute("SELECT source_hash, deleted_at FROM raw_records WHERE dt = ? AND id = ?", (dt_name, rid)).fetchone()
            if row is None:
                cur.execute(
                    "INSERT INTO raw_records (dt, id, data, source_hash, first_seen, updated_at, fetched_at, deleted_at) VALUES (?,?,?,?,?,?,?,NULL)",
                    (dt_name, rid, json.dumps(rec, ensure_ascii=False, separators=(",", ":")), h, ts, ts, ts),
                )
                inserted += 1
                changed.append(rec)
            elif row[0] != h or row[1] is not None:
                cur.execute(
                    "UPDATE raw_records SET data = ?, source_hash = ?, updated_at = ?, fetched_at = ?, deleted_at = NULL WHERE dt = ? AND id = ?",
                    (json.dumps(rec, ensure_ascii=False, separators=(",", ":")), h, ts, ts, dt_name, rid),
                )
                updated += 1
                changed.append(rec)
            else:
                cur.execute("UPDATE raw_records SET fetched_at = ? WHERE dt = ? AND id = ?", (ts, dt_name, rid))
                unchanged += 1
        self.conn.commit()
        return inserted, updated, unchanged, changed

    def mark_deleted(self, dt_name: str, ids: Iterable[int]) -> int:
        ids = list(ids)
        if not ids:
            return 0
        ts = now_iso()
        cur = self.conn.cursor()
        for i in range(0, len(ids), 500):
            chunk = ids[i : i + 500]
            marks = ",".join("?" * len(chunk))
            cur.execute(f"UPDATE raw_records SET deleted_at = ? WHERE dt = ? AND id IN ({marks}) AND deleted_at IS NULL", (ts, dt_name, *chunk))
        self.conn.commit()
        return len(ids)

    def iter_raw(self, dt_name: str) -> Iterable[Dict[str, Any]]:
        for row in self.conn.execute("SELECT data FROM raw_records WHERE dt = ? AND deleted_at IS NULL ORDER BY id", (dt_name,)):
            yield json.loads(row[0])

    # ------------------------------------------------------------------ normalized
    @staticmethod
    def _as_list(value: Any) -> List[Dict[str, Any]]:
        if value is None or value == "" or value == 0:
            return []
        if isinstance(value, dict):
            vals = list(value.values())
            return [v for v in vals if isinstance(v, dict)]
        if isinstance(value, list):
            return [v for v in value if isinstance(v, dict)]
        return []

    @staticmethod
    def _text(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return str(value)

    def upsert_normalized(self, spec: TableSpec, records: Sequence[Dict[str, Any]]) -> int:
        if not records:
            return 0
        ts = now_iso()
        cur = self.conn.cursor()
        if spec.dt == "customerext":
            self._upsert_dynamic(spec.table, records, ts)
            return len(records)
        cols = [col_name(k) for k in spec.columns]
        placeholders = ", ".join("?" * (len(cols) + 2))
        col_sql = ", ".join(f'"{c}"' for c in ["id", *cols, "_updated_at"])
        n = 0
        for rec in records:
            rid = record_id(rec)
            if rid is None:
                continue
            values = [rid, *[self._text(rec.get(k)) for k in spec.columns], ts]
            cur.execute(f'INSERT OR REPLACE INTO "{spec.table}" ({col_sql}, "_deleted_at") VALUES ({placeholders}, NULL)', values)
            for child in spec.children:
                cur.execute(f'DELETE FROM "{child.table}" WHERE "{child.parent_col}" = ?', (rid,))
                ccols = [col_name(k) for k in child.columns]
                ccol_sql = ", ".join(f'"{c}"' for c in ["id", child.parent_col, *ccols, "_seq"])
                cph = ", ".join("?" * (len(ccols) + 3))
                for seq, item in enumerate(self._as_list(rec.get(child.key))):
                    cur.execute(
                        f'INSERT INTO "{child.table}" ({ccol_sql}) VALUES ({cph})',
                        [record_id(item), rid, *[self._text(item.get(k)) for k in child.columns], seq],
                    )
            n += 1
        self.conn.commit()
        return n

    def _upsert_dynamic(self, table: str, records: Sequence[Dict[str, Any]], ts: str) -> None:
        """customer_ext：列按记录中出现的键动态添加。"""
        cur = self.conn.cursor()
        existing = {r[1] for r in cur.execute(f'PRAGMA table_info("{table}")')}
        for rec in records:
            for k in rec.keys():
                c = col_name(k)
                if c != "id" and c not in existing:
                    cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{c}" TEXT')
                    existing.add(c)
        for rec in records:
            rid = record_id(rec)
            if rid is None:
                continue
            keys = [k for k in rec.keys() if col_name(k) != "id"]
            cols = ["id", *[col_name(k) for k in keys], "_updated_at"]
            values = [rid, *[self._text(rec[k]) for k in keys], ts]
            cur.execute(
                f'INSERT OR REPLACE INTO "{table}" ({", ".join(chr(34) + c + chr(34) for c in cols)}, "_deleted_at") VALUES ({", ".join("?" * len(cols))}, NULL)',
                values,
            )
        self.conn.commit()

    def mark_normalized_deleted(self, spec: TableSpec, ids: Iterable[int]) -> None:
        ids = list(ids)
        if not ids:
            return
        ts = now_iso()
        cur = self.conn.cursor()
        for i in range(0, len(ids), 500):
            chunk = ids[i : i + 500]
            marks = ",".join("?" * len(chunk))
            cur.execute(f'UPDATE "{spec.table}" SET "_deleted_at" = ? WHERE id IN ({marks})', (ts, *chunk))
        self.conn.commit()

    def rebuild_normalized(self, spec: TableSpec) -> int:
        cur = self.conn.cursor()
        cur.execute(f'DELETE FROM "{spec.table}"')
        for child in spec.children:
            cur.execute(f'DELETE FROM "{child.table}"')
        self.conn.commit()
        batch: List[Dict[str, Any]] = []
        total = 0
        for rec in self.iter_raw(spec.dt):
            batch.append(rec)
            if len(batch) >= 500:
                total += self.upsert_normalized(spec, batch)
                batch = []
        total += self.upsert_normalized(spec, batch)
        return total

    # ------------------------------------------------------------------ dictionaries
    def save_dictionary(self, dt_name: str, field_name: str, items: Sequence[Dict[str, Any]]) -> None:
        ts = now_iso()
        cur = self.conn.cursor()
        cur.execute("DELETE FROM dictionaries WHERE dt = ? AND field = ?", (dt_name, field_name))
        for it in items:
            cur.execute(
                "INSERT OR REPLACE INTO dictionaries (dt, field, key, value, flag, fetched_at) VALUES (?,?,?,?,?,?)",
                (dt_name, field_name, str(it.get("key")), self._text(it.get("value")), self._text(it.get("flag")), ts),
            )
        self.conn.commit()

    def save_field_names(self, dt_name: str, mapping: Dict[str, Any]) -> None:
        ts = now_iso()
        cur = self.conn.cursor()
        for k, v in mapping.items():
            cur.execute("INSERT OR REPLACE INTO field_names (dt, field, name, fetched_at) VALUES (?,?,?,?)", (dt_name, k, self._text(v), ts))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
