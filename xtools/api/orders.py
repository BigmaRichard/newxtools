"""订单与发货模块：contract（订单）/ sendgoods（发货单）/ sr_notice（收发货通知单）/ libout / libin / price（报价单）/ contract0（合同）。

字段要点（摘自文档）：
* 订单读取（dt=contract）过滤：lastid、id、"No."（订单编号）、confirm（1 待申请;2 同意;3 否决;4 待审）、
  status（1 执行中;2 结束;3 意外中止;-1 预定;-2 借出未还;-3 关闭）、st_send（0 ---;1 未出库;2 需发货;3 部分;4 全部）、
  date（"2025-04-10,2025-05-14" 区间）、payment；extend=1 追加 state/city/mphone/pst/cu_user/st_send/pay_mode/payment/prj_id/op_id/org_id/confirm。
* 订单字段：id、subject、cu_sn、"No."、type、sum、who、memo、name、tel、addr、date、end_date、money_type、money_rate、one_select、
  goods[{id,prod,amount,un_price,sum,tax_money,memo}]；extend 明细追加 tax_rate、zk、prod_name、model、sku、batchnum。
* 订单写入（api.input dt=contract）：cu_sn 定位客户；goods.prod 为产品编码（extend=1 时可用 prod_name/model/sku/batchnum 匹配）。
* 订单修改（api.update dt=contract）：id 或 "No." 定位；cu_sn 不可修改；goods 为“全量替换”——
  未提供的已有明细会被删除，已存在的按修改处理，新的按添加处理。
* 订单分批发货（不计算库存的商品）：api.cmdact dt=contract act=sendGoods_no_stock。
* 收发货通知单（需开通“外部库存”）：读取 dt=sr_notice（type 0 订单-发货;1 采购-收货;2 订单退货-收货;3 采购退货-发货；
  status 0 临时;1 API未读;2 API已读;3 部分执行;4 全部执行;5 已关闭;6 部分执行API已读;7 API错误），
  状态变更 act=chgst（只允许改为 2/5/6/7），执行 act=exc（child 明细，no_more=1 时控制不超通知数量）。
* 出库单：读取 dt=libout；写入 api.input dt=libout（title、lib、date、cu_sn、co_sn、who、libitem[{prod,num,memo}]），
  完成出库 api.cmdact act=liboutok（需写入返回的 id）。入库单同理：dt=libin，act=libinok。
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Union

from ..client import XToolsClient

Id = Union[int, str]


class OrderAPI:
    DT = "contract"

    def __init__(self, client: XToolsClient):
        self.client = client

    # ---- 订单读取
    def get(self, id: Optional[Id] = None, *, no: Optional[str] = None, extend: int = 1) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {"extend": extend}
        if id is not None:
            params["id"] = id
        elif no is not None:
            params["No."] = no
        else:
            raise ValueError("id / No. 至少提供一个")
        rows = self.client.output(self.DT, **params)
        return rows[0] if rows else None

    def list(self, *, lastid: int = 0, extend: int = 1, **filters: Any) -> List[Dict[str, Any]]:
        return self.client.output(self.DT, lastid=lastid, extend=extend, **filters)

    def iter(self, *, lastid: int = 0, extend: int = 1, **filters: Any) -> Iterator[Dict[str, Any]]:
        """filters 如 status=1、st_send=2、date="2026-09-01,2026-09-30"、confirm=2。"""
        return self.client.iter_output(self.DT, lastid=lastid, extend=extend, **filters)

    def other_items(self, id: Id) -> Dict[str, Any]:
        """订单自定义明细（act=getOtherItems）。"""
        return self.client.cmdact(self.DT, {"id": id}, act="getOtherItems")

    # ---- 订单写入 / 修改
    def create(self, data: Dict[str, Any], *, extend: Optional[int] = None) -> Dict[str, Any]:
        return self.client.input(self.DT, data, extend=extend)

    def update(self, data: Dict[str, Any], *, extend: Optional[int] = None) -> Dict[str, Any]:
        """注意 goods 为全量替换：修改时需带上需保留的各条明细。"""
        if "id" not in data and "No." not in data:
            raise ValueError("修改订单需提供 id 或 No.")
        return self.client.update(self.DT, data, extend=extend)

    def ship_partial_no_stock(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """订单分批发货（不计算库存的商品）：data 含 id 或 No.、goods[{pro_id|sn, amount, plan}]、sendcomp、sendcode 等。"""
        return self.client.cmdact(self.DT, data, act="sendGoods_no_stock")

    # ---- 发货单
    def shipments(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        """发货单读取（dt=sendgoods）；filters 可用 id、memo（按备注精确匹配，用于幂等校验）。"""
        return self.client.iter_output("sendgoods", lastid=lastid, **filters)

    def update_shipment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发货单修改（extend=1）：id 或 sn 定位；sntype/num/package_type/weight/volume/cost/costtype/sendcomp/sendcode/…、deli_note[]。"""
        if "id" not in data and "sn" not in data:
            raise ValueError("修改发货单需提供 id 或 sn")
        return self.client.update("sendgoods", data, extend=1)

    # ---- 收发货通知单（外部库存）
    def notices(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        """filters：type、status、lasttime、id。"""
        return self.client.iter_output("sr_notice", lastid=lastid, **filters)

    def notice_set_status(self, id: Id, status: int, *, erp_no: Optional[str] = None, log: Optional[str] = None) -> Dict[str, Any]:
        data: Dict[str, Any] = {"id": id, "status": status}
        if erp_no is not None:
            data["erp_no"] = erp_no
        if log:
            data["log"] = log
        return self.client.cmdact("sr_notice", data, act="chgst")

    def notice_execute(self, data: Dict[str, Any], *, no_more: bool = True) -> Dict[str, Any]:
        """执行通知单：data 含 id 或 erp_no、who、date、sendcode、child[{prod,num,costprice,memo}]。"""
        payload = {**data}
        if no_more:
            payload["no_more"] = 1
        return self.client.cmdact("sr_notice", payload, act="exc")

    # ---- 出库单 / 入库单
    def outbounds(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("libout", lastid=lastid, **filters)

    def create_outbound(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """返回 ret.id 为出库单 ID；随后可 complete_outbound(id)。"""
        return self.client.input("libout", data)

    def complete_outbound(self, id: Id) -> Dict[str, Any]:
        return self.client.cmdact("libout", {"id": id}, act="liboutok")

    def create_inbound(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.input("libin", data)

    def complete_inbound(self, id: Id) -> Dict[str, Any]:
        return self.client.cmdact("libin", {"id": id}, act="libinok")

    # ---- 报价单
    def create_quote(self, data: Dict[str, Any], *, extend: int = 1) -> Dict[str, Any]:
        return self.client.input("price", data, extend=extend)

    def update_quote(self, data: Dict[str, Any], *, extend: int = 1) -> Dict[str, Any]:
        """pricedetail 同样为全量替换。"""
        return self.client.update("price", data, extend=extend)

    # ---- 合同（contract0）
    def contracts(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("contract0", lastid=lastid, **filters)

    def create_contract(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.input("contract0", data)

    # ---- 字典
    def dictionary(self, field: str) -> List[Dict[str, Any]]:
        return self.client.dictionary(self.DT, field)

    def field_names(self) -> Dict[str, str]:
        return self.client.field_names(self.DT)
