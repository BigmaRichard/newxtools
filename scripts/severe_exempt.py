#!/usr/bin/env python3
"""严重逾期标记的手工解除名单（data/severe_exempt.json）：

    scripts/severe_exempt.py list
    scripts/severe_exempt.py add "兰州肽库生物技术有限公司" --note "已协商分期"     # 客户名（精确）或客户 id
    scripts/severe_exempt.py remove 11208

改完前台立即生效（按文件修改时间热加载），不用重启服务。名单不进镜像库、不进 Git。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.server import Mirror  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(ROOT / "data" / "xtools_mirror.sqlite"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = sub.add_parser("add"); a.add_argument("customer"); a.add_argument("--note", default="")
    r = sub.add_parser("remove"); r.add_argument("customer")
    ns = ap.parse_args()

    mirror = Mirror(ns.db)
    conn = mirror.connect()
    lk = mirror.lookups(conn)
    if ns.cmd == "list":
        rows = mirror.exempt.all()
        for e in rows:
            raw = lk.severe_raw(e["id"])
            print(f"{e['id']:>6}  {e['name']}  自 {e['since']}  {e['note']}  " + (f"（本应标记：最久逾期 {raw['days']} 天 · {raw['count']} 期 {raw['amount']:,.0f}）" if raw else "（当前已无逾期超 90 天的计划）"))
        print(f"共 {len(rows)} 家")
        return 0
    key = ns.customer.strip()
    hits = [c for c in lk.customers.values() if str(c["id"]) == key or (c.get("cu_name") or "") == key or (c.get("m_name") or "") == key]
    if not hits:
        like = [c for c in lk.customers.values() if key in (c.get("cu_name") or "")]
        print(f"找不到客户「{key}」" + (f"；名字里含它的有：{'、'.join(c['cu_name'] + '(' + str(c['id']) + ')' for c in like[:8])}" if like else ""))
        return 1
    if len(hits) > 1:
        print("匹配到多家，请用 id：" + "、".join(f"{c['cu_name']}({c['id']})" for c in hits))
        return 1
    c = hits[0]
    if ns.cmd == "add":
        e = mirror.exempt.add(c["id"], c.get("cu_name") or c.get("m_name") or "", ns.note)
        raw = lk.severe_raw(c["id"])
        print(f"已解除：{e['name']}（{e['id']}）自 {e['since']}" + (f"；本应标记：最久逾期 {raw['days']} 天 · {raw['count']} 期 {raw['amount']:,.0f}" if raw else "；该客户当前本来也没有逾期超 90 天的计划"))
    else:
        print(("已恢复标记：" if mirror.exempt.remove(c["id"]) else "本来就不在解除名单里：") + f"{c.get('cu_name')}（{c['id']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
