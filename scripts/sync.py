#!/usr/bin/env python3
"""P0 只读镜像：把 XTools CRM 数据同步到本地 SQLite（只调用读取类接口）。

用法：
    python scripts/sync.py --init                  # 首次：全量拉取全部表 + 刷新字典
    python scripts/sync.py                         # 增量（launchd 定时调用的就是这一条）
    python scripts/sync.py --full                  # 强制全量重拉（含删除检测）
    python scripts/sync.py --table customer,contract   # 只同步指定表
    python scripts/sync.py --dict                  # 只刷新数据字典 / 字段中文名 / 人员对照
    python scripts/sync.py --rebuild               # 用原始 JSON 重建规范化表（规格改动后）
    python scripts/sync.py --status                # 查看各表游标与上次结果
    python scripts/sync.py --db data/other.sqlite  # 指定库文件（缺省 data/xtools_mirror.sqlite）

同一时刻只允许一个实例运行（锁文件 data/sync.lock），避免并发登录触发限频。日志写入 logs/sync.log 并输出到终端。
"""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import logging.handlers
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sync import SPEC_BY_DT, Store, Syncer, TABLE_SPECS  # noqa: E402
from xtools import XTools, XToolsConfig, XToolsError  # noqa: E402

SYNC_DEFAULT_TIMEOUT = 120  # 秒；.env 中 XTOOLS_TIMEOUT 优先


def setup_logging(verbose: bool) -> None:
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    fh = logging.handlers.RotatingFileHandler(log_dir / "sync.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(fh)
    root.addHandler(sh)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def print_status(store: Store) -> None:
    rows = store.all_states()
    if not rows:
        print("尚未同步过。")
        return
    print(f"{'表':<16}{'镜像行数':>8}  {'lastid':>8}  {'lasttime':<20}{'上次全量':<20}{'上次运行':<20}{'状态':<8}{'全量断点':>8}  错误")
    for r in rows:
        progress = r.get("full_progress")
        print(f"{r['dt']:<16}{r['total_rows']:>8}  {r['lastid'] or 0:>8}  {(r['lasttime'] or '')[:19]:<20}{(r['last_full_at'] or '')[:19]:<20}"
              f"{(r['last_run_at'] or '')[:19]:<20}{(r['last_status'] or ''):<8}{('' if progress is None else progress):>8}  {(r['last_error'] or '')[:60]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="XTools CRM → SQLite 只读镜像")
    parser.add_argument("--init", action="store_true", help="首次全量 + 字典")
    parser.add_argument("--full", action="store_true", help="强制全量重拉（含删除检测）")
    parser.add_argument("--dict", action="store_true", help="只刷新字典")
    parser.add_argument("--rebuild", action="store_true", help="用原始 JSON 重建规范化表")
    parser.add_argument("--status", action="store_true", help="显示同步状态")
    parser.add_argument("--table", help="逗号分隔的 dt 列表，如 customer,contract")
    parser.add_argument("--db", default=str(ROOT / "data" / "xtools_mirror.sqlite"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    log = logging.getLogger("xtools.sync.cli")

    store = Store(args.db)
    if args.status:
        print_status(store)
        return 0

    tables = [t.strip() for t in args.table.split(",")] if args.table else None
    if tables:
        unknown = [t for t in tables if t not in SPEC_BY_DT]
        if unknown:
            print("未知的表：", unknown, "可用：", [s.dt for s in TABLE_SPECS])
            return 2

    if args.rebuild:
        for spec in (SPEC_BY_DT[t] for t in tables) if tables else TABLE_SPECS:
            n = store.rebuild_normalized(spec)
            log.info("重建 %s：%d 行", spec.table, n)
        return 0

    lock_path = Path(args.db).parent / "sync.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = open(lock_path, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log.warning("已有同步进程在运行，本次退出")
        return 3

    try:
        # 正式公司订单等表带 extend=1 时单页可能超过 30 秒，同步默认超时 120 秒（.env 的 XTOOLS_TIMEOUT 优先）
        config = XToolsConfig.from_env(defaults={"timeout": SYNC_DEFAULT_TIMEOUT})
    except XToolsError as exc:
        log.error("配置错误：%s", exc)
        return 2
    log.info("开始：com=%s part=%s 库=%s 超时=%.0fs", config.com, config.part, args.db, config.timeout)
    xt = XTools(config)
    syncer = Syncer(xt, store)
    t0 = time.time()

    if args.dict or args.init:
        summary = syncer.refresh_dictionaries()
        if summary["failed"]:
            log.warning("字典刷新失败项：%s", "; ".join(summary["failed"]))
        if args.dict:
            return 0

    mode = "init" if args.init else ("full" if args.full else "incremental")
    results = syncer.run(mode, tables)
    errors = [r for r in results if r["status"] == "error"]
    total = sum(r["rows"] for r in results)
    log.info("结束：%d 张表，读取 %d 条，新增 %d，更新 %d，删除 %d，失败 %d，用时 %.0fs",
             len(results), total, sum(r["inserted"] for r in results), sum(r["updated"] for r in results),
             sum(r["deleted"] for r in results), len(errors), time.time() - t0)
    if errors:
        log.warning("失败的表：%s；已写入的数据保留，下次运行（含 launchd 定时）自动从断点续拉，也可立即重跑：python scripts/sync.py --table %s",
                    ", ".join(r["dt"] for r in errors), ",".join(r["dt"] for r in errors))
    if args.verbose:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
