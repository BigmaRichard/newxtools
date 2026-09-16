"""售后模块：repairinfo（维修工单）。

字段要点（摘自文档，2026-09-01 版补充了读取返回字段）：
* 写入（api.input dt=repairinfo）data：id=0、"No."（维修工单编号）、who（接单人 part 或姓名）、date（接件日期）、recv_time（接件时间 HH:MM）、
  cu_sn（客户编号）、name / tel / phone（联系人及电话、手机）、
  repairinfo[{id:0, prod（产品编码）, pdate（生产日期）, sdate（销售日期）, info（故障描述）, notice（沟通要点）, bx_status（1 在保;2 出保）, dept（承接部门）}]。
* 读取（api.output dt=repairinfo）过滤 lastid / id；返回主单字段同上，另有：
  goods[{id, pid, pro_name, model, spec, amount, un_price, sum, rep_sum（厂家承担金额）, memo}] —— 维修配件及服务明细。
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, Optional, Union

from ..client import XToolsClient

Id = Union[int, str]


class RepairAPI:
    DT = "repairinfo"

    def __init__(self, client: XToolsClient):
        self.client = client

    def get(self, id: Id) -> Optional[Dict[str, Any]]:
        return self.client.output_one(self.DT, id)

    def iter(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output(self.DT, lastid=lastid, **filters)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """维修工单写入；返回 ret：{"ok":1,"msg":"添加维修工单成功"}。"""
        return self.client.input(self.DT, data)
