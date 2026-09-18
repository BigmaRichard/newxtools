"""离线测试：前台访问控制（来源网段 + Basic 认证）与安装脚本生成的访问密码。"""

import base64
import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sync import Store  # noqa: E402
from web.auth import AccessControl, from_env, load_dotenv  # noqa: E402
from web.server import make_server  # noqa: E402

sys.path.insert(0, str(ROOT / "tests"))
from test_web_offline import seed  # noqa: E402

TS_IP = "100.101.102.103"  # Tailscale 分配的地址
BASIC = "Basic " + base64.b64encode("mw:secret".encode()).decode()


def test_local_only_needs_no_password():
    a = AccessControl("127.0.0.1")
    assert a.local_only and not a.require_auth
    assert a.check("127.0.0.1", None) is None
    assert "仅本机" in a.describe()


def test_remote_requires_password_and_tailscale_source():
    a = AccessControl("0.0.0.0", "mw", "secret")
    assert a.check("127.0.0.1", None) is None                      # 本机免密（含安装脚本的就绪探测）
    assert a.check(TS_IP, None) == (401, "需要账号密码")
    assert a.check(TS_IP, "Basic " + base64.b64encode(b"mw:wrong").decode())[0] == 401
    assert a.check(TS_IP, "Bearer x")[0] == 401
    assert a.check(TS_IP, BASIC) is None
    assert a.check("fd7a:115c:a1e0::9", BASIC) is None              # Tailscale 的 IPv6 段
    assert a.check("192.168.1.9", BASIC)[0] == 403                  # 同一 Wi-Fi 的其他设备也挡掉
    assert a.check("203.0.113.5", BASIC)[0] == 403
    assert a.check("不是地址", BASIC)[0] == 403


def test_extra_allowed_network():
    a = AccessControl("0.0.0.0", "mw", "secret", allow="192.168.1.0/24, 10.0.0.0/8")
    assert a.check("192.168.1.9", BASIC) is None and a.check("10.1.2.3", BASIC) is None
    assert a.check("192.168.2.9", BASIC)[0] == 403


def test_missing_password_stops_serving_remotes():
    a = AccessControl("0.0.0.0", "mw", "")
    assert a.misconfigured
    assert a.check("127.0.0.1", None) is None                      # 本机仍能用
    code, msg = a.check(TS_IP, BASIC)
    assert code == 503 and "XTOOLS_WEB_PASSWORD" in msg
    assert "未设置密码" in a.describe()


def test_from_env_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("XTOOLS_WEB_PASSWORD", raising=False)
    (tmp_path / ".env").write_text('XTOOLS_COM=pc7699\nXTOOLS_WEB_USER = mw \nXTOOLS_WEB_PASSWORD="secret"\n# 注释\n', encoding="utf-8")
    assert load_dotenv(tmp_path)["XTOOLS_WEB_PASSWORD"] == "secret"
    a = from_env(tmp_path, "0.0.0.0")
    assert a.user == "mw" and a.check(TS_IP, BASIC) is None
    monkeypatch.setenv("XTOOLS_WEB_PASSWORD", "from-env")           # 环境变量优先于 .env
    assert from_env(tmp_path, "0.0.0.0").password == "from-env"


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "mirror.sqlite"
    store = Store(path)
    seed(store)
    store.close()
    return path


def test_http_blocks_without_credentials(db, monkeypatch):
    monkeypatch.setattr(AccessControl, "is_loopback", staticmethod(lambda ip: False))  # 装作请求来自 Tailscale
    monkeypatch.setattr(AccessControl, "allowed_source", lambda self, ip: True)
    server = make_server(db, "127.0.0.1", 0, AccessControl("0.0.0.0", "mw", "secret"))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{port}"
        for path in ("/", "/api/meta", "/api/orders", "/api/export/orders"):
            with pytest.raises(urllib.error.HTTPError) as info:
                urllib.request.urlopen(base + path)
            assert info.value.code == 401 and info.value.headers["WWW-Authenticate"].startswith("Basic")
        req = urllib.request.Request(base + "/api/meta", headers={"Authorization": BASIC})
        assert json.loads(urllib.request.urlopen(req).read())["today"]
        html = urllib.request.urlopen(urllib.request.Request(base + "/", headers={"Authorization": BASIC})).read().decode()
        assert "XTools 数据前台" in html
    finally:
        server.shutdown()
        server.server_close()


def test_http_blocks_foreign_source(db, monkeypatch):
    monkeypatch.setattr(AccessControl, "is_loopback", staticmethod(lambda ip: False))
    monkeypatch.setattr(AccessControl, "allowed_source", lambda self, ip: False)   # 装作来自 Tailscale 以外的地址
    server = make_server(db, "127.0.0.1", 0, AccessControl("0.0.0.0", "mw", "secret"))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/meta", headers={"Authorization": BASIC})
        with pytest.raises(urllib.error.HTTPError) as info:
            urllib.request.urlopen(req)
        assert info.value.code == 403 and "来源地址" in json.loads(info.value.read())["error"]
    finally:
        server.shutdown()
        server.server_close()


def install_module():
    spec = importlib.util.spec_from_file_location("install_launchd", ROOT / "scripts" / "install_launchd.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_install_script_generates_password(tmp_path, monkeypatch):
    monkeypatch.delenv("XTOOLS_WEB_PASSWORD", raising=False)
    mod = install_module()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    (tmp_path / ".env").write_text("XTOOLS_COM=pc7699", encoding="utf-8")   # 末尾没有换行
    assert mod.ensure_web_password("127.0.0.1") == ("", "", False)          # 只监听本机时不需要密码
    user, password, created = mod.ensure_web_password("0.0.0.0")
    assert created and user == "xtools" and len(password) == 14 and password.count("-") == 2
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert text.startswith("XTOOLS_COM=pc7699\n") and f"XTOOLS_WEB_PASSWORD={password}" in text
    assert mod.ensure_web_password("0.0.0.0") == ("xtools", password, False)  # 第二次沿用，不重新生成
    assert from_env(tmp_path, "0.0.0.0").check(TS_IP, "Basic " + base64.b64encode(f"xtools:{password}".encode()).decode()) is None
