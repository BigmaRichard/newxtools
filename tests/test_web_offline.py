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


def seed(store: Store) -> None:
    users = [
        {"id": "1", "user": "boss", "part": "B1", "name": "boss", "status": "0", "type": "0", "isadmin": "1"},
        {"id": "2", "user": "m9", "part": "M9", "name": "王勇尊", "status": "0", "type": "0", "isadmin": "0"},
        {"id": "3", "user": "m23", "part": "M23", "name": "李勇刚(离职)", "status": "1", "type": "0", "isadmin": "0"},
    ]
    customers = [
        {"id": "1", "sn": "1302", "cu_name": "广州研创生物技术发展有限公司", "m_name": "研创", "life": "3", "type": "3", "cu_status": "2", "owner": "M9", "city": "广州市", "creatdate": "2013-11-01", "moddate": "2026-01-01",
         "contact": [{"id": "101", "name": "张三", "headship": "采购", "mphone": "13800000001"}]},
        {"id": "2", "sn": "", "cu_name": "贵州医科大学-药学院-钱星凯", "m_name": "", "life": "2", "type": "2", "cu_status": "1", "owner": "M23", "city": "贵阳市", "creatdate": "2025-05-01", "moddate": "2026-09-01", "contact": []},
        {"id": "3", "sn": "", "cu_name": "无订单客户", "m_name": "", "life": "1", "type": "1", "cu_status": "1", "owner": "M9", "city": "", "creatdate": "2026-09-01", "moddate": "2026-09-01", "contact": []},
    ]
    products = [{"id": "1", "sn": "08086-31", "name": "πNAP Packed Column 4.6mmI.D.x250mm", "model": "-", "unit": "支", "price": "3000.0000", "status": "正常", "class": "色谱柱", "moddate": "2026-01-01"}]
    y = str(THIS_YEAR)
    contracts = [
        {"id": "10", "No.": f"mw{y}0101010", "subject": "旧单（用 sn 关联客户）", "cu_sn": "1302", "type": "1", "status": "2", "confirm": "2", "st_send": "4", "sum": "1000.00", "who": "王勇尊",
         "date": f"{THIS_YEAR - 1}-06-01", "end_date": f"{THIS_YEAR - 1}-06-01", "money_type": "RMB", "goods": [{"id": "1", "prod": "08086-31", "prod_name": "πNAP", "amount": "1.000", "un_price": "1000", "sum": "1000.00"}]},
        {"id": "11", "No.": f"mw{y}0301011", "subject": "今年订单一", "cu_sn": "[id:1]", "type": "1", "status": "2", "confirm": "2", "st_send": "4", "sum": "2000.00", "who": "王勇尊",
         "date": f"{y}-03-01", "end_date": f"{y}-03-01", "money_type": "RMB", "j1": "含税", "goods": [{"id": "2", "prod": "08086-31", "prod_name": "πNAP", "amount": "2.000", "un_price": "1000", "sum": "2000.00"}]},
        {"id": "12", "No.": f"mw{y}0901012", "subject": "执行中订单", "cu_sn": "[id:2]", "type": "2", "status": "1", "confirm": "2", "st_send": "1", "sum": "500.00", "who": "李勇刚(离职)",
         "date": TODAY.isoformat(), "end_date": TODAY.isoformat(), "money_type": "RMB", "goods": []},
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
    ]
    for dt_name, rows in [("user", users), ("customer", customers), ("product", products), ("contract", contracts), ("gathering_note", notes), ("gathering", plans),
                          ("sendgoods", sends), ("libout", libouts), ("action", actions)]:
        store.upsert_raw(dt_name, rows)
        store.upsert_normalized(SPEC_BY_DT[dt_name], rows)
        store.set_state(dt_name, lastid=len(rows), last_full_at="2026-09-18 05:36:00", last_run_at="2026-09-18 05:36:34", last_status="ok", last_rows=len(rows))
    store.save_dictionary("user", "pr2nm", [{"key": u["part"], "value": u["name"], "flag": "USE"} for u in users])
    store.save_dictionary("contract", "status", [{"key": "1", "value": "执行中", "flag": "Default"}, {"key": "2", "value": "结束", "flag": "USE"}, {"key": "3", "value": "意外中止", "flag": "USE"}])
    store.save_dictionary("gathering", "status", [{"key": "1", "value": "已回", "flag": "USE"}, {"key": "2", "value": "未回", "flag": "Default"}, {"key": "4", "value": "部分回款", "flag": "USE"}])
    store.save_dictionary("action", "type", [{"key": "1", "value": "电话", "flag": "USE"}, {"key": "2", "value": "市内拜访", "flag": "USE"}])
    store.save_dictionary("customer", "life", [{"key": "1", "value": "潜在", "flag": "Default"}, {"key": "2", "value": "签约", "flag": "USE"}, {"key": "3", "value": "重复购买", "flag": "USE"}])
    store.save_field_names("contract", {"j1": "含税方式"})


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
    assert d["top_products"][0]["sn"] == "08086-31" and d["top_products"][0]["name"].startswith("πNAP Packed")
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
    assert d["actions"][0]["subject"] == "上门拜访"
    assert {x["key"]: x for x in d["extras"]}["j1"]["name"] == "含税方式"
    assert all(x["key"] != "No." for x in d["extras"])
    assert q().order_detail(999) is None


def test_customers_list_aggregates_both_key_forms(q):
    res = q(sort="amount").customers()
    assert res["total"] == 3
    top = res["rows"][0]
    assert top["id"] == 1 and top["orders"] == 2 and top["order_amount"] == 3000.0 and top["receipts"] == 2500.0 and top["contacts"] == 1
    assert top["last_order"] == f"{THIS_YEAR}-03-01"
    assert q(q="医科").customers()["rows"][0]["id"] == 2
    assert q(owner="M23").customers()["total"] == 1
    assert q(life="1").customers()["rows"][0]["name"] == "无订单客户"
    d = q().customer_detail(1)
    assert d["customer"]["owner"] == "王勇尊" and len(d["contacts"]) == 1
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
    assert row["contact"] == "张三" and row["content"] == "" and row["order_id"] == 11 and row["type_text"] == "市内拜访" and row["date_flag"] == ""
    assert next(r for r in res["rows"] if r["id"] == 4)["date_flag"] == "future"
    assert [d["date"] for d in res["by_day"]] == [TODAY.isoformat()]  # 未来日期不进按日统计
    assert q(who="M23").actions()["total"] == 2  # 单独与多人记录都命中
    everything = q().actions()
    assert {w["part"]: w["count"] for w in everything["by_who"]} == {"M9": 4, "M23": 2}
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
