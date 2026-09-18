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

from sync.specs import DICT_FIELDS, FIELD_NAME_TABLES  # noqa: E402  字典字段清单与同步规格共用一份
from xtools import XTools, XToolsError  # noqa: E402

TABLES = list(dict.fromkeys([*FIELD_NAME_TABLES, *DICT_FIELDS.keys()]))


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
