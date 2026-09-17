#!/usr/bin/env python3
"""本地前台：在本机启动只读 HTTP 服务，浏览器打开 http://127.0.0.1:8790 查看镜像数据。

用法：
    python scripts/web.py                       # 127.0.0.1:8790，库文件 data/xtools_mirror.sqlite
    python scripts/web.py --port 8800
    python scripts/web.py --db data/other.sqlite

常驻运行请用 scripts/install_launchd.py --web（退出后由 launchd 自动拉起）。服务只读，不向镜像库写入。
"""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sync.store import Store  # noqa: E402
from web import make_server  # noqa: E402

DEFAULT_PORT = 8790  # 8765 等常见端口容易与其他本机应用冲突


def main() -> int:
    parser = argparse.ArgumentParser(description="XTools 镜像本地前台")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，缺省只允许本机访问")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--db", default=str(ROOT / "data" / "xtools_mirror.sqlite"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    for handler in (logging.handlers.RotatingFileHandler(log_dir / "web.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"),
                    logging.StreamHandler(sys.stdout)):
        handler.setFormatter(fmt)
        root.addHandler(handler)

    if not Path(args.db).is_file():
        logging.error("未找到镜像库 %s，请先运行 scripts/sync.py --init", args.db)
        return 2
    # 启动时用同步层的 Store 检查一次库结构（补建索引与视图；若同步正在写库会等待其提交），之后全程只读
    Store(args.db).close()
    logging.info("镜像库结构与索引已检查")
    try:
        server = make_server(args.db, args.host, args.port)
    except OSError as exc:
        if exc.errno in (48, 98):  # macOS / Linux：Address already in use
            logging.error("端口 %d 已被其他程序占用，前台无法启动；请换一个端口：scripts/install_launchd.py --web --port 8801（或 scripts/web.py --port 8801）", args.port)
            return 3
        raise
    logging.info("前台已启动：http://%s:%d  库=%s", args.host, args.port, args.db)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
