"""XToolsCRM（超兔）OPEN API Python 客户端。

用法：
    from xtools import XTools
    xt = XTools()                      # 从环境变量 / .env 读取凭证
    for c in xt.customers.iter(lasttime="2026-09-01"):
        print(c["id"], c["cu_name"])

    xt.client.dictionary("customer", "cu_status")   # 数据字典
    xt.orders.create({...})                         # 写入
"""

from __future__ import annotations

from typing import Optional

from .api import CustomerAPI, FinanceAPI, OrderAPI, ProductAPI, RepairAPI
from .client import XToolsClient, compact_json, md5_hex
from .config import XToolsConfig
from .errors import (
    XToolsApiError,
    XToolsBusinessError,
    XToolsConfigError,
    XToolsError,
    XToolsLoginThrottled,
    XToolsSessionExpired,
    XToolsTransportError,
)

__version__ = "0.2.0"


class XTools:
    """按业务模块组织的门面：xt.customers / xt.orders / xt.products / xt.finance / xt.repairs / xt.client。"""

    def __init__(self, config: Optional[XToolsConfig] = None, **client_kwargs):
        self.client = XToolsClient(config, **client_kwargs)
        self.customers = CustomerAPI(self.client)
        self.orders = OrderAPI(self.client)
        self.products = ProductAPI(self.client)
        self.finance = FinanceAPI(self.client)
        self.repairs = RepairAPI(self.client)

    def login(self, *, force: bool = False) -> str:
        return self.client.login(force=force)


__all__ = [
    "XTools",
    "XToolsClient",
    "XToolsConfig",
    "CustomerAPI",
    "OrderAPI",
    "ProductAPI",
    "FinanceAPI",
    "RepairAPI",
    "XToolsError",
    "XToolsConfigError",
    "XToolsTransportError",
    "XToolsApiError",
    "XToolsSessionExpired",
    "XToolsLoginThrottled",
    "XToolsBusinessError",
    "compact_json",
    "md5_hex",
    "__version__",
]
