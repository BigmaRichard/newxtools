"""离线行为测试：用假 HTTP 会话模拟服务器，验证登录、sid 缓存、失效重登、限频、分页与错误映射。

运行：python -m pytest tests -q
"""

import json
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xtools import (  # noqa: E402
    XToolsApiError,
    XToolsBusinessError,
    XToolsClient,
    XToolsConfig,
    XToolsSessionExpired,
    XToolsTransportError,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self.text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)


class FakeServer:
    """极简仿真：校验 md 与 sid；用 script 队列控制每次响应。"""

    def __init__(self, appkey, comkey, com, part):
        self.appkey, self.comkey, self.com, self.part = appkey, comkey, com, part
        self.calls = []
        self.headers = {}
        self.valid_sids = set()
        self.login_count = 0
        self.script = []  # 可放入 callable(fields) -> payload | FakeResponse | Exception

    def post(self, url, data=None, timeout=None, verify=None):
        fields = {k: (v.decode("utf-8") if isinstance(v, bytes) else v) for k, v in data.items()}
        self.calls.append(fields)
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
            payload = item(fields) if callable(item) else item
            return payload if isinstance(payload, FakeResponse) else FakeResponse(payload)
        # 默认行为：校验签名
        expected = XToolsClient.sign(fields["param"], fields["stamp"], fields["upr"], fields["cmd"], self.appkey)
        if fields["md"] != expected:
            return FakeResponse({"ok": 0, "err": {"errno": 10001, "errmsg": "md 校验失败"}})
        if fields["cmd"] == "user.login":
            upr = json.loads(fields["upr"])
            code = XToolsClient.login_code(fields["stamp"], self.comkey, self.com, self.part)
            if upr.get("md") != code:
                return FakeResponse({"ok": 0, "err": {"errno": 10002, "errmsg": "登录验证码错误"}})
            self.login_count += 1
            sid = f"sid{self.login_count:04d}"
            self.valid_sids.add(sid)
            return FakeResponse({"ok": 1, "ret": {"com": self.com, "part": self.part, "sid": sid}})
        upr = json.loads(fields["upr"])
        if upr.get("sid") not in self.valid_sids:
            return FakeResponse({"ok": 0, "err": {"errno": 20101, "errmsg": "session已经失效，请进行重新登录!"}})
        param = json.loads(fields["param"])
        if fields["cmd"] == "api.output":
            lastid = int(param.get("lastid", 0))
            rows = [{"id": str(i)} for i in range(lastid + 1, min(lastid + 100, 250) + 1)]
            return FakeResponse({"ok": 1, "ret": {"ok": 1, "data": rows}})
        if fields["cmd"] == "api.input":
            return FakeResponse({"ok": 1, "ret": {"ok": 1, "msg": "添加成功", "id": 99}})
        return FakeResponse({"ok": 1, "ret": {"ok": 1, "msg": "ok"}})


@pytest.fixture
def env(tmp_path):
    config = XToolsConfig(
        appid="open00001_sajdjsjsj",
        appkey="open1slslslsdldlsdlds",
        comkeyid="xtoolsplusd002",
        comkey="xtoolsplusd002sjsjsj",
        com="d002",
        part="B1",
        sid_cache=tmp_path / "sid.json",
        min_interval=0,
    )
    server = FakeServer(config.appkey, config.comkey, config.com, config.part)
    clock = {"now": 1_700_000_000.0}
    slept = []

    def sleep(seconds):
        slept.append(seconds)
        clock["now"] += seconds

    client = XToolsClient(config, session=server, clock=lambda: clock["now"], sleep=sleep)
    return client, server, clock, slept


def test_login_and_sid_cache_reuse(env):
    client, server, clock, _ = env
    sid = client.login()
    assert sid == "sid0001" and server.login_count == 1
    # 新实例读取缓存，不再登录
    client2 = XToolsClient(client.config, session=server, clock=lambda: clock["now"], sleep=lambda s: None)
    assert client2.sid == "sid0001"
    client2.output("customer", lastid=0)
    assert server.login_count == 1


def test_login_respects_ten_second_interval(env):
    client, server, clock, slept = env
    client.login()
    clock["now"] += 3
    client.login(force=True)
    assert server.login_count == 2
    assert slept and abs(slept[0] - 7) < 1e-6


def test_session_expired_triggers_relogin_and_retry(env):
    client, server, clock, _ = env
    client.login()
    server.valid_sids.clear()  # 服务器端踢掉会话
    clock["now"] += 60
    rows = client.output("customer", lastid=0)
    assert len(rows) == 100
    assert server.login_count == 2
    cmds = [c["cmd"] for c in server.calls]
    assert cmds == ["user.login", "api.output", "user.login", "api.output"]


def test_iter_output_paginates_by_lastid(env):
    client, _, _, _ = env
    rows = list(client.iter_output("customer"))
    assert len(rows) == 250
    assert rows[0]["id"] == "1" and rows[-1]["id"] == "250"


def test_business_error_raised(env):
    client, server, _, _ = env
    client.login()
    server.script.append({"ok": 1, "ret": {"ok": 0, "msg": "客户编号已存在"}})
    with pytest.raises(XToolsBusinessError) as info:
        client.input("customer", {"cu_name": "x"})
    assert "客户编号已存在" in str(info.value)


def test_api_error_raised_with_errno(env):
    client, server, _, _ = env
    client.login()
    server.script.append({"ok": 0, "err": {"errno": 40001, "errmsg": "无权限"}})
    with pytest.raises(XToolsApiError) as info:
        client.output("customer")
    assert info.value.errno == 40001


def test_write_is_not_retried_on_network_error(env):
    client, server, _, _ = env
    client.login()
    server.script.append(requests.ConnectionError("boom"))
    with pytest.raises(XToolsTransportError):
        client.input("customer", {"cu_name": "x"})
    assert len([c for c in server.calls if c["cmd"] == "api.input"]) == 1


def test_read_is_retried_on_network_error(env):
    client, server, _, _ = env
    client.login()
    server.script.append(requests.ConnectionError("boom"))
    rows = client.output("customer", lastid=0)
    assert len(rows) == 100
    assert len([c for c in server.calls if c["cmd"] == "api.output"]) == 2


def test_read_retries_five_times_with_growing_backoff(env):
    client, server, _, slept = env
    client.login()
    slept.clear()
    # 连续 4 次超时 + 1 次 DNS 抖动后成功：共 5 次尝试，等待 2/5/15/30 秒
    server.script.extend([requests.ReadTimeout("t1"), requests.ReadTimeout("t2"), requests.ReadTimeout("t3"),
                          requests.ConnectionError("dns"), lambda f: {"ok": 1, "ret": {"ok": 1, "data": [{"id": "1"}]}}])
    rows = client.output("contract", lastid=0, extend=1)
    assert rows == [{"id": "1"}]
    assert len([c for c in server.calls if c["cmd"] == "api.output"]) == 5
    assert slept == [2.0, 5.0, 15.0, 30.0]
    # 第 5 次仍失败：抛 XToolsTransportError，不再重试
    server.script.extend([requests.ReadTimeout("t")] * 5)
    with pytest.raises(XToolsTransportError) as info:
        client.output("contract", lastid=0)
    assert "已重试 5 次" in str(info.value)
    assert len([c for c in server.calls if c["cmd"] == "api.output"]) == 10


def test_read_retries_gateway_5xx_but_write_does_not(env):
    client, server, _, _ = env
    client.login()
    server.script.extend([FakeResponse("<html>502 Bad Gateway</html>", status_code=502),
                          FakeResponse("<html>503</html>", status_code=503)])
    rows = client.output("customer", lastid=0)
    assert len(rows) == 100
    assert len([c for c in server.calls if c["cmd"] == "api.output"]) == 3
    server.script.append(FakeResponse("<html>502</html>", status_code=502))
    with pytest.raises(XToolsTransportError) as info:
        client.input("customer", {"cu_name": "x"})
    assert info.value.status_code == 502
    assert len([c for c in server.calls if c["cmd"] == "api.input"]) == 1


def test_param_serialization_is_compact_and_unicode(env):
    client, server, _, _ = env
    client.login()
    client.input("customer", {"cu_name": "中国海上救援大队", "contact": [{"name": "刘大庆"}]})
    sent = server.calls[-1]["param"]
    assert sent == '{"dt":"customer","data":{"cu_name":"中国海上救援大队","contact":[{"name":"刘大庆"}]}}'


def test_non_json_response_is_transport_error(env):
    client, server, _, _ = env
    client.login()
    server.script.append(FakeResponse("<html>维护中</html>", status_code=200))
    with pytest.raises(XToolsTransportError) as info:
        client.output("customer")
    assert "不是合法 JSON" in str(info.value)
    # 非网关类 HTTP 错误（如 404）不重试，直接报错
    server.script.append(FakeResponse("not found", status_code=404))
    with pytest.raises(XToolsTransportError) as info:
        client.output("customer")
    assert info.value.status_code == 404
    assert len([c for c in server.calls if c["cmd"] == "api.output"]) == 2


def test_session_expired_class(env):
    client, server, _, _ = env
    client.login()
    server.script.append({"ok": 0, "err": {"errno": 20102, "errmsg": "session已经失效"}})
    server.script.append({"ok": 0, "err": {"errno": 20102, "errmsg": "session已经失效"}})
    server.script.append({"ok": 0, "err": {"errno": 20102, "errmsg": "session已经失效"}})
    with pytest.raises(XToolsSessionExpired):
        client.output("customer")


def test_update_contact_guards_and_payload(env):
    from xtools import XTools
    client, server, _, _ = env
    xt = XTools(client.config, session=server, clock=client._clock, sleep=lambda s: None)
    xt.client._sid = client.login()
    with pytest.raises(ValueError):
        xt.customers.update_contact({"name": "无 id"})
    with pytest.raises(ValueError):
        xt.customers.update_contact({"id": 30735, "cu_sn": "C0001"})
    server.script.append({"ok": 1, "ret": {"ok": 1, "msg": "修改联系人成功"}})
    ret = xt.customers.update_contact({"id": 30735, "mphone": "13800138000"})
    assert ret["msg"] == "修改联系人成功"
    sent = server.calls[-1]
    assert sent["cmd"] == "api.update"
    assert sent["param"] == '{"dt":"contact","extend":1,"data":{"id":30735,"mphone":"13800138000"}}'


def test_return_readers_use_expected_dt(env):
    from xtools import XTools
    client, server, _, _ = env
    xt = XTools(client.config, session=server, clock=client._clock, sleep=lambda s: None)
    xt.client._sid = client.login()
    server.script.append({"ok": 1, "ret": {"ok": 1, "data": [{"id": "196", "rtnitem": []}]}})
    assert xt.orders.get_return(196)["id"] == "196"
    assert json.loads(server.calls[-1]["param"]) == {"dt": "libreturn", "id": 196}
    server.script.append({"ok": 1, "ret": {"ok": 1, "data": [{"id": "152", "purrtnitem": []}]}})
    assert xt.finance.get_purchase_return(152)["id"] == "152"
    assert json.loads(server.calls[-1]["param"]) == {"dt": "purreturn", "id": 152}
