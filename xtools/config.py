"""XTools OPEN API 配置。

配置来源优先级：显式传参 > 环境变量 > .env 文件（当前目录或上级目录）。

需要向 XTools（超兔）索取的六项凭证：
    XTOOLS_APPID      开发公司的应用 ID（示例 open00001_sajdjsjsj）
    XTOOLS_APPKEY     应用密钥，参与每次请求的 md 签名（示例 open1slslslsdldlsdlds）
    XTOOLS_COMKEYID   XTools 分配给客户公司的 comkeyid，明文放在登录 upr 中（示例 xtoolsplusd002）
    XTOOLS_COMKEY     客户公司 key，参与登录验证码 upr.md 的计算（示例 xtoolsplusd002sjsjsj）
                      注意：文档示例中 comkey 与 comkeyid 并不相同，需分别索取并核对
    XTOOLS_COM        XToolsCRM 中的客户公司内部编码（示例 d002）
    XTOOLS_PART       登录人 part，缺省 B1；写入的数据所有者默认即为该登录人

可选：
    XTOOLS_BASE_URL       缺省 https://crm.xtcrm.com/open/index.xt
    XTOOLS_TIMEOUT        HTTP 超时秒数，缺省 30
    XTOOLS_SID_CACHE      sid 缓存文件路径，缺省 ./.xtools_session.json
    XTOOLS_SID_TTL        本地视 sid 为有效的秒数，缺省 1500（25 分钟，文档建议以 30 分钟为准）
    XTOOLS_MIN_INTERVAL   两次普通请求之间的最小间隔秒数，缺省 0.2
    XTOOLS_VERIFY_SSL     是否校验证书，缺省 1
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from .errors import XToolsConfigError

DEFAULT_BASE_URL = "https://crm.xtcrm.com/open/index.xt"
LOGIN_MIN_INTERVAL = 10.0  # 文档：登录接口 10 秒内只能调用一次


def _load_dotenv(start: Optional[Path] = None) -> Dict[str, str]:
    """读取最近的 .env 文件（不覆盖已有环境变量）。不依赖第三方库。"""
    here = (start or Path.cwd()).resolve()
    for folder in [here, *here.parents]:
        candidate = folder / ".env"
        if candidate.is_file():
            values: Dict[str, str] = {}
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    values[key] = value
            return values
    return {}


@dataclass
class XToolsConfig:
    appid: str
    appkey: str
    comkeyid: str
    comkey: str
    com: str
    part: str = "B1"
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 30.0
    sid_cache: Path = field(default_factory=lambda: Path(".xtools_session.json"))
    sid_ttl: float = 1500.0
    min_interval: float = 0.2
    verify_ssl: bool = True

    REQUIRED = ("appid", "appkey", "comkeyid", "comkey", "com")

    def __post_init__(self) -> None:
        missing = [name for name in self.REQUIRED if not getattr(self, name)]
        if missing:
            raise XToolsConfigError(
                "缺少配置项：" + ", ".join(f"XTOOLS_{m.upper()}" for m in missing)
                + "（请复制 .env.example 为 .env 并填入 XTools 提供的凭证）"
            )
        self.sid_cache = Path(self.sid_cache)

    @classmethod
    def from_env(cls, defaults: Optional[Dict[str, object]] = None, **overrides) -> "XToolsConfig":
        """从环境变量 / .env 读取配置；overrides 用于显式覆盖，defaults 只在环境未提供该项时生效。"""
        env = dict(_load_dotenv())
        env.update({k: v for k, v in os.environ.items() if k.startswith("XTOOLS_")})
        for name, value in (defaults or {}).items():
            env.setdefault(f"XTOOLS_{name.upper()}", str(value))

        def get(name: str, default: Optional[str] = None) -> Optional[str]:
            return env.get(f"XTOOLS_{name.upper()}", default)

        kwargs = dict(
            appid=get("appid", ""),
            appkey=get("appkey", ""),
            comkeyid=get("comkeyid", ""),
            comkey=get("comkey", ""),
            com=get("com", ""),
            part=get("part", "B1") or "B1",
            base_url=get("base_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL,
            timeout=float(get("timeout", "30") or 30),
            sid_cache=Path(get("sid_cache", ".xtools_session.json") or ".xtools_session.json"),
            sid_ttl=float(get("sid_ttl", "1500") or 1500),
            min_interval=float(get("min_interval", "0.2") or 0.2),
            verify_ssl=(get("verify_ssl", "1") or "1").strip().lower() not in ("0", "false", "no"),
        )
        kwargs.update(overrides)
        return cls(**kwargs)

    def masked(self) -> Dict[str, str]:
        """用于日志输出的脱敏视图。"""

        def mask(value: str) -> str:
            if not value:
                return ""
            return value[:3] + "*" * max(0, len(value) - 5) + value[-2:] if len(value) > 6 else "***"

        return {
            "appid": self.appid,
            "appkey": mask(self.appkey),
            "comkeyid": self.comkeyid,
            "comkey": mask(self.comkey),
            "com": self.com,
            "part": self.part,
            "base_url": self.base_url,
        }
