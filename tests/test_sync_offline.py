"""离线测试：同步引擎 + SQLite 存储（用内存假数据代替 CRM）。

运行：python -m pytest tests -q
"""

import copy
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sync import SPEC_BY_DT, Store, Syncer  # noqa: E402
from sync.store import col_name  # noqa: E402


class FakeClient:
    """模拟 api.output / api.fieldinfo：支持 lastid 分页、lasttime、id、status、date 区间过滤。"""

    def __init__(self):
        self.tables = {}
        self.calls = []

    def iter_output(self, dt_name, *, lastid=0, max_pages=None, **params):
        self.calls.append((dt_name, dict(lastid=lastid, **params)))
        rows = [r for r in self.tables.get(dt_name, []) if int(r["id"]) > int(lastid)]
        if "id" in params:
            rows = [r for r in rows if str(r["id"]) == str(params["id"])]
        if "lasttime" in params:
            rows = [r for r in rows if r.get("moddate", "") >= params["lasttime"][:10]]
        if "status" in params:
            rows = [r for r in rows if str(r.get("status")) == str(params["status"])]
        if "date" in params:
            start, end = params["date"].split(",")
            rows = [r for r in rows if start <= r.get("date", "") <= end]
        for r in sorted(rows, key=lambda r: int(r["id"])):
            yield copy.deepcopy(r)

    def users(self):
        return [{"part": "B1", "name": "boss"}]

    def field_names(self, dt_name):
        return {"id": "ID", "cu_name": "客户名称"}

    def dictionary(self, dt_name, field):
        return [{"key": "1", "value": "选项1", "flag": "USE"}]


class FakeXT:
    def __init__(self):
        self.client = FakeClient()


def seed(client: FakeClient):
    today = dt.date.today().isoformat()
    client.tables = {
        "user": [{"id": "1", "user": "boss", "part": "B1", "name": "boss", "status": "0", "type": "0", "isadmin": "1"}],
        "csstree": [{"id": "1", "tid": "1", "title": "介质", "upid": "0", "status": "0"}],
        "product": [
            {"id": "10", "sn": "P001", "name": "填料A", "model": "10um", "price": "100.0000", "moddate": "2026-01-01"},
            {"id": "11", "sn": "P002", "name": "填料B", "model": "5um", "price": "200.0000", "moddate": "2026-01-01"},
        ],
        "prod_alias": [],
        "customer": [
            {"id": "1", "sn": "C001", "cu_name": "甲公司", "life": "2", "moddate": "2026-01-01",
             "contact": [{"id": "101", "name": "张三", "mphone": "138"}, {"id": "102", "name": "李四", "mphone": "139"}]},
            {"id": "2", "sn": "", "cu_name": "乙公司", "life": "1", "moddate": "2026-01-01", "contact": []},
        ],
        "customerext": [{"id": "1", "sn": "C001", "ext_item1": "自定义"}],
        "contract": [
            {"id": "1", "No.": "DD001", "subject": "订单一", "cu_sn": "C001", "status": "2", "sum": "300.00", "date": "2026-03-01",
             "goods": [{"id": "1", "prod": "P001", "amount": "1.000", "un_price": "100", "sum": "100"}, {"id": "2", "prod": "P002", "amount": "1.000", "un_price": "200", "sum": "200"}]},
            {"id": "2", "No.": "DD002", "subject": "订单二", "cu_sn": "[id:2]", "status": "1", "sum": "50.00", "date": today, "goods": {"0": {"id": "3", "prod": "P001", "amount": "0.500", "un_price": "100", "sum": "50"}}},
        ],
        "gathering_note": [{"id": "1", "cu_sn": "C001", "co_id": "1", "date": "2026-03-05", "money": "300.00", "type": "1"}],
    }


@pytest.fixture
def env(tmp_path):
    xt = FakeXT()
    seed(xt.client)
    store = Store(tmp_path / "mirror.sqlite")
    return xt, store, Syncer(xt, store)


TABLES = ["user", "csstree", "product", "customer", "customerext", "contract", "gathering_note"]


def test_init_full_pull_populates_raw_and_normalized(env):
    xt, store, syncer = env
    results = syncer.run("init", TABLES)
    assert all(r["status"] == "ok" for r in results)
    assert store.count_raw("customer") == 2
    assert store.count_raw("contract") == 2
    rows = store.conn.execute("SELECT id, sn, cu_name FROM customer ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [(1, "C001", "甲公司"), (2, "", "乙公司")]
    assert store.conn.execute("SELECT COUNT(*) FROM contact").fetchone()[0] == 2
    goods = store.conn.execute("SELECT contract_id, prod FROM contract_goods ORDER BY contract_id, _seq").fetchall()
    assert [tuple(g) for g in goods] == [(1, "P001"), (1, "P002"), (2, "P001")]
    assert store.conn.execute('SELECT no_ FROM contract WHERE id = 1').fetchone()[0] == "DD001"
    assert store.conn.execute("SELECT ext_item1 FROM customer_ext WHERE id = 1").fetchone()[0] == "自定义"
    state = store.get_state("customer")
    assert state["last_full_at"] and state["lasttime"]


def test_views_join_customer_by_sn_or_id(env):
    xt, store, syncer = env
    syncer.run("init", TABLES)
    rows = {r["order_no"]: r["cu_name"] for r in store.conn.execute("SELECT order_no, cu_name FROM v_contract")}
    assert rows == {"DD001": "甲公司", "DD002": "乙公司"}
    overview = {r["cu_name"]: (r["orders"], r["order_amount"], r["receipt_amount"], r["contacts"]) for r in store.conn.execute("SELECT * FROM v_customer_overview")}
    assert overview["甲公司"] == (1, 300.0, 300.0, 2)
    assert overview["乙公司"] == (1, 50.0, None, 0)
    monthly = store.conn.execute("SELECT month, amount FROM v_monthly_sales ORDER BY month").fetchall()
    assert monthly[0][0] == "2026-03" and monthly[0][1] == 300.0


def test_incremental_picks_up_changes_and_new_rows(env):
    xt, store, syncer = env
    syncer.run("init", TABLES)
    today = dt.date.today().isoformat()
    # 修改客户名称（moddate 更新）、新增订单、修改已有活动订单状态
    xt.client.tables["customer"][0]["cu_name"] = "甲公司（更名）"
    xt.client.tables["customer"][0]["moddate"] = today
    xt.client.tables["contract"].append({"id": "3", "No.": "DD003", "subject": "订单三", "cu_sn": "C001", "status": "1", "sum": "10.00", "date": today, "goods": []})
    xt.client.tables["contract"][1]["status"] = "2"
    results = {r["dt"]: r for r in syncer.run("incremental", TABLES)}
    assert results["customer"]["updated"] == 1
    assert store.conn.execute("SELECT cu_name FROM customer WHERE id = 1").fetchone()[0] == "甲公司（更名）"
    assert store.count_raw("contract") == 3
    assert results["contract"]["inserted"] == 1
    # 订单二状态 1→2：不再命中 status=1 过滤，但命中近 90 天 date 区间，因此被重拉并更新
    assert store.conn.execute("SELECT status FROM contract WHERE id = 2").fetchone()[0] == "2"
    # 再跑一次：无变化
    again = {r["dt"]: r for r in syncer.run("incremental", TABLES)}
    assert again["customer"]["updated"] == 0 and again["contract"]["inserted"] == 0


def test_full_pull_detects_deletions(env):
    xt, store, syncer = env
    syncer.run("init", TABLES)
    del xt.client.tables["product"][1]
    results = {r["dt"]: r for r in syncer.run("full", ["product"])}
    assert results["product"]["deleted"] == 1
    assert store.count_raw("product") == 1
    assert store.conn.execute("SELECT _deleted_at FROM product WHERE id = 11").fetchone()[0] is not None
    # 记录恢复后再次出现：取消删除标记
    xt.client.tables["product"].append({"id": "11", "sn": "P002", "name": "填料B", "model": "5um", "price": "200.0000", "moddate": "2026-01-01"})
    syncer.run("full", ["product"])
    assert store.conn.execute("SELECT _deleted_at FROM product WHERE id = 11").fetchone()[0] is None


def test_rebuild_normalized_and_dictionaries(env):
    xt, store, syncer = env
    syncer.run("init", TABLES)
    store.conn.execute("DELETE FROM contract_goods")
    store.conn.commit()
    n = store.rebuild_normalized(SPEC_BY_DT["contract"])
    assert n == 2
    assert store.conn.execute("SELECT COUNT(*) FROM contract_goods").fetchone()[0] == 3
    summary = syncer.refresh_dictionaries()
    assert summary["users"] == 1 and summary["dictionaries"] > 0 and not summary["failed"]
    assert store.conn.execute("SELECT value FROM dictionaries WHERE dt='user' AND key='B1'").fetchone()[0] == "boss"


def test_optional_table_failure_is_skipped(env):
    xt, store, syncer = env

    def boom(dt_name, **kw):
        from xtools import XToolsApiError
        raise XToolsApiError(50001, "未启用外部库存", cmd="api.output")
        yield  # pragma: no cover

    xt.client.iter_output = boom
    result = syncer.run("init", ["sr_notice"])[0]
    assert result["status"] == "skipped"
    assert store.get_state("sr_notice")["last_status"] == "skipped"


def test_col_name_mapping():
    assert col_name("No.") == "no_"
    assert col_name("cu_name") == "cu_name"
    assert col_name("1abc") == "f_1abc"
