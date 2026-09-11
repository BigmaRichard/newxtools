"""财务模块：gathering（计划回款）/ gathering_note（回款记录）/ bill（开票记录）/ bill_apply（开票申请）/
pay_plan（付款计划）/ purchase（采购单）/ cost（批单报销）/ costdetail（费用明细）。

字段要点（摘自文档）：
* 计划回款（dt=gathering）：id、date、serial（期次）、money、status（是否回款）、who、principal、cu_sn、co_sn、prj_id、memo。
  读取可用 memo 精确匹配做唯一性校验；修改时不可传 cu_sn（客户不可改）。
* 回款记录（dt=gathering_note）：cu_sn、co_id（订单 ID 或编号，可不传）、date（必填）、invoice（1 是;2 否;3 无需开票）、
  serial、money（必填）、type（付款方式，必填）、ctype、who（所有者 part）。写入返回 ret.id。
* 开票记录（dt=bill）：cu_sn、co_sn|co_id、type（票据类型）、tax_rate、content、money、billsn（发票号）、money_type、money_rate、
  date、serial、who、cu_sub、sthk、stjh、sendcode、mphone、address、memo。写入返回 ret.id。
* 开票申请的开票动作：api.cmdact dt=bill_apply act=kaipiao data={id:开票申请ID, billsn:票号}。
* 付款计划（dt=pay_plan）：date、serial、money、cu_sn（供应商编号）、money_type、money_rate、who、status、pu_id、ctype、type、
  exp_date、pay_com、rec_com、bank、acc_no、others、memo。
* 采购单（dt=purchase，写入 extend=1）：title、cu_id|cu_sn、"No."、date、eta、type、status0、lib、address、who、money_type、money_rate、
  money、amount_before_tax、ref_cu_id、ref_co_id、prj_id、j1…、puritem[{prod,num,price,money,tax_rate,memo}]。
* 批单报销（dt=cost）读取可按 lasttime、baox_st1、aprv_status 过滤；修改注意 aprv_status=4/5 会终结 CRM 审批且不可再改。
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Union

from ..client import XToolsClient

Id = Union[int, str]


class FinanceAPI:
    def __init__(self, client: XToolsClient):
        self.client = client

    # ---- 计划回款
    def planned_receipts(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("gathering", lastid=lastid, **filters)

    def create_planned_receipt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.input("gathering", data)

    def update_planned_receipt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in data:
            raise ValueError("修改计划回款需提供 id")
        data = {k: v for k, v in data.items() if k != "cu_sn"}  # 文档：客户不可修改
        return self.client.update("gathering", data)

    # ---- 回款记录
    def receipts(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        """filters 可用 memo 精确匹配做幂等校验。"""
        return self.client.iter_output("gathering_note", lastid=lastid, **filters)

    def create_receipt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("date", "money", "type"):
            if key not in data:
                raise ValueError(f"回款记录缺少必填字段 {key}")
        return self.client.input("gathering_note", data)

    # ---- 开票
    def create_invoice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """开票记录写入（dt=bill）。"""
        return self.client.input("bill", data)

    def issue_invoice_for_apply(self, apply_id: Id, billsn: str) -> Dict[str, Any]:
        """对开票申请执行开票动作（act=kaipiao）。"""
        return self.client.cmdact("bill_apply", {"id": apply_id, "billsn": billsn}, act="kaipiao")

    # ---- 付款计划
    def payment_plans(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("pay_plan", lastid=lastid, **filters)

    def create_payment_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.input("pay_plan", data)

    # ---- 采购单
    def purchases(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("purchase", lastid=lastid, **filters)

    def create_purchase(self, data: Dict[str, Any], *, extend: int = 1) -> Dict[str, Any]:
        return self.client.input("purchase", data, extend=extend)

    # ---- 报销 / 费用
    def expense_claims(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        """批单报销（dt=cost）；filters：lasttime、baox_st1、aprv_status。"""
        return self.client.iter_output("cost", lastid=lastid, **filters)

    def update_expense_claim(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in data and "number" not in data:
            raise ValueError("修改批单报销需提供 id 或 number")
        return self.client.update("cost", data)

    def expense_details(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("costdetail", lastid=lastid, **filters)

    # ---- 字典
    def dictionary(self, dt: str, field: str) -> List[Dict[str, Any]]:
        """如 dictionary("gathering_note","type")（付款方式）、dictionary("bill","type")（票据类型）。"""
        return self.client.dictionary(dt, field)
