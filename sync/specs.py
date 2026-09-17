"""P0 只读镜像：各数据表的同步规格。

同步模式（mode）：
    lasttime  —— 首次全量；之后按 lasttime（末次修改时间，含新增与修改）增量，重叠 30 分钟以吸收时钟偏差；每周全量一次以检测删除
    lastid    —— 首次全量；之后按 lastid 拉新增；每隔 full_every_hours 小时全量重拉一次（捕获状态变化并检测删除）；
                 另可配置 refresh_params：每次运行按过滤条件重拉活动单据
    full      —— 每次运行全量重拉（仅用于小表）

列名映射：JSON 键 "No." → 列 no_ ；其余键原样（仅替换非法字符为下划线）。所有字段同时保留在原始 JSON 表中，规范化表只挑选常用列。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ChildSpec:
    key: str          # 记录里的子数组键，如 goods
    table: str        # 子表名，如 contract_goods
    parent_col: str   # 子表中指向父记录的列名，如 contract_id
    columns: List[str]


@dataclass
class TableSpec:
    dt: str
    table: str
    mode: str
    columns: List[str]
    extend: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)
    children: List[ChildSpec] = field(default_factory=list)
    refresh_params: List[Callable[[], Dict[str, Any]]] = field(default_factory=list)
    full_every_hours: Optional[float] = None
    optional: bool = False
    note: str = ""


def _recent_days(days: int) -> Callable[[], Dict[str, Any]]:
    def make() -> Dict[str, Any]:
        end = dt.date.today()
        start = end - dt.timedelta(days=days)
        return {"date": f"{start.isoformat()},{end.isoformat()}"}
    return make


CUSTOMER_COLUMNS = [
    "sn", "cu_name", "m_name", "life", "cu_status", "period", "type", "cu_from", "industry", "employees",
    "rala_rating", "state", "city", "district", "address", "tel", "web", "country", "owner", "uid", "info",
    "cu_remark", "qydate", "creatdate", "moddate", "contract_money", "gathering_note_money", "gathering_money",
    "receivable_money", "bill_money", "imprest_money",
]
CONTACT_COLUMNS = ["name", "headship", "department", "mphone", "phone", "qq", "weixin", "email", "sex", "islinkman", "birthday", "remark"]

TABLE_SPECS: List[TableSpec] = [
    TableSpec("user", "crm_user", "full", ["user", "part", "name", "dept", "status", "type", "isadmin"], note="用户"),
    TableSpec("csstree", "product_class", "full", ["tid", "title", "upid", "status"], note="产品分类"),
    TableSpec("product", "product", "lasttime",
              ["sn", "name", "model", "sku", "class", "price", "costprice", "unit", "lnum", "lup", "ldown", "ptype", "status",
               "mflag", "manufacturer", "batchnum", "weight", "w_unit", "pow_type", "pmode", "intro", "parameter", "memo", "flow_id"],
              full_every_hours=24 * 7, note="产品"),
    TableSpec("prod_alias", "product_alias", "full", ["cu_sn", "cu_id", "pid", "name", "sn", "memo"], note="产品客制别名"),
    TableSpec("customer", "customer", "lasttime", CUSTOMER_COLUMNS, extend=1,
              children=[ChildSpec("contact", "contact", "customer_id", CONTACT_COLUMNS)], full_every_hours=24 * 7, note="客户（含联系人）"),
    TableSpec("customerext", "customer_ext", "lastid", [], full_every_hours=24, note="客户自定义字段（全部列动态展开）"),
    TableSpec("contract", "contract", "lastid",
              ["No.", "subject", "cu_sn", "cu_no", "type", "one_select", "status", "confirm", "st_send", "sum", "who", "memo",
               "name", "tel", "addr", "mphone", "date", "end_date", "money_type", "money_rate", "pay_mode", "payment",
               "cu_sub", "prj_id", "op_id", "org_id"],
              extend=1,
              children=[ChildSpec("goods", "contract_goods", "contract_id",
                                  ["prod", "prod_name", "model", "sku", "batchnum", "amount", "un_price", "sum", "tax_money", "tax_rate", "zk", "memo"])],
              refresh_params=[lambda: {"status": 1}, _recent_days(90)], full_every_hours=24 * 7, note="订单（CRM 称合同）"),
    TableSpec("contract0", "contract0", "lastid",
              ["No.", "subject", "cu_sn", "type", "sum", "sum_memo", "back_sum", "who", "status", "date", "begin_date", "end_date",
               "money_type", "money_rate", "payment", "pay_mode", "cu_user", "deli_place", "prj_id", "op_id", "memo"],
              full_every_hours=24, note="合同"),
    TableSpec("sendgoods", "sendgoods", "lastid",
              ["co_id", "cu_sn", "date", "status", "who", "sn", "memo", "sendcomp", "sendcode", "name", "addr", "tel"],
              children=[ChildSpec("deli_note", "sendgoods_items", "sendgoods_id", ["pid", "price", "num", "tax", "sum", "memo"])],
              full_every_hours=24, note="发货单"),
    TableSpec("libout", "libout", "lasttime",
              ["title", "lib", "libname", "cu_sn", "co_sn", "date", "who", "memo", "mes_work_order_id"],
              children=[ChildSpec("libitem", "libout_items", "libout_id", ["prod", "pid", "pro_name", "model", "sku", "sn", "batchnum", "num", "cprice", "memo"])],
              full_every_hours=24 * 7, note="出库单"),
    TableSpec("libreturn", "order_return", "lastid",
              ["subject", "cu_sn", "co_id", "status", "ra_who", "ra_date", "lib", "date", "who", "who_name", "return_no",
               "st_libin", "st_hk", "hk_sum", "money", "money_type", "money_rate", "one_select", "sendcode", "memo"],
              children=[ChildSpec("rtnitem", "order_return_items", "return_id", ["pid", "rnum", "rprice", "rsum", "nin", "reason", "memo"])],
              full_every_hours=24, note="订单退货单"),
    TableSpec("purchase", "purchase", "lastid",
              ["No.", "title", "cu_sn", "type", "status0", "status", "money", "amount_before_tax", "backsum", "return_yn", "lib",
               "who", "memo", "eta", "confirm", "ref_cu_id", "ref_co_id", "prj_id", "sendcode", "is_zhifa", "date", "money_type", "money_rate"],
              children=[ChildSpec("puritem", "purchase_items", "purchase_id",
                                  ["prod", "prod_name", "model", "sku", "batchnum", "num", "price", "money", "backnum", "tax_rate", "tax_money", "un_price_tax", "memo"])],
              full_every_hours=24, note="采购单"),
    TableSpec("purreturn", "purchase_return", "lastid",
              ["subject", "cu_sn", "pu_id", "status", "ra_who", "ra_date", "lib", "date", "who", "who_name", "return_no",
               "st_libout", "st_hk", "hk_sum", "money", "money_type", "money_rate", "one_select", "memo"],
              children=[ChildSpec("purrtnitem", "purchase_return_items", "return_id", ["pid", "rnum", "rprice", "rsum", "nout", "reason", "memo"])],
              full_every_hours=24, note="采购退货单"),
    TableSpec("pay_plan", "pay_plan", "lastid",
              ["date", "serial", "money_type", "money_rate", "money", "money_memo", "who", "status", "pu_id", "cu_sn", "ctype", "type",
               "exp_date", "pay_com", "rec_com", "bank", "acc_no", "memo", "owner", "prj_id", "bill_num"],
              full_every_hours=24, note="付款计划"),
    TableSpec("gathering", "gathering", "lastid",
              ["date", "serial", "money", "status", "who", "principal", "cu_sn", "co_sn", "prj_id", "memo"],
              full_every_hours=24, note="计划回款"),
    TableSpec("gathering_note", "gathering_note", "lastid",
              ["cu_sn", "co_id", "date", "invoice", "serial", "money", "type", "ctype", "gtype", "owner", "who", "memo", "money_type"],
              full_every_hours=24, note="回款记录"),
    TableSpec("opport", "opport", "lastid",
              ["oppname", "cu_sn", "cu_sub", "date", "expdate", "exprev", "oppowner", "phase", "status", "type", "probability",
               "leadsource", "pnote", "cu_require", "provider", "creatdate", "moddate"],
              extend=1, full_every_hours=24, note="销售机会"),
    TableSpec("action", "action", "lastid",
              ["cale", "subject", "content", "type", "cu_sn", "con_id", "who", "date", "endate", "op_id", "prj_id", "co_id"],
              note="行动记录 / 待办"),
    TableSpec("sr_notice", "sr_notice", "lastid",
              ["subject", "cu_sn", "lib", "libname", "erp_no", "type", "mid", "status", "who", "memo", "name", "mphone", "addr",
               "date", "eta", "sendcomp", "sendcode"],
              children=[ChildSpec("sr_notice_item", "sr_notice_items", "notice_id",
                                  ["prod", "num", "num_exc", "memo", "prod_name", "model", "sku", "batchnum", "price", "money_type", "money_rate"])],
              full_every_hours=24, optional=True, note="收发货通知单（需外部库存）"),
]

SPEC_BY_DT: Dict[str, TableSpec] = {s.dt: s for s in TABLE_SPECS}

# 字典：与 scripts/dump_dictionary.py 保持一致
DICT_FIELDS: Dict[str, List[str]] = {
    "customer": ["cu_status", "type", "cu_from", "employees", "industry", "life", "rala_rating", "country"],
    "contract": ["type", "status", "pay_mode", "payment", "one_select", "confirm", "st_send"],
    "product": ["unit", "pow_type", "class", "ptype", "status", "pmode"],
    "gathering_note": ["type", "ctype", "invoice"],
    "gathering": ["status", "type"],
    "bill": ["type"],
    "sendgoods": ["sntype", "package_type", "costtype", "status", "one_select"],
    "action": ["type", "cale"],
    "purchase": ["type", "status0"],
    "contact": ["contype"],
    "libreturn": ["one_select"],
    "purreturn": ["one_select"],
}
FIELD_NAME_TABLES = ["customer", "contact", "contract", "product", "gathering", "gathering_note", "bill", "sendgoods",
                     "purchase", "purreturn", "libreturn", "repairinfo", "action", "opport"]
