#!/usr/bin/env python3
"""本地前台：启动只读 HTTP 服务，浏览器打开 http://127.0.0.1:8790 查看镜像数据。

用法：
    python scripts/web.py                       # 127.0.0.1:8790，库文件 data/xtools_mirror.sqlite
    python scripts/web.py --port 8800
    python scripts/web.py --db data/other.sqlite
    python scripts/web.py --host 0.0.0.0        # 供手机经 Tailscale 访问（需在 .env 设置访问密码）

常驻运行请用 scripts/install_launchd.py --web（退出后由 launchd 自动拉起）。服务只读，不向镜像库写入。
绑到非本机地址时：来源限本机与 Tailscale 网段，且需 .env 中的 XTOOLS_WEB_USER / XTOOLS_WEB_PASSWORD（见 web/auth.py）。
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
from web.auth import from_env as access_from_env  # noqa: E402

DEFAULT_PORT = 8790  # 8765 等常见端口容易与其他本机应用冲突


def main() -> int:
    parser = argparse.ArgumentParser(description="XTools 镜像本地前台")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，缺省只允许本机访问；手机访问用 0.0.0.0（配合 Tailscale 与访问密码）")
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
    access = access_from_env(ROOT, args.host)
    logging.info("访问控制：%s", access.describe())
    if access.misconfigured:
        logging.warning("未设置 XTOOLS_WEB_PASSWORD：本机仍可访问，其他设备一律拒绝。"
                        "执行 .venv/bin/python scripts/install_launchd.py --web --host %s 可自动生成密码", args.host)
    try:
        server = make_server(args.db, args.host, args.port, access)
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
