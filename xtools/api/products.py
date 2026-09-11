"""产品与库存模块：product / csstree（产品分类）/ prod_alias（客制别名）/ libn（外部库存）。

字段要点（摘自文档）：
* 产品读取（dt=product）过滤：id、lastid、lasttime、sn（产品编码）、mflag（是否自产）。
  返回字段：id、name、model、sku、sn、class（分类名）、price、unit、intro、parameter、costprice、lup、ldown、lnum（库存数量）、
  ptype（是否计算库存 0 否;1 是;2 外部库存）、status（0 正常;1 停售）、batchnum、sntype、weight、w_unit、manufacturer、
  pmode、mflag、j1…（自定义字段）、flow_id。注意：读取时部分枚举字段返回的是展示文本（如 "是"/"正常"），写入时用数字。
* 产品写入（api.input dt=product）：name、model、sku、sn、price、memo、unit（数据字典“产品-单位”数字）、mflag、manufacturer、
  intro、ptype（启用外部库存时只能 0/2；未启用时只能 0/1）、class（分类 ID）、list_remark、parameter、pow_type、自定义字段。
* 产品修改（api.update dt=product）：data.id 定位，只传变化字段。
* 价格策略变更：api.cmdact dt=product act=chg_str_ps，data={"id":产品ID,"data":{"<策略字典序号>":"价格"}}。
* 产品分类：读取 dt=csstree（tid、title、upid、status 0 无下级;1 有下级）；写入 api.input dt=csstree data={id:0,tid:1,upid,title}。
* 客制别名：读取 dt=prod_alias（cu_id、pid 过滤）；写入 api.input dt=prod_alias data={cu_sn|客户id, pid, name, sn, memo}。
* 外部库存变更（需开通外部库存）：api.cmdact dt=libn act=erp_libn data={lib:仓库ID或名称, prod:产品编码, num, memo}。
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Union

from ..client import XToolsClient

Id = Union[int, str]


class ProductAPI:
    DT = "product"

    def __init__(self, client: XToolsClient):
        self.client = client

    # ---- 读取
    def get(self, id: Optional[Id] = None, *, sn: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if id is not None:
            params["id"] = id
        elif sn is not None:
            params["sn"] = sn
        else:
            raise ValueError("id / sn 至少提供一个")
        rows = self.client.output(self.DT, **params)
        return rows[0] if rows else None

    def list(self, *, lastid: int = 0, **filters: Any) -> List[Dict[str, Any]]:
        return self.client.output(self.DT, lastid=lastid, **filters)

    def iter(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        """filters 如 lasttime="2026-09-01"（增量）、mflag=1。"""
        return self.client.iter_output(self.DT, lastid=lastid, **filters)

    # ---- 写入 / 修改
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """返回 ret：{"ok":1,"msg":"产品信息添加成功！","id":40614}"""
        return self.client.input(self.DT, data)

    def update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in data:
            raise ValueError("修改产品需提供 id")
        return self.client.update(self.DT, data)

    def change_price_strategy(self, id: Id, prices: Dict[str, Any]) -> Dict[str, Any]:
        """prices：{"<价格策略字典序号>": "<价格>"}，如 {"4":"98","5":"99"}。"""
        return self.client.cmdact(self.DT, {"id": id, "data": prices}, act="chg_str_ps")

    # ---- 产品分类
    def categories(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("csstree", lastid=lastid, **filters)

    def create_category(self, title: str, *, upid: Id, tid: int = 1) -> Dict[str, Any]:
        return self.client.input("csstree", {"id": 0, "tid": tid, "upid": upid, "title": title})

    # ---- 客制别名
    def aliases(self, *, lastid: int = 0, cu_id: Optional[Id] = None, pid: Optional[Id] = None) -> Iterator[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if cu_id is not None:
            params["cu_id"] = cu_id
        if pid is not None:
            params["pid"] = pid
        return self.client.iter_output("prod_alias", lastid=lastid, **params)

    def create_alias(self, *, pid: Id, cu_sn: Union[int, str], name: str = "", sn: str = "", memo: str = "") -> Dict[str, Any]:
        if not name and not sn:
            raise ValueError("客制别名 name 与客制编号 sn 至少一项不为空")
        return self.client.input("prod_alias", {"cu_sn": cu_sn, "pid": pid, "name": name, "sn": sn, "memo": memo})

    # ---- 外部库存
    def set_external_stock(self, *, lib: Union[int, str], prod: str, num: Union[int, float], memo: str = "") -> Dict[str, Any]:
        """外部库存变更（erp_libn）：lib 为仓库 ID（数字）或仓库名称（文本，不存在时自动新建）。"""
        return self.client.cmdact("libn", {"lib": lib, "prod": prod, "num": num, "memo": memo}, act="erp_libn")

    # ---- 字典
    def dictionary(self, field: str) -> List[Dict[str, Any]]:
        """如 unit（单位）、pow_type（权限分组）等。"""
        return self.client.dictionary(self.DT, field)

    def field_names(self) -> Dict[str, str]:
        return self.client.field_names(self.DT)
