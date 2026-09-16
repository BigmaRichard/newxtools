"""客户与联系人模块：customer / customerext / cuview / action / jk_collect。

字段要点（摘自文档）：
* customer 读取（api.output dt=customer）过滤参数：lastid、id、sn、name、lasttime（时间串或时间戳）、
  life（1 潜在;2 签约;3 重复购买;4 失效，多个用逗号）、type（客户种类）、cu_status（客户阶段）、employees、extend=1（含扩展字段）。
* 单条客户主要字段：id、cu_name、life、sn、address、cu_remark、cu_from、state（省份编码 1–35）、city、district、
  rala_rating、qydate、creatdate、moddate、tianyancha{...}、contact[{id,name,headship,mphone,qq,weixin,email,sex,islinkman}]。
  extend=1 追加：type、period、uid、info、tel、web、country、industry、employees、m_name、owner、bill_content。
* 客户写入（api.input dt=customer）data：cu_name、sn、life、address、cu_remark、cu_from、state、city、district、
  contact[...]；extend=1 时可写 type、period、uid、info、tel、web、country、industry、employees、m_name。
  所有者默认为登录人 part；需指定所有者时先写入再调用客户转移。
* 客户修改（api.update dt=customer）只改客户表不改联系人；data 中以 id 或 sn 定位；改 sn 时需提供 id。
* 联系人修改（api.update dt=contact，文档 2026-09-01 版新增）：data.id 必填且不能为 0，不能传 cu_sn（客户不可改）；
  可改 name、sex（2 男;1 女）、appellation、department、headship、preside、phone、mphone、mphone_s、fax、email、qq、weixin、
  wx_name、qq_name、h_phone、h_addr、h_pst、birthday、remark、cr_ty（1 身份证;2 军官证;3 护照;4 其他1;5 其他2）、cr_sn、
  islinkman（0 联系人;1 主联系人;2 个人客户;3 离职）、用户画像字段 ext_selN / ext_itemN；示例带 extend=1。
* 自定义字段：读取 dt=customerext；写入 api.input dt=customerext，data={"sn"|"id", "ext_itemN": ...}。
* 个人客户写入：api.input dt=cuview。
* 行动记录：dt=action，cale 1 日程;2 待办任务;3 记录;4 *待办任务；op_id / prj_id 只能有一个。
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Union

from ..client import XToolsClient

Id = Union[int, str]


class CustomerAPI:
    DT = "customer"

    def __init__(self, client: XToolsClient):
        self.client = client

    # ---- 读取
    def get(self, id: Optional[Id] = None, *, sn: Optional[str] = None, name: Optional[str] = None, extend: int = 1) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {"extend": extend}
        if id is not None:
            params["id"] = id
        elif sn is not None:
            params["sn"] = sn
        elif name is not None:
            params["name"] = name
        else:
            raise ValueError("id / sn / name 至少提供一个")
        rows = self.client.output(self.DT, **params)
        return rows[0] if rows else None

    def list(self, *, lastid: int = 0, extend: int = 1, **filters: Any) -> List[Dict[str, Any]]:
        """一页客户（≤100）。filters 如 lasttime="2026-09-01 00:00:00"、life="2,3"、type=1、cu_status=1。"""
        return self.client.output(self.DT, lastid=lastid, extend=extend, **filters)

    def iter(self, *, lastid: int = 0, extend: int = 1, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output(self.DT, lastid=lastid, extend=extend, **filters)

    # ---- 写入 / 修改
    def create(self, data: Dict[str, Any], *, extend: Optional[int] = None) -> Dict[str, Any]:
        """新建企业客户（含联系人数组 contact）。返回 ret：{"ok":1,"msg":"添加客户成功"}。"""
        return self.client.input(self.DT, data, extend=extend)

    def update(self, data: Dict[str, Any], *, extend: Optional[int] = None) -> Dict[str, Any]:
        """修改客户主表；data 需含 id 或 sn 作为定位条件，只传变化字段。"""
        if "id" not in data and "sn" not in data:
            raise ValueError("修改客户需提供 id 或 sn")
        return self.client.update(self.DT, data, extend=extend)

    def transfer(self, owner: str, *, id: Optional[Id] = None, sn: Optional[str] = None) -> Dict[str, Any]:
        """客户转移（api.chgown）：owner 为业务员姓名或 part。"""
        return self.client.chgown(owner, id=id, sn=sn, dt=self.DT)

    # ---- 联系人
    def update_contact(self, data: Dict[str, Any], *, extend: Optional[int] = 1) -> Dict[str, Any]:
        """修改联系人（api.update dt=contact）：data.id 必填；不能带 cu_sn；只传变化字段。返回 ret：{"ok":1,"msg":"修改联系人成功"}。"""
        if not data.get("id"):
            raise ValueError("修改联系人需提供非 0 的 id")
        if "cu_sn" in data:
            raise ValueError("联系人的所属客户不可修改，data 中不能包含 cu_sn")
        return self.client.update("contact", data, extend=extend)

    # ---- 自定义字段（customerext）
    def ext_get(self, id: Optional[Id] = None, *, sn: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if id is not None:
            params["id"] = id
        elif sn is not None:
            params["sn"] = sn
        rows = self.client.output("customerext", **params)
        return rows[0] if rows else None

    def ext_iter(self, *, lastid: int = 0) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("customerext", lastid=lastid)

    def ext_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """写自定义字段：data={"sn":"00003","ext_item5":"..."}（以 sn 或 id 定位，字段名以 ext_ 开头）。"""
        if "id" not in data and "sn" not in data:
            raise ValueError("写自定义字段需提供 id 或 sn")
        return self.client.input("customerext", data)

    # ---- 个人客户
    def create_personal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """个人客户写入（dt=cuview）：name、mphone、department、preside、sex、cr_ty、cr_sn、sn、type、period、cu_from …"""
        return self.client.input("cuview", data)

    # ---- 行动记录 / 待办
    def actions(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("action", lastid=lastid, **filters)

    def add_action(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """行动记录写入：{"id":0,"cale":"3","subject":..,"content":..,"cu_sn":..,"date":"YYYY-MM-DD","who":"M2,M4,"}"""
        return self.client.input("action", data)

    # ---- 附件
    def attachments(self, id: Id, *, field: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.client.downfile(self.DT, id, field=field)

    # ---- 获客线索
    def leads(self, *, lastid: int = 0, **filters: Any) -> Iterator[Dict[str, Any]]:
        return self.client.iter_output("jk_collect", lastid=lastid, **filters)

    def add_lead(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """获客线索写入：come_from、com_name、con_name、con_type、cost、opport、memo、owner、mark_id。"""
        return self.client.input("jk_collect", data)

    # ---- 字典
    def dictionary(self, field: str) -> List[Dict[str, Any]]:
        """客户表字段的数据字典，如 cu_status / type / cu_from / employees / industry。"""
        return self.client.dictionary(self.DT, field)

    def field_names(self) -> Dict[str, str]:
        return self.client.field_names(self.DT)
