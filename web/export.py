"""导出 Excel：把各列表接口的结果（按当前筛选，不分页，最多 EXPORT_MAX 行）写成 .xlsx。

每种导出定义为 (文件名前缀, 取数函数, 列定义)；列定义为 (表头, 取值函数)。取值函数拿到接口返回的一行 dict。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Sequence, Tuple

from .xlsx import write_xlsx

EXPORT_MAX = 20000
Col = Tuple[str, Callable[[Dict[str, Any]], Any]]


@dataclass
class Download:
    filename: str
    data: bytes
    content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _cust(key: str = "customer") -> Callable[[Dict[str, Any]], Any]:
    return lambda r: ((r.get(key) or {}).get("name") or "")


def _num(value: Any) -> Any:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _join(value: Any) -> str:
    return "、".join(value) if isinstance(value, list) else (value or "")


ORDER_COLS: List[Col] = [
    ("日期", lambda r: r.get("date")), ("单号", lambda r: r.get("no")), ("客户", _cust()), ("客户ID", lambda r: (r.get("customer") or {}).get("id")),
    ("主题", lambda r: r.get("subject")), ("金额", lambda r: _num(r.get("amount"))), ("币种", lambda r: r.get("money_type")), ("已回款", lambda r: _num(r.get("received"))),
    ("状态", lambda r: r.get("status_text")), ("审批", lambda r: r.get("confirm_text")), ("发货状态", lambda r: r.get("st_send_text")), ("发货单数", lambda r: r.get("shipments")),
    ("业务员", lambda r: r.get("who")), ("类型", lambda r: r.get("type_text")), ("付款", lambda r: r.get("payment_text")), ("付款模式", lambda r: r.get("pay_mode_text")),
    ("发票类型", lambda r: r.get("invoice_type")), ("付款方式", lambda r: r.get("pay_terms")), ("货期", lambda r: r.get("lead_time")), ("是否试用", lambda r: r.get("trial")), ("首单签约", lambda r: r.get("first_sign")),
    ("收货人", lambda r: r.get("contact_name")), ("手机", lambda r: r.get("mphone")), ("地址", lambda r: r.get("addr")), ("备注", lambda r: r.get("memo")),
]
CUSTOMER_COLS: List[Col] = [
    ("客户", lambda r: r.get("name")), ("简称", lambda r: r.get("short")), ("编号", lambda r: r.get("sn")), ("ID", lambda r: r.get("id")), ("所有者", lambda r: r.get("owner")),
    ("周期", lambda r: r.get("life_text")), ("类型", lambda r: r.get("type_text")), ("阶段", lambda r: r.get("stage_text")), ("行业", lambda r: r.get("industry_text")),
    ("城市", lambda r: r.get("city")), ("电话", lambda r: r.get("tel")), ("地址", lambda r: r.get("address")), ("创建", lambda r: r.get("created")), ("修改", lambda r: r.get("modified")),
    ("订单数", lambda r: r.get("orders")), ("订单额", lambda r: _num(r.get("order_amount"))), ("最近订单", lambda r: r.get("last_order")), ("回款额", lambda r: _num(r.get("receipts"))), ("联系人数", lambda r: r.get("contacts")),
]
RECEIVABLE_COLS: List[Col] = [
    ("计划日期", lambda r: r.get("date")), ("客户", _cust()), ("订单号", lambda r: r.get("order_no")), ("期次", lambda r: r.get("serial")), ("金额", lambda r: _num(r.get("amount"))),
    ("状态", lambda r: r.get("status_text")), ("逾期天数", lambda r: r.get("overdue_days")), ("业务员", lambda r: r.get("who")), ("备注", lambda r: r.get("memo")),
]
RECEIVABLE_WHO_COLS: List[Col] = [
    ("业务员", lambda r: r.get("who")), ("未回期数", lambda r: r.get("count")), ("未回金额", lambda r: _num(r.get("amount"))),
    ("逾期期数", lambda r: r.get("overdue_count")), ("逾期金额", lambda r: _num(r.get("overdue"))),
    ("逾期≤30天", lambda r: _num((r.get("aging") or {}).get("d30"))), ("逾期31–90天", lambda r: _num((r.get("aging") or {}).get("d90"))),
    ("逾期91–365天", lambda r: _num((r.get("aging") or {}).get("d365"))), ("逾期超1年", lambda r: _num((r.get("aging") or {}).get("d365p"))),
]
RECEIPT_COLS: List[Col] = [
    ("日期", lambda r: r.get("date")), ("客户", _cust()), ("订单号", lambda r: r.get("order_no")), ("金额", lambda r: _num(r.get("amount"))), ("币种", lambda r: r.get("money_type")),
    ("付款方式", lambda r: r.get("type_text")), ("分类", lambda r: r.get("ctype_text")), ("开票", lambda r: r.get("invoice_text")), ("期次", lambda r: r.get("serial")),
    ("业务员", lambda r: r.get("who")), ("所有者", lambda r: r.get("owner")), ("备注", lambda r: r.get("memo")),
]
ACTION_COLS: List[Col] = [
    ("日期", lambda r: r.get("date")), ("结束日期", lambda r: r.get("end_date")), ("人员", lambda r: _join(r.get("who"))), ("类型", lambda r: r.get("type_text")), ("日程", lambda r: r.get("cale_text")),
    ("客户", _cust()), ("联系人", lambda r: r.get("contact")), ("提及", lambda r: _join(r.get("mentions"))), ("标题", lambda r: r.get("subject")), ("内容", lambda r: r.get("content")),
    ("字数", lambda r: r.get("chars")), ("关联订单", lambda r: r.get("order_id")), ("日期标记", lambda r: {"future": "日期异常", "invalid": "无日期"}.get(r.get("date_flag") or "", "")),
]
PRODUCT_COLS: List[Col] = [
    ("编号", lambda r: r.get("sn")), ("名称", lambda r: r.get("name")), ("型号", lambda r: r.get("model")), ("SKU", lambda r: r.get("sku")), ("分类", lambda r: r.get("class")), ("大类", lambda r: r.get("group")),
    ("单位", lambda r: r.get("unit")), ("价格", lambda r: _num(r.get("price"))), ("状态", lambda r: r.get("status")), ("库存", lambda r: _num(r.get("stock"))), ("库存上限", lambda r: _num(r.get("lup"))), ("库存下限", lambda r: _num(r.get("ldown"))),
    ("低于下限", lambda r: "是" if r.get("stock_low") else ""), ("销售额", lambda r: _num(r.get("sales_amount"))), ("销售数量", lambda r: _num(r.get("sales_qty"))), ("订单数", lambda r: r.get("sales_orders")),
    ("客户数", lambda r: r.get("sales_customers")), ("最近销售", lambda r: r.get("last_sale")), ("生产厂家", lambda r: r.get("manufacturer")), ("备注", lambda r: r.get("memo")),
]
PURCHASE_COLS: List[Col] = [
    ("日期", lambda r: r.get("date")), ("单号", lambda r: r.get("no")), ("标题", lambda r: r.get("title")), ("供应商", _cust("supplier")), ("类型", lambda r: r.get("type_text")), ("状态", lambda r: r.get("status0_text")),
    ("入库状态", lambda r: r.get("status_text")), ("审批", lambda r: r.get("confirm_text")), ("金额", lambda r: _num(r.get("money"))), ("币种", lambda r: r.get("money_type")), ("汇率", lambda r: _num(r.get("money_rate"))),
    ("折算人民币", lambda r: _num(r.get("rmb"))), ("未税金额", lambda r: _num(r.get("before_tax"))), ("已付", lambda r: _num(r.get("paid"))), ("经办", lambda r: r.get("who")), ("预计到货", lambda r: r.get("eta")),
    ("明细行数", lambda r: r.get("items")), ("备注", lambda r: r.get("memo")),
]
PAY_PLAN_COLS: List[Col] = [
    ("计划日期", lambda r: r.get("date")), ("供应商", _cust("supplier")), ("采购单号", lambda r: r.get("purchase_no")), ("采购标题", lambda r: r.get("purchase_title")), ("期次", lambda r: r.get("serial")),
    ("金额", lambda r: _num(r.get("money"))), ("币种", lambda r: r.get("money_type")), ("折算人民币", lambda r: _num(r.get("rmb"))), ("状态", lambda r: r.get("status_text")), ("逾期天数", lambda r: r.get("overdue_days")),
    ("付款方式", lambda r: r.get("type_text")), ("经办", lambda r: r.get("who")), ("所有者", lambda r: r.get("owner")), ("预计日期", lambda r: r.get("exp_date")), ("票号", lambda r: r.get("bill_num")), ("备注", lambda r: r.get("memo")),
]
CONTACT_COLS: List[Col] = [
    ("姓名", lambda r: r.get("name")), ("客户", _cust()), ("客户ID", lambda r: (r.get("customer") or {}).get("id")), ("所有者", lambda r: (r.get("customer") or {}).get("owner")),
    ("职务", lambda r: r.get("headship")), ("部门", lambda r: r.get("department")), ("手机", lambda r: r.get("mphone")), ("电话", lambda r: r.get("phone")), ("微信", lambda r: r.get("weixin")),
    ("QQ", lambda r: r.get("qq")), ("邮箱", lambda r: r.get("email")), ("无联系方式", lambda r: "是" if r.get("missing") else ""),
    ("客户建档", lambda r: (r.get("customer") or {}).get("created")), ("客户订单额", lambda r: _num((r.get("customer") or {}).get("amount"))),
    ("客户联系人数", lambda r: (r.get("customer") or {}).get("contacts")), ("现对接", lambda r: (r.get("customer") or {}).get("latest_contact_name")),
    ("最近联系", lambda r: r.get("last_contact")), ("日志条数", lambda r: r.get("actions")),
    ("备注", lambda r: r.get("remark")),
]
_CUST_BASE: List[Col] = [("客户", lambda r: r.get("name")), ("客户ID", lambda r: r.get("id")), ("所有者", lambda r: r.get("owner")), ("周期", lambda r: r.get("life_text")), ("城市", lambda r: r.get("city"))]
TIER_COLS: List[Col] = [("分层", lambda r: r.get("tier")), *_CUST_BASE, ("本年金额", lambda r: _num(r.get("amount"))), ("占比%", lambda r: _num(r.get("share"))), ("累计占比%", lambda r: _num(r.get("cum_share"))),
                        ("本年单数", lambda r: r.get("count")), ("上年金额", lambda r: _num(r.get("prev_amount"))), ("首单", lambda r: r.get("first_date")), ("末单", lambda r: r.get("last_date"))]
NEW_COLS: List[Col] = [*_CUST_BASE, ("首单日期", lambda r: r.get("first_date")), ("本年金额", lambda r: _num(r.get("amount"))), ("本年单数", lambda r: r.get("count"))]
CHURN_COLS: List[Col] = [*_CUST_BASE, ("末单日期", lambda r: r.get("last_date")), ("未下单天数", lambda r: r.get("idle_days")), ("历史单数", lambda r: r.get("count")), ("历史金额", lambda r: _num(r.get("amount"))), ("首单", lambda r: r.get("first_date"))]
LOST_COLS: List[Col] = [*_CUST_BASE, ("末单日期", lambda r: r.get("last_date")), ("上年金额", lambda r: _num(r.get("prev_amount"))), ("上年单数", lambda r: r.get("prev_count"))]


def _sales_sheet(res: Dict[str, Any]) -> Tuple[Sequence[str], List[List[Any]]]:
    years = [str(y) for y in res["years"]]
    line = res.get("line_mode")
    headers = ["名称", "说明"]
    for y in years:
        headers += [f"{y} 金额", f"{y} 单数"] + ([f"{y} 数量"] if line else [])
    headers += ["合计", "同比%"]
    rows = []
    for r in res["rows"]:
        row: List[Any] = [r.get("name"), r.get("sub")]
        for y in years:
            c = r["cells"].get(y) or {}
            row += [_num(c.get("amount", 0)), c.get("count", 0)] + ([_num(c.get("qty", 0))] if line else [])
        row += [_num(r.get("total")), _num(r.get("yoy"))]
        rows.append(row)
    return headers, rows


def build_export(q: Any, kind: str) -> Download:
    """q 为 web.server.Query（已设置 max_size）。"""
    today = dt.date.today().strftime("%Y%m%d")
    simple = {
        "orders": ("订单", lambda: q.orders()["rows"], ORDER_COLS),
        "customers": ("客户", lambda: q.customers()["rows"], CUSTOMER_COLS),
        "receivables": ("计划回款", lambda: q.receivables()["rows"], RECEIVABLE_COLS),
        "receivables_by_who": ("未回款按业务员", lambda: q.receivables()["by_who"], RECEIVABLE_WHO_COLS),
        "receipts": ("回款记录", lambda: q.receipts()["rows"], RECEIPT_COLS),
        "actions": ("工作日志", lambda: q.actions()["rows"], ACTION_COLS),
        "products": ("产品", lambda: q.products()["rows"], PRODUCT_COLS),
        "purchases": ("采购单", lambda: q.purchases()["rows"], PURCHASE_COLS),
        "pay_plans": ("付款计划", lambda: q.pay_plans()["rows"], PAY_PLAN_COLS),
        "contacts": ("联系人", lambda: q.contacts()["rows"], CONTACT_COLS),
        "tiers": ("客户分层", lambda: q.customer_analysis()["tier_rows"], TIER_COLS),
        "new_customers": ("新客户", lambda: q.customer_analysis()["new_rows"], NEW_COLS),
        "churn": ("流失预警", lambda: q.customer_analysis()["churn"]["rows"], CHURN_COLS),
        "lost": ("上年有单今年未下单", lambda: q.customer_analysis()["lost_rows"], LOST_COLS),
    }
    if kind == "sales":
        res = q.sales()
        headers, rows = _sales_sheet(res)
        title = {"who": "按业务员", "customer": "按客户", "product": "按产品", "class": "按分类", "group": "按大类", "region": "按地区", "type": "按类型", "month": "按月份"}.get(res["by"], "")
        data = write_xlsx([(f"销售分析{title}", headers, rows)])
        return Download(f"销售分析_{title}_{today}.xlsx", data)
    if kind not in simple:
        raise KeyError(kind)
    title, fetch, cols = simple[kind]
    rows = fetch()
    data = write_xlsx([(title, [h for h, _ in cols], ([fn(r) for _, fn in cols] for r in rows))])
    return Download(f"{title}_{today}.xlsx", data)
