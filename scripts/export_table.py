#!/usr/bin/env python3
"""按 lastid 全量或增量导出任一读取表为 JSONL（每行一条），作为本地镜像与数据核对的起点。

用法：
    python scripts/export_table.py customer --extend 1                 # 全量
    python scripts/export_table.py customer --lasttime "2026-09-01"    # 增量（支持 lasttime 的表）
    python scripts/export_table.py contract --filter status=1 --filter st_send=2
    python scripts/export_table.py product --out data/product.jsonl --max-pages 5

支持 lasttime 增量的表（依据文档）：customer、product、libout、sr_notice、cost。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xtools import XTools  # noqa: E402


def parse_filter(items):
    result = {}
    for item in items or []:
        key, _, value = item.partition("=")
        if not key:
            continue
        result[key] = int(value) if value.lstrip("-").isdigit() else value
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dt", help="数据表分类，如 customer / contract / product / gathering_note")
    parser.add_argument("--out", help="输出文件，缺省 data/<dt>.jsonl")
    parser.add_argument("--lastid", type=int, default=0)
    parser.add_argument("--lasttime", help="最后修改时间起点，如 2026-09-01 或 2026-09-01 08:00:00")
    parser.add_argument("--extend", type=int, help="extend=1 读取扩展字段")
    parser.add_argument("--filter", action="append", help="附加过滤，如 status=1，可多次")
    parser.add_argument("--max-pages", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    params = parse_filter(args.filter)
    if args.lasttime:
        params["lasttime"] = args.lasttime
    if args.extend is not None:
        params["extend"] = args.extend

    out = Path(args.out or f"data/{args.dt}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)

    xt = XTools()
    count = 0
    with out.open("w", encoding="utf-8") as fh:
        for row in xt.client.iter_output(args.dt, lastid=args.lastid, max_pages=args.max_pages, **params):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    print(f"导出完成：{count} 条 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
