#!/usr/bin/env python3
"""在 Mac 上安装 / 卸载 launchd 任务。

    python scripts/install_launchd.py                 # 同步：每 30 分钟增量一次（缺省间隔 1800 秒）
    python scripts/install_launchd.py --interval 900
    python scripts/install_launchd.py --web           # 前台：常驻 http://127.0.0.1:8790（退出自动拉起）
    python scripts/install_launchd.py --web --port 8801
    python scripts/install_launchd.py --uninstall     # 卸载同步任务
    python scripts/install_launchd.py --web --uninstall

生成 ~/Library/LaunchAgents/com.microwants.xtools-sync.plist（同步）与 com.microwants.xtools-web.plist（前台），
使用仓库内 .venv 的 Python 执行 scripts/sync.py / scripts/web.py；标准输出 / 错误写入 logs/。仅在当前用户登录期间运行（LaunchAgent）。
"""

from __future__ import annotations

import argparse
import plistlib
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {"sync": "com.microwants.xtools-sync", "web": "com.microwants.xtools-web"}
DEFAULT_WEB_PORT = 8790


def port_in_use(port: int) -> str:
    """端口被占用时返回占用者描述（尽量给出进程名），空字符串表示可用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return ""
        except OSError:
            pass
    try:
        out = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
        names = sorted({line.split()[0] for line in out[1:] if line.split()})
        return "、".join(names) or "未知程序"
    except Exception:  # noqa: BLE001
        return "未知程序"


def wait_web(port: int, seconds: float = 8.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/meta", timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    return False


def plist_path(kind: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABELS[kind]}.plist"


def install(kind: str, program: list, extra: dict, message: str) -> int:
    python = ROOT / ".venv" / "bin" / "python"
    if not python.exists():
        print("未找到 .venv，请先执行：python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")
        return 2
    (ROOT / "logs").mkdir(exist_ok=True)
    label = LABELS[kind]
    plist = {
        "Label": label,
        "ProgramArguments": [str(python), *program],
        "WorkingDirectory": str(ROOT),
        "RunAtLoad": True,
        "StandardOutPath": str(ROOT / "logs" / f"launchd.{kind}.out.log"),
        "StandardErrorPath": str(ROOT / "logs" / f"launchd.{kind}.err.log"),
        "EnvironmentVariables": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONUNBUFFERED": "1"},
        **extra,
    }
    if kind == "sync":  # 兼容 0.3.x 的日志文件名
        plist["StandardOutPath"] = str(ROOT / "logs" / "launchd.out.log")
        plist["StandardErrorPath"] = str(ROOT / "logs" / "launchd.err.log")
    path = plist_path(kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["launchctl", "unload", str(path)], check=False, capture_output=True)
    with open(path, "wb") as fh:
        plistlib.dump(plist, fh)
    subprocess.run(["launchctl", "load", str(path)], check=True)
    print(f"已安装 {label}：{message}，日志在 {ROOT / 'logs'}")
    print(f"查看状态：launchctl list | grep {label.rsplit('.', 1)[-1]} ；手动触发：launchctl start {label}")
    return 0


def uninstall(kind: str) -> int:
    path = plist_path(kind)
    subprocess.run(["launchctl", "unload", str(path)], check=False)
    if path.exists():
        path.unlink()
    print("已卸载", LABELS[kind])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--web", action="store_true", help="安装 / 卸载前台服务而不是同步任务")
    parser.add_argument("--interval", type=int, default=1800, help="同步间隔秒数，缺省 1800")
    parser.add_argument("--port", type=int, default=DEFAULT_WEB_PORT, help=f"前台端口，缺省 {DEFAULT_WEB_PORT}")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    kind = "web" if args.web else "sync"
    if args.uninstall:
        return uninstall(kind)
    if kind == "web":
        # 先停掉已安装的前台（可能正因端口冲突反复重启），再检查端口是否空闲
        subprocess.run(["launchctl", "unload", str(plist_path("web"))], check=False, capture_output=True)
        time.sleep(1)
        holder = port_in_use(args.port)
        if holder:
            print(f"端口 {args.port} 已被其他程序占用（{holder}），未安装。请换一个端口，例如：")
            print(f"    .venv/bin/python scripts/install_launchd.py --web --port {args.port + 11}")
            return 3
        code = install("web", [str(ROOT / "scripts" / "web.py"), "--port", str(args.port)], {"KeepAlive": True, "ThrottleInterval": 30},
                       f"前台常驻 http://127.0.0.1:{args.port}（退出后自动拉起）")
        if code:
            return code
        if wait_web(args.port):
            print(f"前台已就绪：http://127.0.0.1:{args.port}")
            return 0
        print(f"前台未在 8 秒内响应，请看 {ROOT / 'logs' / 'launchd.web.err.log'}")
        return 4
    return install("sync", [str(ROOT / "scripts" / "sync.py")], {"StartInterval": args.interval},
                   f"每 {args.interval} 秒运行一次增量同步")


if __name__ == "__main__":
    sys.exit(main())
