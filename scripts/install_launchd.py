#!/usr/bin/env python3
"""在 Mac 上安装 / 卸载 launchd 任务。

    python scripts/install_launchd.py                 # 同步：每 30 分钟增量一次（缺省间隔 1800 秒）
    python scripts/install_launchd.py --interval 900
    python scripts/install_launchd.py --web           # 前台：常驻 http://127.0.0.1:8790（退出自动拉起）
    python scripts/install_launchd.py --web --port 8801
    python scripts/install_launchd.py --web --host 0.0.0.0   # 供手机经 Tailscale 访问：自动生成访问密码写入 .env
    python scripts/install_launchd.py --web --host 0.0.0.0 --allow-lan   # 另放行本机所在的局域网（同一 Wi-Fi 的手机不必开 VPN）
    python scripts/install_launchd.py --uninstall     # 卸载同步任务
    python scripts/install_launchd.py --web --uninstall

生成 ~/Library/LaunchAgents/com.microwants.xtools-sync.plist（同步）与 com.microwants.xtools-web.plist（前台），
使用仓库内 .venv 的 Python 执行 scripts/sync.py / scripts/web.py；标准输出 / 错误写入 logs/。仅在当前用户登录期间运行（LaunchAgent）。
"""

from __future__ import annotations

import argparse
import ipaddress
import plistlib
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.auth import LOCAL_HOSTS, load_dotenv  # noqa: E402
LABELS = {"sync": "com.microwants.xtools-sync", "web": "com.microwants.xtools-web"}
DEFAULT_WEB_PORT = 8790


# 手机上要手输一次的密码：去掉易混淆字符，分三段
PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def make_password() -> str:
    return "-".join("".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(4)) for _ in range(3))


def ensure_web_password(host: str):
    """非本机监听时确保 .env 里有访问密码，没有就生成一个。返回 (用户名, 密码, 是否新生成)。"""
    if host in LOCAL_HOSTS:
        return "", "", False
    env = load_dotenv(ROOT)
    user = env.get("XTOOLS_WEB_USER") or "xtools"
    if env.get("XTOOLS_WEB_PASSWORD"):
        return user, env["XTOOLS_WEB_PASSWORD"], False
    password = make_password()
    path = ROOT / ".env"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    prefix = "" if (not existing or existing.endswith("\n")) else "\n"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{prefix}\n# 前台访问密码（手机 / 其他设备经 Tailscale 访问时使用；本机访问免密）\n"
                 f"XTOOLS_WEB_USER={user}\nXTOOLS_WEB_PASSWORD={password}\n")
    return user, password, True


def local_ips() -> list:
    """本机在 en* 网卡上的 IPv4 地址。"""
    try:
        out = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return []
    ips, iface = [], ""
    for line in out.splitlines():
        if line and not line[0].isspace():
            iface = line.split(":")[0]
            continue
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == "inet" and iface.startswith("en") and not parts[1].startswith("127."):
            ips.append(parts[1])
    return ips


def lan_networks() -> list:
    """本机有线 / 无线网卡上的私有网段（en* 接口；VPN 的 utun 接口不算）。"""
    try:
        out = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return []
    nets, iface = [], ""
    for line in out.splitlines():
        if line and not line[0].isspace():
            iface = line.split(":")[0]
            continue
        parts = line.strip().split()
        if len(parts) >= 4 and parts[0] == "inet" and iface.startswith("en"):
            try:
                prefix = bin(int(parts[3], 16)).count("1") if parts[3].startswith("0x") else int(parts[3])
                net = ipaddress.ip_network(f"{parts[1]}/{prefix}", strict=False)
            except ValueError:
                continue
            if net.is_private and not net.is_loopback and net.prefixlen >= 16 and str(net) not in nets:
                nets.append(str(net))
    return nets


def ensure_allow(networks: list) -> str:
    """把网段并入 .env 的 XTOOLS_WEB_ALLOW（已有的保留），返回最终值。"""
    env = load_dotenv(ROOT)
    current = [x.strip() for x in (env.get("XTOOLS_WEB_ALLOW") or "").replace(";", ",").split(",") if x.strip()]
    merged = current + [n for n in networks if n not in current]
    value = ",".join(merged)
    if not merged or value == env.get("XTOOLS_WEB_ALLOW"):
        return value
    path = ROOT / ".env"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    line = f"XTOOLS_WEB_ALLOW={value}\n"
    if re.search(r"^XTOOLS_WEB_ALLOW=.*$", text, re.M):
        text = re.sub(r"^XTOOLS_WEB_ALLOW=.*$", line.rstrip("\n"), text, count=1, flags=re.M)
        path.write_text(text, encoding="utf-8")
    else:
        prefix = "" if (not text or text.endswith("\n")) else "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{prefix}\n# 除本机与 Tailscale 外额外放行的网段（局域网访问用）\n{line}")
    return value


def tailscale_ip() -> str:
    """本机的 Tailscale 地址（100.64.0.0/10）；未安装或未登录时返回空串。"""
    for cmd in (["tailscale", "ip", "-4"], ["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "ip", "-4"],
                ["/opt/homebrew/bin/tailscale", "ip", "-4"], ["/usr/local/bin/tailscale", "ip", "-4"]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:  # noqa: BLE001
            continue
        for line in out.splitlines():
            if line.strip().startswith("100."):
                return line.strip()
    try:  # 退回：从网卡地址里找
        out = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return ""
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == "inet" and parts[1].startswith("100."):
            return parts[1]
    return ""


def port_in_use(port: int, host: str = "127.0.0.1") -> str:
    """端口被占用时返回占用者描述（尽量给出进程名），空字符串表示可用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("" if host == "0.0.0.0" else host, port))
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
    parser.add_argument("--host", default="127.0.0.1", help="前台监听地址；手机经 Tailscale 访问用 0.0.0.0（会自动生成访问密码）")
    parser.add_argument("--allow-lan", action="store_true", help="额外放行本机所在的局域网网段（同一 Wi-Fi 的手机不必开 VPN；写入 .env 的 XTOOLS_WEB_ALLOW）")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    kind = "web" if args.web else "sync"
    if args.uninstall:
        return uninstall(kind)
    if kind == "web":
        # 先停掉已安装的前台（可能正因端口冲突反复重启），再检查端口是否空闲
        subprocess.run(["launchctl", "unload", str(plist_path("web"))], check=False, capture_output=True)
        time.sleep(1)
        holder = port_in_use(args.port, args.host)
        if holder:
            print(f"端口 {args.port} 已被其他程序占用（{holder}），未安装。请换一个端口，例如：")
            print(f"    .venv/bin/python scripts/install_launchd.py --web --port {args.port + 11}")
            return 3
        user, password, created = ensure_web_password(args.host)
        lans = []
        if args.allow_lan:
            lans = lan_networks()
            if lans:
                ensure_allow(lans)
            else:
                print("未找到本机的局域网地址（en* 网卡），跳过 --allow-lan")
        code = install("web", [str(ROOT / "scripts" / "web.py"), "--port", str(args.port), "--host", args.host], {"KeepAlive": True, "ThrottleInterval": 30},
                       f"前台常驻 http://127.0.0.1:{args.port}（退出后自动拉起）")
        if code:
            return code
        if wait_web(args.port):
            print(f"前台已就绪：http://127.0.0.1:{args.port}")
            if args.host not in LOCAL_HOSTS:
                ip = tailscale_ip()
                print("\n手机访问（先在手机上装 Tailscale 并用同一账号登录）：")
                print(f"    地址：http://{ip or '<Mac 的 Tailscale 地址 100.x.x.x>'}:{args.port}")
                print(f"    账号：{user}    密码：{password}" + ("（本次新生成，已写入 .env）" if created else "（.env 中的现有密码）"))
                if not ip:
                    print("    注：本机尚未取得 Tailscale 地址，装好并登录 Tailscale 后用 `tailscale ip -4` 查看")
                if lans:
                    print(f"\n同一 Wi-Fi 下（不必开 VPN）：http://{(local_ips() or ['<本机局域网地址>'])[0]}:{args.port}")
                    print(f"    已放行网段：{', '.join(lans)}（同一网络内的其他设备也能访问，仍需上面的账号密码）")
                print("    本机浏览器打开 127.0.0.1 时不需要密码。")
            return 0
        print(f"前台未在 8 秒内响应，请看 {ROOT / 'logs' / 'launchd.web.err.log'}")
        return 4
    return install("sync", [str(ROOT / "scripts" / "sync.py")], {"StartInterval": args.interval},
                   f"每 {args.interval} 秒运行一次增量同步")


if __name__ == "__main__":
    sys.exit(main())
