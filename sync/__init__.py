"""P0 只读镜像：XTools CRM → 本地 SQLite。"""

from .engine import Syncer
from .specs import DICT_FIELDS, SPEC_BY_DT, TABLE_SPECS, TableSpec
from .store import Store

__all__ = ["Syncer", "Store", "TABLE_SPECS", "SPEC_BY_DT", "TableSpec", "DICT_FIELDS"]
