"""前台访问控制：来源地址限制 + HTTP Basic 认证。

前台只读镜像库，但镜像库里是全部客户与订单数据，因此一旦不再只监听本机（例如为了手机访问而绑到
Tailscale 地址），就要求两道门：

1. 来源地址：只接受本机与 Tailscale 网段（100.64.0.0/10、fd7a:115c:a1e0::/48）的请求，其余一律 403。
   需要局域网访问时用 XTOOLS_WEB_ALLOW 增补网段（逗号分隔，如 "192.168.1.0/24"）。
2. 账号密码：HTTP Basic，凭证取自 .env 的 XTOOLS_WEB_USER / XTOOLS_WEB_PASSWORD（.env 不进仓库）。
   只监听 127.0.0.1 时不要求密码（0.4 起的原有用法不变）。

密码在安装前台服务时由 scripts/install_launchd.py 自动生成并写入 .env（见该脚本的 ensure_password）。
"""

from __future__ import annotations

import base64
import binascii
import hmac
import ipaddress
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Tailscale 给每台设备分配的地址段（CGNAT 100.64.0.0/10 与其 IPv6 ULA 前缀）
TAILSCALE_NETS = ["100.64.0.0/10", "fd7a:115c:a1e0::/48"]
LOCAL_NETS = ["127.0.0.0/8", "::1/128"]
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def load_dotenv(root: Path) -> Dict[str, str]:
    """读取仓库根目录的 .env（环境变量优先）。与 xtools.config 同样的极简解析，避免前台依赖 xtools 包。"""
    values: Dict[str, str] = {}
    path = Path(root) / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({k: v for k, v in os.environ.items() if k.startswith("XTOOLS_WEB_")})
    return values


def parse_nets(text: str) -> List[ipaddress._BaseNetwork]:
    nets = []
    for item in (text or "").replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            nets.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return nets


class AccessControl:
    """按来源地址与 Basic 认证放行请求。check() 返回 None 表示放行，否则返回 (状态码, 提示)。"""

    def __init__(self, host: str = "127.0.0.1", user: str = "", password: str = "", allow: str = "", require_auth: Optional[bool] = None):
        self.host = host
        self.user = user or ""
        self.password = password or ""
        self.local_only = host in LOCAL_HOSTS
        self.networks = parse_nets(",".join(LOCAL_NETS + TAILSCALE_NETS)) + parse_nets(allow)
        # 只监听本机时不强制密码；绑到其他地址时必须有密码（没有则整个服务拒绝提供数据）
        self.require_auth = (not self.local_only) if require_auth is None else require_auth
        self.enabled = bool(self.password)

    @property
    def misconfigured(self) -> bool:
        return self.require_auth and not self.enabled

    def allowed_source(self, client_ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(client_ip)
        except ValueError:
            return False
        if addr.is_loopback:
            return True
        addr = addr.ipv4_mapped or addr if isinstance(addr, ipaddress.IPv6Address) else addr
        return any(addr in net for net in self.networks if net.version == addr.version)

    def check_auth(self, header: Optional[str]) -> bool:
        if not self.enabled:
            return True
        if not header or not header.lower().startswith("basic "):
            return False
        try:
            raw = base64.b64decode(header.split(None, 1)[1].strip(), validate=True).decode("utf-8", "replace")
        except (binascii.Error, IndexError, UnicodeDecodeError):
            return False
        user, _, password = raw.partition(":")
        return hmac.compare_digest(user, self.user) and hmac.compare_digest(password, self.password)

    @staticmethod
    def is_loopback(client_ip: str) -> bool:
        try:
            return ipaddress.ip_address(client_ip).is_loopback
        except ValueError:
            return False

    def check(self, client_ip: str, auth_header: Optional[str]) -> Optional[Tuple[int, str]]:
        if self.is_loopback(client_ip):  # 本机浏览器与安装脚本的就绪探测始终放行
            return None
        if self.misconfigured:
            return (503, "前台监听了非本机地址但未设置访问密码，已停止提供数据：在 .env 中设置 XTOOLS_WEB_USER / XTOOLS_WEB_PASSWORD 后重启服务")
        if not self.allowed_source(client_ip):
            return (403, "来源地址不在允许范围内（本机与 Tailscale 网段；如需局域网访问请设置 XTOOLS_WEB_ALLOW）")
        if self.require_auth and not self.check_auth(auth_header):
            return (401, "需要账号密码")
        return None

    def describe(self) -> str:
        if self.local_only:
            return "仅本机访问，未启用密码"
        return f"监听 {self.host}；本机免密，其余来源限 Tailscale 网段" + (f"（另放行 {len(self.networks) - 4} 个自定义网段）" if len(self.networks) > 4 else "") + \
               ("；已启用账号密码" if self.enabled else "；未设置密码（服务将拒绝提供数据）")


def from_env(root: Path, host: str = "127.0.0.1") -> AccessControl:
    env = load_dotenv(root)
    return AccessControl(host=host, user=env.get("XTOOLS_WEB_USER", "xtools"), password=env.get("XTOOLS_WEB_PASSWORD", ""), allow=env.get("XTOOLS_WEB_ALLOW", ""))
