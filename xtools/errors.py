"""XTools OPEN API 异常定义。

异常层级：
    XToolsError                 —— 基类
    ├── XToolsConfigError       —— 配置缺失或不合法
    ├── XToolsTransportError    —— 网络 / HTTP / 响应不是 JSON
    ├── XToolsApiError          —— 接口层失败：{"ok":0,"err":{"errno":..,"errmsg":..}}
    │   ├── XToolsSessionExpired    —— errno 20101 / 20102，需要重新登录
    │   └── XToolsLoginThrottled    —— errno 30103，登录接口 10 秒内只能调用一次
    └── XToolsBusinessError     —— 业务层失败：{"ok":1,"ret":{"ok":0,"msg":..}}
"""

from __future__ import annotations

from typing import Any, Optional


class XToolsError(Exception):
    """XTools 客户端异常基类。"""

    def __init__(self, message: str, *, raw: Any = None):
        super().__init__(message)
        self.raw = raw


class XToolsConfigError(XToolsError):
    """配置缺失或不合法。"""


class XToolsTransportError(XToolsError):
    """网络错误、HTTP 状态异常、响应体无法解析为 JSON。"""

    def __init__(self, message: str, *, status_code: Optional[int] = None, raw: Any = None):
        super().__init__(message, raw=raw)
        self.status_code = status_code


class XToolsApiError(XToolsError):
    """接口层失败（ok == 0）。"""

    def __init__(self, errno: Optional[int], errmsg: str, *, cmd: str = "", raw: Any = None):
        super().__init__(f"[{cmd}] errno={errno} {errmsg}", raw=raw)
        self.errno = errno
        self.errmsg = errmsg
        self.cmd = cmd


class XToolsSessionExpired(XToolsApiError):
    """sid 失效（errno 20101 / 20102），需要重新登录后重试。"""


class XToolsLoginThrottled(XToolsApiError):
    """登录过于频繁（errno 30103）：登录接口 10 秒内只能调用一次。"""


class XToolsBusinessError(XToolsError):
    """业务层失败（ok == 1 但 ret.ok == 0），msg 为 CRM 返回的失败原因。"""

    def __init__(self, msg: str, *, cmd: str = "", dt: str = "", raw: Any = None):
        super().__init__(f"[{cmd} dt={dt}] {msg}", raw=raw)
        self.msg = msg
        self.cmd = cmd
        self.dt = dt


# 文档中明确给出的错误码（附录“状态码”在导出文件中为空，以下为正文中出现的编号）
SESSION_EXPIRED_ERRNOS = frozenset({20101, 20102})
LOGIN_THROTTLED_ERRNO = 30103
