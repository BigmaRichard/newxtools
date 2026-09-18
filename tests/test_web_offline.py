"""离线测试：本地前台 API（用 Store 生成小型镜像库，直接调用 Query / HTTP 服务）。

运行：python -m pytest tests -q
"""

import json
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sync import SPEC_BY_DT, Store  # noqa: E402
from web.server import Lookups, Mirror, Query, make_server  # noqa: E402

TODAY = __import__("datetime").date.today()
THIS_YEAR = TODAY.year
# 一条 CRM 长记录：subject 是 content 截断到 128 字的前缀，正文分段并提到另一位联系人
LONG = "上门拜访：老客户-终端-研创\n   上门拜访纯化组长张三，询问项目进展，" + "填料参数上维持不变，" * 8 + "\n   拜访付玉清付总，简单聊了两句。"


def seed(store: Store) -> None:
    y = str(THIS_YEAR)
    users = [
        {"id": "1", "user": "boss", "part": "B1", "name": "boss", "status": "0", "type": "0", "isadmin": "1"},
        {"id": "2", "user": "m9", "part": "M9", "name": "王勇尊", "status": "0", "type": "0", "isadmin": "0"},
        {"id": "3", "user": "m23", "part": "M23", "name": "李勇刚(离职)", "status": "1", "type": "0", "isadmin": "0"},
    ]
    customers = [
        {"id": "1", "sn": "1302", "cu_name": "广州研创生物技术发展有限公司", "m_name": "研创", "life": "3", "type": "3", "cu_status": "2", "owner": "M9", "city": "广州市", "state": "6", "district": "", "creatdate": "2013-11-01", "moddate": "2026-01-01",
         "contact": [{"id": "101", "name": "张三", "headship": "采购", "mphone": "13800000001"}, {"id": "102", "name": "付玉清", "headship": "", "mphone": ""}, {"id": "103", "name": "金舫", "headship": "", "mphone": ""}]},
        {"id": "2", "sn": "", "cu_name": "贵州医科大学-药学院-钱星凯", "m_name": "", "life": "2", "type": "2", "cu_status": "1", "owner": "M23", "city": "贵阳市", "state": "29", "district": "", "creatdate": "2025-05-01", "moddate": "2026-09-01", "contact": []},
        {"id": "3", "sn": "", "cu_name": "供应商A（无订单客户）", "m_name": "", "life": "1", "type": "1", "cu_status": "1", "owner": "M9", "city": "", "state": "0", "district": "", "creatdate": "2026-09-01", "moddate": "2026-09-01",
         "contact": [{"id": "301", "name": "供应商联系人", "headship": "", "mphone": "", "phone": "", "weixin": "", "qq": "", "email": ""}]},
    ]
    products = [
        {"id": "1", "sn": "08086-31", "name": "πNAP Packed Column 4.6mmI.D.x250mm", "model": "-", "unit": "支", "price": "3000.0000", "status": "正常", "class": "色谱柱", "lnum": "5.000", "ldown": "20.000", "moddate": "2026-01-01"},
        {"id": "2", "sn": "", "name": "无编号产品（明细里以 [id:2] 引用）", "model": "", "unit": "桶", "price": "0.0000", "status": "正常", "class": "制备色谱填料", "lnum": "0.000", "ldown": "0.000", "moddate": "2026-01-01"},
        {"id": "3", "sn": "SLOW-1", "name": "滞销品", "model": "", "unit": "支", "price": "100.0000", "status": "正常", "class": "色谱柱", "lnum": "9.000", "ldown": "0.000", "moddate": "2026-01-01"},
    ]
    # 产品类别树（csstree）：根 → 大类 → 分类；产品表 class 存的是分类标题
    csstree = [{"id": "1", "tid": "1", "title": "产品类别", "upid": "0", "status": "1"}, {"id": "2", "tid": "1", "title": "1.色谱柱", "upid": "1", "status": "1"},
               {"id": "3", "tid": "1", "title": "2.色谱介质", "upid": "1", "status": "1"}, {"id": "7", "tid": "1", "title": "色谱柱", "upid": "2", "status": "1"},
               {"id": "11", "tid": "1", "title": "制备色谱填料", "upid": "3", "status": "1"}]
    purchases = [
        {"id": "1", "No.": f"CGMW{y}0901001", "title": "供应商A：填料", "cu_sn": "[id:0]", "cu_id": "3", "type": "1", "status0": "1", "status": "3", "money": "1000000.00", "amount_before_tax": "884955.75", "backsum": "0.00",
         "who": "肖婷姣", "date": f"{y}-09-01", "money_type": "JPY", "money_rate": "5.0", "confirm": "2", "lib": "7", "memo": "",
         "puritem": [{"id": "1", "prod": "[id:2]", "prod_name": "无编号产品", "num": "10.000", "price": "100000.0000", "money": "1000000.00", "backnum": "10.000", "tax_rate": "0"}]},
        {"id": "2", "No.": f"CGMW{y}0902002", "title": "供应商A：色谱柱", "cu_sn": "[id:0]", "cu_id": "3", "type": "2", "status0": "1", "status": "0", "money": "1600.00", "amount_before_tax": "1415.93", "backsum": "1600.00",
         "who": "鲍晓星", "date": f"{y}-09-02", "money_type": "RMB", "money_rate": "100", "confirm": "2", "lib": "7", "memo": "",
         "puritem": [{"id": "2", "prod": "08086-31", "prod_name": "πNAP", "num": "1.000", "price": "1600.0000", "money": "1600.00", "backnum": "0.000", "tax_rate": "13.00"}]},
    ]
    pay_plans = [
        {"id": "1", "date": f"{y}-10-01", "serial": "1", "money_type": "JPY", "money_rate": "5.0", "money": "1000000.00", "who": "黄晓霞", "status": "0", "pu_id": "1", "cu_sn": "[id:3]", "ctype": "0", "type": "5", "owner": "黄晓霞", "memo": ""},
        {"id": "2", "date": f"{THIS_YEAR - 1}-12-01", "serial": "1", "money_type": "RMB", "money_rate": "100", "money": "1600.00", "who": "鲍晓星", "status": "1", "pu_id": "2", "cu_sn": "[id:3]", "ctype": "0", "type": "5", "owner": "鲍晓星", "memo": ""},
        {"id": "3", "date": f"{THIS_YEAR - 1}-01-01", "serial": "1", "money_type": "RMB", "money_rate": "100", "money": "500.00", "who": "鲍晓星", "status": "0", "pu_id": "2", "cu_sn": "[id:3]", "ctype": "0", "type": "5", "owner": "鲍晓星", "memo": "逾期未付"},
    ]
    contracts = [
        {"id": "10", "No.": f"mw{y}0101010", "subject": "旧单（用 sn 关联客户）", "cu_sn": "1302", "type": "1", "status": "2", "confirm": "2", "st_send": "4", "sum": "1000.00", "who": "王勇尊",
         "date": f"{THIS_YEAR - 1}-06-01", "end_date": f"{THIS_YEAR - 1}-06-01", "money_type": "RMB", "goods": [{"id": "1", "prod": "08086-31", "prod_name": "πNAP", "amount": "1.000", "un_price": "1000", "sum": "1000.00"}]},
        {"id": "11", "No.": f"mw{y}0301011", "subject": "今年订单一", "cu_sn": "[id:1]", "type": "1", "status": "2", "confirm": "2", "st_send": "4", "sum": "2000.00", "who": "王勇尊",
         "date": f"{y}-03-01", "end_date": f"{y}-03-01", "money_type": "RMB", "j1": "含税", "j7": "5", "j8": "2", "j28": "a@b.com", "goods": [{"id": "2", "prod": "08086-31", "prod_name": "πNAP", "amount": "2.000", "un_price": "1000", "sum": "2000.00"}]},
        {"id": "12", "No.": f"mw{y}0901012", "subject": "执行中订单", "cu_sn": "[id:2]", "type": "2", "status": "1", "confirm": "2", "st_send": "1", "sum": "500.00", "who": "李勇刚(离职)",
         "date": TODAY.isoformat(), "end_date": TODAY.isoformat(), "money_type": "RMB", "j7": "10", "goods": [{"id": "3", "prod": "[id:2]", "prod_name": "无编号产品", "amount": "1.000", "un_price": "500", "sum": "500.00"}]},
        {"id": "13", "No.": f"mw{y}0501013", "subject": "意外中止", "cu_sn": "[id:2]", "type": "1", "status": "3", "confirm": "2", "st_send": "0", "sum": "9999.00", "who": "王勇尊",
         "date": f"{y}-05-01", "end_date": f"{y}-05-01", "money_type": "RMB", "goods": []},
    ]
    notes = [
        {"id": "1", "cu_sn": "[id:1]", "co_id": "11", "date": f"{y}-03-20", "invoice": "1", "serial": "1", "money": "1500.00", "type": "5", "ctype": "4", "owner": "王勇尊", "who": "王勇尊", "money_type": "RMB", "memo": "首付"},
        {"id": "2", "cu_sn": "1302", "co_id": "10", "date": f"{THIS_YEAR - 1}-07-01", "invoice": "2", "serial": "1", "money": "1000.00", "type": "4", "ctype": "2", "owner": "王勇尊", "who": "王勇尊", "money_type": "RMB", "memo": ""},
    ]
    plans = [
        {"id": "1", "date": f"{y}-04-01", "serial": "1", "money": "2000.00", "status": "4", "who": "M9", "cu_sn": "[id:1]", "co_sn": f"mw{y}0301011", "memo": "月结"},
        {"id": "2", "date": (TODAY.replace(day=1) + __import__("datetime").timedelta(days=40)).isoformat(), "serial": "1", "money": "500.00", "status": "2", "who": "M23", "cu_sn": "[id:2]", "co_sn": f"mw{y}0901012", "memo": ""},
        {"id": "3", "date": f"{THIS_YEAR - 1}-07-01", "serial": "1", "money": "1000.00", "status": "1", "who": "M9", "cu_sn": "1302", "co_sn": f"mw{y}0101010", "memo": ""},
    ]
    sends = [{"id": "1", "co_id": "11", "cu_sn": "[id:1]", "date": f"{y}-03-02", "status": "1", "who": "王勇尊", "sn": "mw,20260302,000001", "sendcomp": "顺丰", "sendcode": "SF1", "name": "张三", "addr": "广州", "deli_note": [{"id": "1", "pid": "08086-31", "num": "2.000"}]}]
    libouts = [{"id": "1", "title": "出库", "lib": "1", "libname": "1号仓库", "cu_sn": "1", "co_sn": f"mw{y}0301011", "date": f"{y}-03-02", "who": "M9", "memo": "", "libitem": [{"id": "1", "prod": "08086-31", "num": "2.000"}]}]
    actions = [
        {"id": "1", "cale": "3", "subject": "上门拜访", "content": "上门拜访", "type": "2", "cu_sn": "[id:1]", "con_id": "101", "who": ",M9,", "date": TODAY.isoformat(), "endate": TODAY.isoformat(), "co_id": "11"},
        {"id": "2", "cale": "3", "subject": "电话", "content": "电话沟通详情", "type": "1", "cu_sn": "[id:2]", "con_id": "", "who": "M23,", "date": TODAY.isoformat(), "endate": TODAY.isoformat()},
        {"id": "3", "cale": "3", "subject": "很久以前", "content": "", "type": "1", "cu_sn": "[id:1]", "con_id": "", "who": ",M9,M23,", "date": "2020-01-01", "endate": "2020-01-01"},
        {"id": "4", "cale": "3", "subject": "日期录错", "content": "", "type": "1", "cu_sn": "[id:1]", "con_id": "", "who": ",M9,", "date": "2224-06-12", "endate": "2224-06-12"},
        {"id": "5", "cale": "4", "subject": "没有日期的待办", "content": "", "type": "", "cu_sn": "[id:1]", "con_id": "", "who": ",M9,", "date": "", "endate": ""},
        {"id": "6", "cale": "3", "subject": LONG[:128], "content": LONG, "type": "2", "cu_sn": "[id:1]", "con_id": "101", "who": ",M9,", "date": "2020-06-01", "endate": "2020-06-01"},
    ]
    for dt_name, rows in [("user", users), ("csstree", csstree), ("customer", customers), ("product", products), ("contract", contracts), ("gathering_note", notes), ("gathering", plans),
                          ("sendgoods", sends), ("libout", libouts), ("action", actions), ("purchase", purchases), ("pay_plan", pay_plans)]:
        store.upsert_raw(dt_name, rows)
        store.upsert_normalized(SPEC_BY_DT[dt_name], rows)
        store.set_state(dt_name, lastid=len(rows), last_full_at="2026-09-18 05:36:00", last_run_at="2026-09-18 05:36:34", last_status="ok", last_rows=len(rows))
    store.save_dictionary("user", "pr2nm", [{"key": u["part"], "value": u["name"], "flag": "USE"} for u in users])
    store.save_dictionary("contract", "status", [{"key": "1", "value": "执行中", "flag": "Default"}, {"key": "2", "value": "结束", "flag": "USE"}, {"key": "3", "value": "意外中止", "flag": "USE"}])
    store.save_dictionary("gathering", "status", [{"key": "1", "value": "已回", "flag": "USE"}, {"key": "2", "value": "未回", "flag": "Default"}, {"key": "4", "value": "部分回款", "flag": "USE"}])
    store.save_dictionary("action", "type", [{"key": "1", "value": "电话", "flag": "USE"}, {"key": "2", "value": "市内拜访", "flag": "USE"}])
    store.save_dictionary("customer", "life", [{"key": "1", "value": "潜在", "flag": "Default"}, {"key": "2", "value": "签约", "flag": "USE"}, {"key": "3", "value": "重复购买", "flag": "USE"}])
    store.save_dictionary("contract", "j7", [{"key": "5", "value": "增值税专用发票", "flag": "USE"}, {"key": "10", "value": "增值税普通发票", "flag": "USE"}])
    store.save_dictionary("contract", "j8", [{"key": "1", "value": "款到发货", "flag": "USE"}, {"key": "2", "value": "月结", "flag": "USE"}])
    store.save_dictionary("purchase", "type", [{"key": "1", "value": "大宗采购", "flag": "USE"}, {"key": "2", "value": "零星采购", "flag": "USE"}])
    store.save_field_names("contract", {"j1": "含税方式", "j7": "一、发票类型", "j8": "二、付款方式", "j28": "收电子发票邮箱"})


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "mirror.sqlite"
    store = Store(path)
    seed(store)
    store.close()
    return path


@pytest.fixture
def q(db):
    mirror = Mirror(db)
    conn = mirror.connect()
    lk = mirror.lookups(conn)

    def make(**params):
        return Query(conn, lk, {k: str(v) for k, v in params.items()})

    return make


def test_lookups_resolve_customer_keys_and_people(q):
    lk = q().lk
    assert lk.customer_id("[id:2]") == 2
    assert lk.customer_id("1302") == 1  # 客户编号
    assert lk.customer_id("1", numeric_is_id=True) == 1  # 出库单形式
    assert lk.customer_id("不存在") is None
    assert lk.customer("[id:1]")["name"] == "广州研创生物技术发展有限公司"
    assert lk.customer("[id:1]")["owner"] == "王勇尊"
    assert lk.names_from_codes(",M9,M23,") == ["王勇尊", "李勇刚(离职)"]
    assert lk.names_from_codes("M23,") == ["李勇刚(离职)"]
    assert lk.user_name("M9") == "王勇尊" and lk.user_name("X1") == "X1"
    assert lk.text("contract", "status", "1") == "执行中"


def test_meta_lists_users_dicts_and_years(q):
    m = q().meta()
    assert m["synced_at"] == "2026-09-18 05:36:34"
    assert [u["part"] for u in m["users"]][:2] == ["B1", "M9"]  # 在职优先
    assert m["dicts"]["contract.status"][0]["value"] == "执行中"
    assert THIS_YEAR in m["years"] and THIS_YEAR - 1 in m["years"]


def test_overview_kpis_exclude_cancelled_orders(q):
    d = q(year=THIS_YEAR).overview()
    assert d["year_total"] == {"count": 2, "amount": 2500.0}  # 2000 + 500，剔除意外中止 9999
    assert d["kpi"]["ytd_receipts"]["amount"] == 1500.0
    assert d["kpi"]["open_orders"] == {"count": 1, "amount": 500.0}
    assert d["kpi"]["open_plans"] == {"count": 2, "amount": 2500.0}
    assert d["kpi"]["overdue_plans"] == {"count": 1, "amount": 2000.0}
    march = next(m for m in d["monthly"] if m["month"] == f"{THIS_YEAR}-03")
    assert march["orders"]["amount"] == 2000.0 and march["receipts"]["amount"] == 1500.0
    assert len(d["monthly"]) == 24
    assert d["top_customers"][0]["customer"]["id"] == 1 and d["top_customers"][0]["amount"] == 2000.0
    assert d["top_sales"][0]["name"] == "王勇尊"
    assert d["top_products"][0]["name"].startswith("πNAP Packed") and d["top_products"][0]["batches"] == 1   # Top 榜按型号合并批号
    assert {s["status"]: s["count"] for s in d["status_mix"]} == {"1": 1, "2": 1, "3": 1}


def test_orders_search_filters_and_received(q):
    all_orders = q().orders()
    assert all_orders["total"] == 4 and all_orders["amount"] == 3500.0
    row = next(r for r in all_orders["rows"] if r["id"] == 11)
    assert row["customer"]["name"] == "广州研创生物技术发展有限公司" and row["received"] == 1500.0 and row["shipments"] == 1
    assert row["status_text"] == "结束"
    # 按客户名称搜索：命中 [id:1] 与 sn=1302 两种关联
    by_name = q(q="研创").orders()
    assert sorted(r["id"] for r in by_name["rows"]) == [10, 11]
    # 按人员（part → 姓名）
    assert [r["id"] for r in q(who="M23").orders()["rows"]] == [12]
    assert q(status="1").orders()["total"] == 1
    assert q(**{"from": f"{THIS_YEAR}-01-01", "to": f"{THIS_YEAR}-12-31"}).orders()["total"] == 3
    assert q(customer_id=1).orders()["total"] == 2
    assert q(page=2, size=3).orders()["rows"][0]["id"] == 10


def test_order_detail_joins_children(q):
    d = q().order_detail(11)
    assert d["order"]["no"] == f"mw{THIS_YEAR}0301011"
    assert d["goods"][0]["name"].startswith("πNAP") and d["goods"][0]["unit"] == "支"
    assert [r["amount"] for r in d["receipts"]] == [1500.0]
    assert d["plans"][0]["status_text"] == "部分回款" and d["plans"][0]["overdue_days"] > 0
    assert d["shipments"][0]["items"] == 1 and d["libouts"][0]["who"] == "王勇尊"
    assert d["actions"][0]["content"] == "上门拜访"
    terms = {x["key"]: x for x in d["terms"]}  # 0.5 起自定义字段 j* 单列为“合同条款”，其余原始字段仍在 extras
    assert terms["j1"]["name"] == "含税方式" and terms["j1"]["value"] == "含税" and terms["j1"]["decoded"] is False
    assert all(x["key"] not in ("No.", "j1") for x in d["extras"])
    assert q().order_detail(999) is None


def test_customers_list_aggregates_both_key_forms(q):
    res = q(sort="amount").customers()
    assert res["total"] == 3
    top = res["rows"][0]
    assert top["id"] == 1 and top["orders"] == 2 and top["order_amount"] == 3000.0 and top["receipts"] == 2500.0 and top["contacts"] == 3
    assert top["last_order"] == f"{THIS_YEAR}-03-01"
    assert q(q="医科").customers()["rows"][0]["id"] == 2
    assert q(owner="M23").customers()["total"] == 1
    assert q(life="1").customers()["rows"][0]["name"] == "供应商A（无订单客户）"
    d = q().customer_detail(1)
    assert d["customer"]["owner"] == "王勇尊" and len(d["contacts"]) == 3
    assert sorted(o["id"] for o in d["orders"]) == [10, 11]
    assert [p["amount"] for p in d["open_plans"]] == [2000.0]
    assert [y["year"] for y in d["yearly"]] == [str(THIS_YEAR - 1), str(THIS_YEAR)]
    assert q().customer_detail(999) is None


def test_receivables_status_and_aging(q):
    opened = q().receivables()
    assert opened["total"] == 2 and opened["amount"] == 2500.0
    assert opened["aging"]["not_due"] == 500.0 and opened["aging"]["d30"] + opened["aging"]["d90"] + opened["aging"]["d365"] == 2000.0
    assert {w["part"]: w["overdue"] for w in opened["by_who"]} == {"M9": 2000.0, "M23": 0.0}
    overdue = q(status="overdue").receivables()
    assert overdue["total"] == 1 and overdue["rows"][0]["order_id"] == 11 and overdue["rows"][0]["who"] == "王勇尊"
    assert q(status="done").receivables()["total"] == 1
    assert q(status="all", q="研创").receivables()["total"] == 2


def test_receipts_filters_and_summary(q):
    res = q(**{"from": f"{THIS_YEAR}-01-01"}).receipts()
    assert res["total"] == 1 and res["amount"] == 1500.0
    assert res["rows"][0]["order_no"] == f"mw{THIS_YEAR}0301011" and res["rows"][0]["customer"]["id"] == 1
    assert res["by_month"] == [{"month": f"{THIS_YEAR}-03", "count": 1, "amount": 1500.0}]
    assert q(who="M9").receipts()["total"] == 2
    assert q(q="首付").receipts()["total"] == 1


def test_actions_who_codes_and_summaries(q):
    res = q(**{"from": TODAY.isoformat()}).actions()
    assert res["total"] == 3  # 含一条日期录成 2224 年的记录
    assert {r["id"]: r["who"] for r in res["rows"]} == {1: ["王勇尊"], 2: ["李勇刚(离职)"], 4: ["王勇尊"]}
    row = next(r for r in res["rows"] if r["id"] == 1)
    assert row["contact"] == "张三" and row["subject"] == "" and row["content"] == "上门拜访" and row["order_id"] == 11 and row["type_text"] == "市内拜访" and row["date_flag"] == ""
    assert next(r for r in res["rows"] if r["id"] == 4)["date_flag"] == "future"
    assert [d["date"] for d in res["by_day"]] == [TODAY.isoformat()]  # 未来日期不进按日统计
    assert q(who="M23").actions()["total"] == 2  # 单独与多人记录都命中
    everything = q().actions()
    assert {w["part"]: w["count"] for w in everything["by_who"]} == {"M9": 5, "M23": 2}
    assert next(w for w in everything["by_who"] if w["part"] == "M9")["chars"] > len(LONG)
    assert next(r for r in everything["rows"] if r["id"] == 5)["date_flag"] == "invalid"
    assert q(q="沟通").actions()["rows"][0]["content"] == "电话沟通详情"


def test_http_server_serves_page_and_api(db):
    server = make_server(db, "127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{port}"
        html = urllib.request.urlopen(base + "/").read().decode("utf-8")
        assert "<title>Microwants · XTools 数据前台</title>" in html
        meta = json.loads(urllib.request.urlopen(base + "/api/meta").read())
        assert meta["synced_at"]
        url = base + "/api/orders?" + urllib.parse.urlencode({"q": "研创"})
        assert json.loads(urllib.request.urlopen(url).read())["total"] == 2
        with pytest.raises(urllib.error.HTTPError) as info:
            urllib.request.urlopen(base + "/api/orders/999")
        assert info.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as info:
            urllib.request.urlopen(base + "/static/../server.py")
        assert info.value.code == 404
    finally:
        server.shutdown()
        server.server_close()


def test_connection_is_read_only(db):
    conn = Mirror(db).connect()
    with pytest.raises(Exception):
        conn.execute("DELETE FROM contract")
    conn.close()


def test_action_long_record_dedupes_subject_and_marks_mentions(q):
    res = q(**{"from": "2020-06-01", "to": "2020-06-30"}).actions()
    assert res["total"] == 1
    row = res["rows"][0]
    assert row["subject"] == "" and row["content"] == LONG and row["chars"] == len(LONG)  # subject 只是正文前缀，不重复显示
    assert row["contact"] == "张三" and row["mentions"] == ["付玉清"]  # 主联系人之外、正文里提到的建档联系人
    # 客户详情里的行动记录同样带“提及”
    detail = q().customer_detail(1)
    assert next(a for a in detail["actions"] if a["id"] == 6)["mentions"] == ["付玉清"]
    # subject 是正文开头时只显示正文；subject 与正文各不相同时两者都保留
    row2 = next(r for r in q(**{"from": TODAY.isoformat()}).actions()["rows"] if r["id"] == 2)
    assert row2["subject"] == "" and row2["content"] == "电话沟通详情"
    made = q().action_row({"id": 9, "subject": "回访", "content": "客户反馈良好", "who": ",M9,", "cu_sn": "[id:1]"})
    assert made["subject"] == "回访" and made["content"] == "客户反馈良好"


# ---------------------------------------------------------------------- 0.5：分析页与导出
def test_meta_includes_product_tree_states_and_order_terms(q):
    meta = q().meta()
    assert meta["product_groups"] == ["1.色谱柱", "2.色谱介质"]
    assert {c["title"]: c["group"] for c in meta["product_classes"]} == {"色谱柱": "1.色谱柱", "制备色谱填料": "2.色谱介质"}
    states = {s["key"]: s["name"] for s in meta["states"]}
    assert states["6"] == "广东" and states["29"] == "贵州" and states["0"] == "（未填地区）"  # 字典未抓取时按城市推断省份
    terms = {t["key"]: t for t in meta["order_terms"]}
    assert terms["j7"]["has_dict"] is True and terms["j7"]["name"] == "一、发票类型" and terms["j9"]["has_dict"] is False
    assert meta["salespeople"][0]["part"] == "M9"


def test_sales_by_dimension_and_years(q):
    res = q(by="who", years=f"{THIS_YEAR},{THIS_YEAR - 1}").sales()
    assert res["years"] == [THIS_YEAR, THIS_YEAR - 1] and res["line_mode"] is False
    rows = {r["key"]: r for r in res["rows"]}
    assert rows["王勇尊"]["cells"][str(THIS_YEAR)]["amount"] == 2000.0 and rows["王勇尊"]["cells"][str(THIS_YEAR - 1)]["amount"] == 1000.0  # 意外中止的 9999 不计
    assert rows["王勇尊"]["yoy"] == 100.0
    assert res["totals"][str(THIS_YEAR)] == {"count": 2, "amount": 2500.0, "qty": 0.0}
    assert len(res["monthly"]) == 12 and res["monthly"][2]["cells"][str(THIS_YEAR)]["amount"] == 2000.0  # 3 月
    # 客户维度把 "[id:1]" 与编号 "1302" 两种写法归并为同一客户
    cust = {r["key"]: r for r in q(by="customer", years=f"{THIS_YEAR},{THIS_YEAR - 1}").sales()["rows"]}
    assert cust[1]["total"] == 3000.0 and cust[1]["count"] == 2 and cust[1]["name"].startswith("广州研创")
    # 地区 / 类型 / 月份
    region = {r["key"]: r for r in q(by="region").sales()["rows"]}
    assert region["6"]["name"] == "广东" and region["29"]["total"] == 500.0
    assert q(by="type").sales()["rows"][0]["key"] in ("1", "2")
    month = q(by="month").sales()
    assert [r["key"] for r in month["rows"]][:1] == ["03"] or month["rows"][0]["key"] <= "09"
    assert q(by="who", ytd="1").sales()["ytd"] is True


def test_sales_line_mode_products_classes_groups_and_filters(q):
    prod = q(by="product").sales()
    assert prod["line_mode"] is True
    rows = {r["name"]: r for r in prod["rows"]}
    pi = rows["πNAP Packed Column 4.6mmI.D.x250mm"]                     # 产品维度 = 型号，key 即型号名
    assert pi["key"] == pi["model_name"] == "πNAP Packed Column 4.6mmI.D.x250mm" and pi["total"] == 3000.0 and pi["sub"].startswith("色谱柱")
    assert rows["无编号产品（明细里以 [id:2] 引用）"]["cells"][str(THIS_YEAR)]["qty"] == 1.0  # "[id:N]" 引用按 id 关联
    cls = {r["key"]: r for r in q(by="class").sales()["rows"]}
    assert cls["色谱柱"]["sub"] == "1.色谱柱" and cls["制备色谱填料"]["total"] == 500.0
    grp = {r["key"]: r for r in q(by="group").sales()["rows"]}
    assert set(grp) == {"1.色谱柱", "2.色谱介质"}
    # 产品条件下钻到业务员：只剩买过 πNAP 的王勇尊；分类 / 大类条件同理
    who = q(by="who", prod="08086-31").sales()
    assert who["line_mode"] is True and [r["key"] for r in who["rows"]] == ["王勇尊"] and who["filters"]["prod"].startswith("πNAP")
    assert [r["key"] for r in q(by="who", group="2.色谱介质").sales()["rows"]] == ["李勇刚(离职)"]
    assert [r["key"] for r in q(by="product", who="M9").sales()["rows"]] == ["πNAP Packed Column 4.6mmI.D.x250mm"]
    assert q(by="product", state="29").sales()["rows"][0]["key"] == "无编号产品（明细里以 [id:2] 引用）"
    # prod 条件：产品编号按单个批号；型号名按该型号的全部批号
    by_model = q(by="who", prod="πNAP Packed Column 4.6mmI.D.x250mm").sales()
    assert [r["key"] for r in by_model["rows"]] == ["王勇尊"] and by_model["filters"]["prod"].startswith("πNAP")


def test_customer_analysis_tiers_new_retention_churn(q):
    d = q().customer_analysis()
    k = d["kpi"]
    assert k["active"] == 2 and k["prev_active"] == 1 and k["amount"] == 2500.0 and k["prev_amount"] == 1000.0
    assert k["new"] == 1 and k["retained"] == 1 and k["retention_rate"] == 100.0 and k["repeat"] == 0
    tiers = {t["tier"]: t for t in d["tiers"]}
    assert tiers["A"]["count"] == 1 and tiers["A"]["amount"] == 2000.0 and tiers["B"]["count"] + tiers["C"]["count"] == 1
    assert d["tier_rows"][0]["tier"] == "A" and d["tier_rows"][0]["id"] == 1 and d["tier_rows"][0]["prev_amount"] == 1000.0
    assert d["new_rows"][0]["id"] == 2 and d["new_rows"][0]["first_date"] == TODAY.isoformat()
    assert sum(m["count"] for m in d["new_by_month"]) == 1
    idle = (TODAY - TODAY.replace(month=3, day=1)).days  # 研创最近一单在今年 3 月 1 日
    expect_bucket = "6-12" if 182 <= idle < 365 else None
    buckets = {b["key"]: b["count"] for b in d["churn"]["buckets"]}
    assert sum(buckets.values()) == (1 if expect_bucket else 0) and (not expect_bucket or buckets[expect_bucket] == 1)
    if expect_bucket:
        assert d["churn"]["rows"][0]["id"] == 1 and d["churn"]["rows"][0]["idle_days"] == idle and d["churn"]["rows"][0]["amount"] == 3000.0
    owners = {o["part"]: o for o in d["by_owner"]}
    assert owners["M9"]["customers"] == 2 and owners["M9"]["active"] == 1 and owners["M23"]["new"] == 1
    assert q(owner="M23").customer_analysis()["kpi"]["active"] == 1
    assert q(year=str(THIS_YEAR - 1)).customer_analysis()["kpi"]["active"] == 1


def test_salesperson_dashboard(q):
    d = q(who="M9").salesperson()
    assert d["user"]["name"] == "王勇尊" and d["year"] == THIS_YEAR
    k = d["kpi"]
    assert k["orders"]["amount"] == 2000.0 and k["orders_prev"]["amount"] == 1000.0 and k["receipts"]["amount"] == 1500.0
    assert k["open_plans"]["count"] == 1 and k["overdue_plans"]["count"] == 1 and k["customers_owned"] == 2 and k["customers_active"] == 1
    assert k["actions"] >= 1 and k["last_action"] == TODAY.isoformat()  # 2224 年的异常日期不算“最近”
    assert d["rank"] == 1 and d["rank_of"] == 2
    assert d["monthly"][2]["orders"]["amount"] == 2000.0 and d["top_customers"][0]["customer"]["id"] == 1 and d["top_products"][0]["model_name"].startswith("πNAP")
    assert len(d["open_plans"]) == 1 and d["recent_orders"][0]["no"].endswith("013")  # 最近订单含意外中止的单
    assert q(who="王勇尊").salesperson()["user"]["part"] == "M9"  # 按姓名也能找到
    assert q().salesperson() is None


def test_products_list_summary_and_detail(q):
    res = q(months="0").products()
    assert res["total"] == 3 and res["window"] == "全部"
    rows = {r["sn"]: r for r in res["rows"]}
    assert rows["08086-31"]["sales_amount"] == 3000.0 and rows["08086-31"]["sales_qty"] == 3.0 and rows["08086-31"]["stock_low"] is True and rows["08086-31"]["group"] == "1.色谱柱"
    assert rows[""]["id"] == 2 and rows[""]["sales_amount"] == 500.0  # 无编号产品按 [id:2] 关联到销售
    assert res["summary"]["low"] == 1 and res["summary"]["unsold"] == 1 and res["summary"]["sold"] == 2
    assert [g["group"] for g in res["by_group"]][0] == "1.色谱柱"
    assert q(months="0", stock="unsold").products()["rows"][0]["sn"] == "SLOW-1"
    assert q(months="0", group="2.色谱介质").products()["total"] == 1
    assert q(months="0", q="πNAP").products()["total"] == 1
    d = q(id="2", months="0").product_detail()
    assert d["product"]["name"].startswith("无编号") and d["yearly"][0]["amount"] == 500.0 and d["lines"][0]["order_no"].endswith("012")
    assert d["purchases"][0]["no"].endswith("001") and d["purchases"][0]["money_type"] == "JPY"
    d2 = q(sn="08086-31", months="0").product_detail()
    assert d2["top_customers"][0]["customer"]["id"] == 1 and len(d2["monthly"]) == 24 and d2["libouts"][0]["qty"] == 2.0
    assert q(sn="nope").product_detail() is None


def test_purchases_pay_plans_and_currency_conversion(q):
    res = q().purchases()
    assert res["total"] == 2 and res["rmb"] == 51600.0  # 1,000,000 JPY × 5.0 / 100 + 1,600 RMB
    row = {r["no"][-3:]: r for r in res["rows"]}
    assert row["001"]["supplier"]["id"] == 3 and row["001"]["rmb"] == 50000.0 and row["001"]["status_text"] == "全部入库" and row["001"]["type_text"] == "大宗采购"
    assert row["002"]["status_text"] == "待入库" and row["002"]["paid"] == 1600.0
    assert {c["money_type"]: c["rmb"] for c in res["by_currency"]} == {"JPY": 50000.0, "RMB": 1600.0}
    assert res["by_supplier"][0]["supplier"]["id"] == 3 and res["by_supplier"][0]["count"] == 2
    assert q(supplier_id="3", money_type="RMB").purchases()["total"] == 1 and q(q="供应商A").purchases()["total"] == 2
    d = q().purchase_detail(1)
    assert d["items"][0]["product_id"] == 2 and d["items"][0]["qty"] == 10.0 and d["plans"][0]["rmb"] == 50000.0 and d["plans"][0]["status_text"] == "未付"
    assert q().purchase_detail(99) is None
    plans = q().pay_plans()  # 缺省只看未付
    assert plans["total"] == 2 and plans["overdue"]["count"] == 1 and plans["overdue"]["rmb"] == 500.0
    overdue = q(status="overdue").pay_plans()["rows"]
    assert len(overdue) == 1 and overdue[0]["overdue_days"] > 0 and overdue[0]["purchase_no"].endswith("002")
    assert q(status="done").pay_plans()["total"] == 1 and q(status="all").pay_plans()["total"] == 3


def test_cashflow_monthly_series(q):
    d = q(months="24").cashflow()
    assert len(d["rows"]) == 24 and d["rows"][-1]["month"] == TODAY.strftime("%Y-%m")
    this_month = d["rows"][-1]
    assert this_month["purchases"] == 51600.0 and this_month["sales"] == 500.0 and this_month["orders"] == 1
    assert d["open_payments"]["count"] == 2 and d["open_receivables"]["count"] == 2
    assert d["totals"]["receipts"] >= 1500.0 and d["upcoming"][0]["rmb"] == 50000.0


def test_contacts_search_missing_and_last_contact(q):
    res = q().contacts()
    assert res["total"] == 4 and res["missing"] == 3 and res["never_contacted"] == 3
    rows = {k["name"]: k for k in res["rows"]}
    assert rows["张三"]["missing"] is False and rows["张三"]["last_contact"] == TODAY.isoformat() and rows["张三"]["actions"] == 2
    assert rows["付玉清"]["missing"] is True and rows["付玉清"]["customer"]["owner"] == "王勇尊"
    assert q(missing="1").contacts()["total"] == 3 and q(q="138").contacts()["rows"][0]["name"] == "张三"
    assert q(owner="M9", missing="1").contacts()["by_owner"][0]["missing"] == 3
    assert q(sort="last").contacts()["rows"][0]["name"] == "张三"


def test_order_custom_fields_decoded_and_filterable(q):
    rows = {o["id"]: o for o in q().orders()["rows"]}
    assert rows[11]["invoice_type"] == "增值税专用发票" and rows[11]["pay_terms"] == "月结" and rows[11]["lead_time"] == ""  # j9 没有字典 → 不显示代码
    assert rows[12]["invoice_type"] == "增值税普通发票"
    assert [o["id"] for o in q(j7="5").orders()["rows"]] == [11]
    assert [o["id"] for o in q(prod="08086-31").orders()["rows"]] == [11, 10]
    assert [o["id"] for o in q(**{"class": "制备色谱填料"}).orders()["rows"]] == [12]
    assert [o["id"] for o in q(group="1.色谱柱", month=f"{THIS_YEAR}-03").orders()["rows"]] == [11]
    assert [o["id"] for o in q(state="29").orders()["rows"]] == [12, 13]
    terms = {t["key"]: t for t in q().order_detail(11)["terms"]}
    assert terms["j7"] == {"key": "j7", "name": "一、发票类型", "value": "增值税专用发票", "raw": "5", "decoded": True}
    assert terms["j28"]["value"] == "a@b.com" and terms["j28"]["decoded"] is False
    assert [t["key"] for t in q().order_detail(11)["terms"]] == ["j7", "j8", "j1", "j28"]  # 有字典的在前
    assert q().order_detail(11)["goods"][0]["product_id"] == 1


def test_export_xlsx_over_http(db):
    import io
    import zipfile

    server = make_server(db, "127.0.0.1", 0)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{port}"
        resp = urllib.request.urlopen(base + "/api/export/orders?" + urllib.parse.urlencode({"who": "M9"}))
        assert resp.headers["Content-Type"].startswith("application/vnd.openxmlformats") and "filename*=UTF-8''" in resp.headers["Content-Disposition"]
        z = zipfile.ZipFile(io.BytesIO(resp.read()))
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "<t>日期</t>" in sheet and "<t>发票类型</t>" in sheet and "增值税专用发票" in sheet and "意外中止" in sheet
        assert sheet.count("<row ") == 1 + 3  # 表头 + 王勇尊的 3 单
        for kind in ("customers", "receivables", "receipts", "actions", "products", "purchases", "pay_plans", "contacts", "tiers", "new_customers", "churn", "lost"):
            data = urllib.request.urlopen(f"{base}/api/export/{kind}").read()
            assert zipfile.ZipFile(io.BytesIO(data)).testzip() is None, kind
        sales = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(base + "/api/export/sales?by=product").read())).read("xl/worksheets/sheet1.xml").decode()
        assert f"<t>{THIS_YEAR} 数量</t>" in sales and "πNAP" in sales
        with pytest.raises(urllib.error.HTTPError) as info:
            urllib.request.urlopen(base + "/api/export/nope")
        assert info.value.code == 404
        # 导出不受列表分页 500 行上限约束（page/size 被忽略）
        big = urllib.request.urlopen(base + "/api/export/actions?size=1&page=2").read()
        assert zipfile.ZipFile(io.BytesIO(big)).read("xl/worksheets/sheet1.xml").decode().count("<row ") == 1 + 6
    finally:
        server.shutdown()
        server.server_close()


def test_products_group_by_model_and_sorting(q):
    """型号视图：同一产品名下的批号合并成一行，库存与销量合计；列表可按各数值列排序。"""
    by_model = q(view="model", months="0").products()
    assert by_model["view"] == "model" and by_model["total"] == 3      # 三个型号，其中 πNAP 只有一个批号
    rows = {r["model_name"]: r for r in by_model["rows"]}
    p1 = rows["πNAP Packed Column 4.6mmI.D.x250mm"]
    assert p1["batches"] == 1 and p1["stock"] == 5.0 and p1["sales_amount"] == 3000.0 and p1["stock_low"] is True
    assert rows["滞销品"]["stock"] == 9.0 and rows["滞销品"]["sales_amount"] == 0.0
    # 排序：库存升序 / 降序
    asc = [r["model_name"] for r in q(view="model", months="0", sort="stock", dir="asc").products()["rows"]]
    desc = [r["model_name"] for r in q(view="model", months="0", sort="stock", dir="desc").products()["rows"]]
    assert asc == desc[::-1] and desc[0] == "滞销品"                    # 库存 9 > 5 > 0
    assert [r["sn"] for r in q(months="0", sort="stock", dir="desc").products()["rows"]][:2] == ["SLOW-1", "08086-31"]
    assert [r["sn"] for r in q(months="0", sort="customers", dir="desc").products()["rows"]][0] == "08086-31"
    assert [r["sn"] for r in q(months="0", sort="sn", dir="asc").products()["rows"]][0] == ""      # 无编号排最前
    # 型号视图下的库存筛选按合计判断
    assert q(view="model", months="0", stock="in").products()["total"] == 2
    assert q(view="model", months="0", stock="unsold").products()["rows"][0]["model_name"] == "滞销品"
    # 型号详情：批号清单 + 合计
    d = q(model="πNAP Packed Column 4.6mmI.D.x250mm", months="0").product_detail()
    assert d["view"] == "model" and d["product"]["batches"] == 1 and d["product"]["stock"] == 5.0
    assert [b["sn"] for b in d["batches"]] == ["08086-31"] and d["batches"][0]["sales_orders"] == 2
    assert d["yearly"][0]["amount"] == 1000.0 and d["top_customers"][0]["customer"]["id"] == 1
    assert q(model="不存在的型号").product_detail() is None


def test_model_view_unit_default_and_pack_spec(tmp_path):
    """填料型号：编号里的 20kg/桶 是包装规格；计量单位按有库存的批号判断，CRM 未填时按公斤。"""
    path = tmp_path / "pack.sqlite"
    store = Store(path)
    seed(store)
    batches = [  # 同一型号三个批号：公斤 / 历史上把包装当单位（已无库存）/ 未填单位
        {"id": "11", "sn": "260227AB-20kg/桶", "name": "SP-100-8-C4-NP", "model": "-", "unit": "公斤", "price": "8800.0000",
         "status": "正常", "class": "制备色谱填料", "lnum": "130.000", "ldown": "0.000", "moddate": "2026-01-01"},
        {"id": "12", "sn": "121031-100g/桶", "name": "SP-100-8-C4-NP", "model": "-", "unit": "桶", "price": "8800.0000",
         "status": "停用", "class": "制备色谱填料", "lnum": "0.000", "ldown": "0.000", "moddate": "2026-01-01"},
        {"id": "13", "sn": "230101AK-1kg/桶", "name": "SP-100-8-C4-NP", "model": "-", "unit": "", "price": "8800.0000",
         "status": "正常", "class": "制备色谱填料", "lnum": "20.000", "ldown": "0.000", "moddate": "2026-01-01"},
    ]
    store.upsert_raw("product", batches)
    store.upsert_normalized(SPEC_BY_DT["product"], batches)
    store.close()
    mirror = Mirror(path)
    conn = mirror.connect()
    lk = mirror.lookups(conn)
    query = lambda **p: Query(conn, lk, {k: str(v) for k, v in p.items()})  # noqa: E731

    row = next(r for r in query(view="model", months="0").products()["rows"] if r["model_name"] == "SP-100-8-C4-NP")
    assert row["batches"] == 3 and row["batches_in_stock"] == 2 and row["stock"] == 150.0
    assert row["units"] == 1 and row["unit"] == "公斤"        # 库存为 0 的“桶”不算，空单位按填料默认公斤
    d = query(model="SP-100-8-C4-NP", months="0").product_detail()
    packs = {b["sn"]: b["pack"] for b in d["batches"]}
    assert packs == {"260227AB-20kg/桶": "20kg/桶", "121031-100g/桶": "100g/桶", "230101AK-1kg/桶": "1kg/桶"}
    assert next(b for b in d["batches"] if b["id"] == 13)["unit"] == "公斤"
    assert next(b for b in d["batches"] if b["id"] == 13)["unit_assumed"] is True
    one = query(sn="260227AB-20kg/桶").product_detail()["product"]
    assert one["pack"] == "20kg/桶" and one["unit"] == "公斤" and one["unit_assumed"] is False


def test_sales_product_dimension_merges_batches_of_one_model(tmp_path):
    """销售分析的产品维度按型号合并：同型号两个批号的订单合成一行，订单筛选也按整个型号。"""
    path = tmp_path / "model_sales.sqlite"
    store = Store(path)
    seed(store)
    y = str(THIS_YEAR)
    batches = [
        {"id": "21", "sn": "260227AB-20kg/桶", "name": "SP-100-8-C4-NP", "model": "-", "unit": "公斤", "price": "8800.0000",
         "status": "正常", "class": "制备色谱填料", "lnum": "130.000", "ldown": "0.000", "moddate": "2026-01-01"},
        {"id": "22", "sn": "260430AB-20kg/桶", "name": "SP-100-8-C4-NP", "model": "-", "unit": "公斤", "price": "8800.0000",
         "status": "正常", "class": "制备色谱填料", "lnum": "40.000", "ldown": "0.000", "moddate": "2026-01-01"},
    ]
    orders = [
        {"id": "91", "No.": f"mw{y}0401091", "subject": "型号合并一", "cu_sn": "[id:1]", "type": "1", "status": "2", "confirm": "2", "st_send": "4",
         "sum": "8000.00", "who": "王勇尊", "date": f"{y}-04-01", "end_date": f"{y}-04-01", "money_type": "RMB",
         "goods": [{"id": "91", "prod": "260227AB-20kg/桶", "prod_name": "SP-100-8-C4-NP", "amount": "2.000", "un_price": "4000", "sum": "8000.00"}]},
        {"id": "92", "No.": f"mw{y}0402092", "subject": "型号合并二", "cu_sn": "[id:2]", "type": "1", "status": "2", "confirm": "2", "st_send": "4",
         "sum": "4000.00", "who": "王勇尊", "date": f"{y}-04-02", "end_date": f"{y}-04-02", "money_type": "RMB",
         "goods": [{"id": "92", "prod": "260430AB-20kg/桶", "prod_name": "SP-100-8-C4-NP", "amount": "1.000", "un_price": "4000", "sum": "4000.00"}]},
    ]
    store.upsert_raw("product", batches)
    store.upsert_normalized(SPEC_BY_DT["product"], batches)
    store.upsert_raw("contract", orders)
    store.upsert_normalized(SPEC_BY_DT["contract"], orders)
    store.close()
    mirror = Mirror(path)
    conn = mirror.connect()
    lk = mirror.lookups(conn)
    query = lambda **p: Query(conn, lk, {k: str(v) for k, v in p.items()})  # noqa: E731

    rows = {r["key"]: r for r in query(by="product", years=THIS_YEAR).sales()["rows"]}
    row = rows["SP-100-8-C4-NP"]                                   # 两个批号合成一行
    assert row["total"] == 12000.0 and row["batches"] == 2 and row["cells"][str(THIS_YEAR)]["qty"] == 3.0
    assert row["class"] == "制备色谱填料" and row["sub"].startswith("制备色谱填料")
    # 订单列表按型号筛选：两张单都算进来；按单个批号筛选只剩一张
    assert query(prod="SP-100-8-C4-NP").orders()["total"] == 2
    assert query(prod="260227AB-20kg/桶").orders()["total"] == 1
    # 业务员看板与总览的产品 Top 榜同样按型号
    top = query(who="M9", year=THIS_YEAR).salesperson()["top_products"]
    assert top[0]["model_name"] == "SP-100-8-C4-NP" and top[0]["batches"] == 2 and top[0]["amount"] == 12000.0
