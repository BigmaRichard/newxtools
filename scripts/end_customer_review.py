"""最终客户核对表：把当前识别结果和“备注写了终端但对不上 CRM 档案”的订单导成 Excel，供人工核对后写进 data/end_customers.json。

用法：.venv/bin/python scripts/end_customer_review.py [输出路径]
缺省输出 data/最终客户核对_YYYYMMDD.xlsx（data/ 不进仓库）。
"""
from __future__ import annotations

import datetime as dt
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.end_customers import EndCustomerFile, EndCustomerIndex, build_map, from_memo  # noqa: E402
from web.xlsx import write_xlsx  # noqa: E402

DATA = ROOT / "data"
_HINT = re.compile(r"终端|最终客户|最终用户|直发客户")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / f"最终客户核对_{dt.date.today():%Y%m%d}.xlsx"
    conn = sqlite3.connect(f"file:{DATA / 'xtools_mirror.sqlite'}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    customers = {r["id"]: dict(r) for r in conn.execute("SELECT id, sn, cu_name, m_name, type, industry FROM customer WHERE _deleted_at IS NULL")}
    by_sn = {c["sn"]: cid for cid, c in customers.items() if c["sn"]}

    def own_id(cu: object) -> object:
        s = str(cu or "").strip()
        return int(s[4:-1]) if s.startswith("[id:") and s[4:-1].isdigit() else by_sn.get(s)

    orders = [dict(r) for r in conn.execute(
        "SELECT id, no_, date, cu_sn, sum, money_type, who, memo, addr FROM contract WHERE _deleted_at IS NULL AND status <> '3' ORDER BY date DESC, id DESC")]
    end_of, agents = build_map(customers, EndCustomerFile(DATA / "end_customers.json"), orders, own_id)
    name = lambda cid: (customers.get(cid) or {}).get("cu_name") or ""  # noqa: E731
    index = EndCustomerIndex(customers)

    found, open_rows = [], []
    for o in orders:
        own = own_id(o["cu_sn"])
        base = [o["date"], o["no_"], float(o["sum"] or 0), o["money_type"] or "RMB", o["who"], name(own), own]
        hit = end_of.get(o["id"])
        if hit:
            found.append(base + [name(hit[0]), hit[0], hit[1], "", (o["memo"] or "")[:200], (o["addr"] or "")[:120]])
            continue
        memo = o["memo"] or ""
        if not _HINT.search(memo):
            continue
        written = from_memo(memo) or ""
        cands = sorted({cid for core, lst in index.by_core.items() if written and (core in written or written in core) for cid, _ in lst})[:5] if written else []
        why = ("备注写的单位在 CRM 里有多个同名档案" if len(cands) > 1 else "备注写的是简称或与下单客户 / 代理商同名，没自动认；候选档案可能就是" if cands
               else "备注写了单位名但 CRM 里找不到" if written else "备注提到终端但没写单位名")
        open_rows.append(base + [written, why, "、".join(f"{name(c)}（{c}）" for c in cands), "", memo[:200], (o["addr"] or "")[:120]])

    summary: dict = {}
    for r in open_rows:
        if not r[7]:
            continue
        g = summary.setdefault(r[7], [r[7], 0, 0.0, r[8], r[9], set(), []])
        g[1] += 1
        g[2] = round(g[2] + r[2], 2)
        g[5].add(r[5])
        if len(g[6]) < 5:
            g[6].append(r[1])
    by_name = [[g[0], g[1], g[2], g[3], g[4], "、".join(sorted(g[5]))[:200], "、".join(g[6]), ""] for g in sorted(summary.values(), key=lambda g: -g[2])]

    head = ["日期", "单号", "金额", "币种", "业务员", "下单客户", "下单客户ID"]
    out.write_bytes(write_xlsx([
        ("已识别", head + ["最终客户", "最终客户ID", "依据", "核对（对 / 错 / 改为客户ID）", "备注", "收货地址"], found),
        ("待确认_按单位汇总", ["备注里写的终端", "单数", "金额", "原因", "候选档案", "下单客户", "单号示例", "最终客户ID（填 0 表示不算）"], by_name),
        ("待确认", head + ["备注里写的终端", "原因", "候选档案", "最终客户ID（填 0 表示不算）", "备注", "收货地址"], open_rows),
        ("代理商", ["客户ID", "客户"], [[cid, name(cid)] for cid in sorted(agents)]),
    ]))
    print(f"已识别 {len(found)} 单，待确认 {len(open_rows)} 单（{len(by_name)} 个单位名），代理商 {len(agents)} 家 → {out}")


if __name__ == "__main__":
    main()
