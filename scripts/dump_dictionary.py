#!/usr/bin/env python3
"""导出数据字典、字段中文名与人员对照，写入 JSON 文件供映射与排错使用。

用法：
    python scripts/dump_dictionary.py                 # 输出到 ./dictionary/ 目录
    python scripts/dump_dictionary.py --out ./dict    # 指定目录

导出内容：
    users.json                    人员 part ↔ 姓名
    fields_<dt>.json              各表字段英文名 → 中文名（act=dbcn）
    dict_<dt>_<field>.json        指定字段的数据字典（key/value/flag）

未开通的表或字段会记录为失败而不中断。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xtools import XTools, XToolsError  # noqa: E402

TABLES = ["customer", "contract", "product", "gathering", "gathering_note", "bill", "sendgoods", "purchase", "action", "opport"]

# 文档中明确提到“参考数据字典”的字段（首批四模块）
DICT_FIELDS = {
    "customer": ["cu_status", "type", "cu_from", "employees", "industry", "life", "rala_rating", "country"],
    "contract": ["type", "status", "pay_mode", "payment", "one_select", "confirm", "st_send"],
    "product": ["unit", "pow_type", "class", "ptype", "status", "pmode"],
    "gathering_note": ["type", "ctype", "invoice"],
    "gathering": ["status", "type"],
    "bill": ["type"],
    "sendgoods": ["sntype", "package_type", "costtype", "status", "one_select"],
    "action": ["type", "cale"],
    "purchase": ["type", "status0"],
}


def dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dictionary")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    xt = XTools()
    failures = []

    try:
        dump(out / "users.json", xt.client.users())
        print("users.json 完成")
    except XToolsError as exc:
        failures.append(("users", str(exc)))

    for dt in TABLES:
        try:
            dump(out / f"fields_{dt}.json", xt.client.field_names(dt))
            print(f"fields_{dt}.json 完成")
        except XToolsError as exc:
            failures.append((f"fields_{dt}", str(exc)))
        for field in DICT_FIELDS.get(dt, []):
            try:
                dump(out / f"dict_{dt}_{field}.json", xt.client.dictionary(dt, field))
                print(f"dict_{dt}_{field}.json 完成")
            except XToolsError as exc:
                failures.append((f"dict_{dt}_{field}", str(exc)))

    if failures:
        print("\n以下项目未能导出（通常为未开通的表或该表没有此字段）：")
        for name, reason in failures:
            print(f"  - {name}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
