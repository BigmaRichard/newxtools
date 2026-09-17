#!/usr/bin/env python3
"""在 Mac 上安装 / 卸载 launchd 定时任务：每 30 分钟运行一次增量同步。

用法：
    python scripts/install_launchd.py            # 安装并立即加载（缺省间隔 1800 秒）
    python scripts/install_launchd.py --interval 900
    python scripts/install_launchd.py --uninstall

生成 ~/Library/LaunchAgents/com.microwants.xtools-sync.plist，使用仓库内 .venv 的 Python 执行 scripts/sync.py；
标准输出 / 错误写入 logs/launchd.out.log 与 logs/launchd.err.log。仅在当前用户登录期间运行（LaunchAgent）。
"""

from __future__ import annotations

import argparse
import plistlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = "com.microwants.xtools-sync"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=1800, help="运行间隔秒数，缺省 1800")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()

    if args.uninstall:
        subprocess.run(["launchctl", "unload", str(PLIST)], check=False)
        if PLIST.exists():
            PLIST.unlink()
        print("已卸载", LABEL)
        return 0

    python = ROOT / ".venv" / "bin" / "python"
    if not python.exists():
        print("未找到 .venv，请先执行：python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")
        return 2
    (ROOT / "logs").mkdir(exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [str(python), str(ROOT / "scripts" / "sync.py")],
        "WorkingDirectory": str(ROOT),
        "StartInterval": args.interval,
        "RunAtLoad": True,
        "StandardOutPath": str(ROOT / "logs" / "launchd.out.log"),
        "StandardErrorPath": str(ROOT / "logs" / "launchd.err.log"),
        "EnvironmentVariables": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
    }
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["launchctl", "unload", str(PLIST)], check=False, capture_output=True)
    with open(PLIST, "wb") as fh:
        plistlib.dump(plist, fh)
    subprocess.run(["launchctl", "load", str(PLIST)], check=True)
    print(f"已安装 {LABEL}：每 {args.interval} 秒运行一次增量同步，日志在 {ROOT / 'logs'}")
    print("查看状态：launchctl list | grep xtools-sync ；手动触发：launchctl start", LABEL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
