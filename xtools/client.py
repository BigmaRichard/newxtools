"""XToolsCRM（超兔）OPEN API Python 客户端。

协议要点（依据 apizza 导出的《XToolsCRM OPEN API》文档，2026-09-01 版；签名算法已用文档示例核验）：

* 统一入口：POST https://crm.xtcrm.com/open/index.xt，表单字段 cmd / appid / stamp / upr / param / md。
* cmd 取值：user.login（登录）、api.output（读取）、api.input（写入）、api.update（修改）、
  api.cmdact（动作）、api.fieldinfo（字段信息 / 数据字典 / 用户）、api.chgown（客户转移）、api.downfile（附件）。
* param / upr 为 JSON 字符串；签名 md = md5(param + stamp + upr + cmd + appkey)。
  JSON 需与发送的字符串逐字一致：紧凑格式（无空格）、中文不转义。
* 登录 upr = {"comkeyid","com","part","md"}，其中 md = md5(stamp + comkey + com + part)。
  登录接口 10 秒内只能调用一次（errno 30103）；成功后返回 sid，后续请求 upr = {"sid": sid}。
* sid 失效（errno 20101 / 20102）时需重新登录后重试；文档建议以 30 分钟有效期为准。
* 读取接口每次至多返回 100 条，用 lastid（上一页最大 id）翻页。

本模块只依赖 requests。
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

import requests

from .config import LOGIN_MIN_INTERVAL, XToolsConfig
from .errors import (
    LOGIN_THROTTLED_ERRNO,
    SESSION_EXPIRED_ERRNOS,
    XToolsApiError,
    XToolsBusinessError,
    XToolsLoginThrottled,
    XToolsSessionExpired,
    XToolsTransportError,
)

__all__ = ["XToolsClient", "compact_json", "md5_hex"]

JsonLike = Union[Dict[str, Any], List[Any], str]

logger = logging.getLogger("xtools")


def compact_json(obj: JsonLike) -> str:
    """按文档要求序列化：紧凑、中文不转义。传入字符串时原样返回（用于精确控制签名文本）。"""
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _is_ok(value: Any) -> bool:
    return str(value).strip() in ("1", "true", "True")


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class XToolsClient:
    """线程不安全的简单客户端；多线程场景请每线程一个实例（sid 缓存文件可共享）。"""

    USER_AGENT = "xtools-openapi-python/0.2"

    def __init__(
        self,
        config: Optional[XToolsConfig] = None,
        *,
        session: Optional[requests.Session] = None,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.config = config or XToolsConfig.from_env()
        self.http = session or requests.Session()
        self.http.headers.setdefault("User-Agent", self.USER_AGENT)
        self._clock = clock
        self._sleep = sleep
        self._sid: Optional[str] = None
        self._sid_time: float = 0.0
        self._last_login: float = 0.0
        self._last_call: float = 0.0
        self.last_response: Optional[Dict[str, Any]] = None
        self._load_sid_cache()

    # ------------------------------------------------------------------ 签名
    @staticmethod
    def sign(param: str, stamp: str, upr: str, cmd: str, appkey: str) -> str:
        """请求签名：md5(param字符串 + 时间戳 + upr字符串 + cmd + appkey)。"""
        return md5_hex(f"{param}{stamp}{upr}{cmd}{appkey}")

    @staticmethod
    def login_code(stamp: str, comkey: str, com: str, part: str) -> str:
        """登录验证码 upr.md：md5(时间戳 + 客户公司key + 公司内部编码 + 登录人part)。"""
        return md5_hex(f"{stamp}{comkey}{com}{part}")

    def build_request(self, cmd: str, param: JsonLike, upr: JsonLike, *, stamp: Optional[str] = None) -> Dict[str, str]:
        """生成待发送的表单字段（便于调试与离线测试）。"""
        stamp = stamp or str(int(self._clock()))
        param_str = compact_json(param)
        upr_str = compact_json(upr)
        return {
            "cmd": cmd,
            "appid": self.config.appid,
            "stamp": stamp,
            "upr": upr_str,
            "param": param_str,
            "md": self.sign(param_str, stamp, upr_str, cmd, self.config.appkey),
        }

    def build_login_request(self, *, stamp: Optional[str] = None) -> Dict[str, str]:
        stamp = stamp or str(int(self._clock()))
        upr = {
            "comkeyid": self.config.comkeyid,
            "com": self.config.com,
            "part": self.config.part,
            "md": self.login_code(stamp, self.config.comkey, self.config.com, self.config.part),
        }
        return self.build_request("user.login", "[]", upr, stamp=stamp)

    # ------------------------------------------------------------------ sid 缓存
    @property
    def _cache_key(self) -> str:
        return f"{self.config.appid}|{self.config.com}|{self.config.part}"

    def _load_sid_cache(self) -> None:
        path = self.config.sid_cache
        try:
            if path and Path(path).is_file():
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                if data.get("key") == self._cache_key:
                    self._sid = data.get("sid") or None
                    self._sid_time = float(data.get("sid_time") or 0)
                    self._last_login = float(data.get("last_login") or 0)
        except (OSError, ValueError) as exc:  # 缓存损坏不影响主流程
            logger.warning("读取 sid 缓存失败，忽略：%s", exc)

    def _save_sid_cache(self) -> None:
        path = self.config.sid_cache
        if not path:
            return
        try:
            Path(path).write_text(
                json.dumps(
                    {
                        "key": self._cache_key,
                        "sid": self._sid,
                        "sid_time": self._sid_time,
                        "last_login": self._last_login,
                    }
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("写入 sid 缓存失败，忽略：%s", exc)

    def clear_session(self) -> None:
        """清除本地 sid（不会通知服务器）。"""
        self._sid = None
        self._sid_time = 0.0
        self._save_sid_cache()

    @property
    def sid(self) -> Optional[str]:
        return self._sid

    # ------------------------------------------------------------------ HTTP
    def _throttle(self) -> None:
        gap = self.config.min_interval - (self._clock() - self._last_call)
        if gap > 0:
            self._sleep(gap)

    def _send(self, fields: Dict[str, str], *, idempotent: bool = True) -> Dict[str, Any]:
        """发送表单并返回解析后的 JSON；接口层错误（ok=0）在此转换为异常。"""
        cmd = fields["cmd"]
        attempts = 3 if idempotent else 1
        resp: Optional[requests.Response] = None
        for attempt in range(1, attempts + 1):
            self._throttle()
            self._last_call = self._clock()
            logger.debug("POST %s cmd=%s param=%s", self.config.base_url, cmd, fields["param"][:300])
            try:
                resp = self.http.post(
                    self.config.base_url,
                    data={k: v.encode("utf-8") for k, v in fields.items()},
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl,
                )
                break
            except requests.RequestException as exc:
                logger.warning("网络异常（第 %d/%d 次）：%s", attempt, attempts, exc)
                if attempt >= attempts:
                    raise XToolsTransportError(f"请求失败：{exc}") from exc
                self._sleep(min(2.0 * attempt, 5.0))
        assert resp is not None

        if resp.status_code != 200:
            raise XToolsTransportError(
                f"HTTP {resp.status_code}: {resp.text[:300]}", status_code=resp.status_code, raw=resp.text
            )
        payload = self._parse_json(resp.text)
        self.last_response = payload
        if not _is_ok(payload.get("ok")):
            err = payload.get("err") or {}
            errno = _to_int(err.get("errno"))
            errmsg = str(err.get("errmsg") or payload.get("msg") or payload)
            if errno in SESSION_EXPIRED_ERRNOS:
                raise XToolsSessionExpired(errno, errmsg, cmd=cmd, raw=payload)
            if errno == LOGIN_THROTTLED_ERRNO:
                raise XToolsLoginThrottled(errno, errmsg, cmd=cmd, raw=payload)
            raise XToolsApiError(errno, errmsg, cmd=cmd, raw=payload)
        return payload

    def _post(self, cmd: str, param: JsonLike, upr: JsonLike, *, idempotent: bool = True) -> Dict[str, Any]:
        return self._send(self.build_request(cmd, param, upr), idempotent=idempotent)

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        text = text.lstrip("﻿ \r\n\t")
        try:
            return json.loads(text)
        except ValueError:
            # 兼容响应前后夹杂 PHP 提示信息的情况
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except ValueError:
                    pass
            raise XToolsTransportError("响应不是合法 JSON：" + text[:300], raw=text)

    # ------------------------------------------------------------------ 登录
    def login(self, *, force: bool = False) -> str:
        """登录并缓存 sid。非 force 时优先复用本地未过期的 sid。"""
        now = self._clock()
        if not force and self._sid and (now - self._sid_time) < self.config.sid_ttl:
            return self._sid

        wait = LOGIN_MIN_INTERVAL - (now - self._last_login)
        if wait > 0:
            logger.info("距上次登录不足 %.0f 秒，等待 %.1f 秒", LOGIN_MIN_INTERVAL, wait)
            self._sleep(wait)

        for attempt in (1, 2):
            fields = self.build_login_request()
            self._last_login = self._clock()
            try:
                payload = self._send(fields, idempotent=True)
            except XToolsLoginThrottled:
                if attempt == 1:
                    logger.info("登录被限频（30103），等待 %.0f 秒后重试", LOGIN_MIN_INTERVAL)
                    self._sleep(LOGIN_MIN_INTERVAL)
                    continue
                raise
            ret = payload.get("ret") or {}
            sid = ret.get("sid") if isinstance(ret, dict) else None
            if not sid:
                raise XToolsApiError(None, f"登录响应中没有 sid：{payload}", cmd="user.login", raw=payload)
            self._sid = sid
            self._sid_time = self._clock()
            self._save_sid_cache()
            logger.info("登录成功 com=%s part=%s sid=%s…", ret.get("com"), ret.get("part"), sid[:6])
            return sid
        raise XToolsApiError(None, "登录失败", cmd="user.login")  # pragma: no cover

    def ensure_sid(self) -> str:
        return self._sid if self._sid else self.login()

    # ------------------------------------------------------------------ 通用调用
    def call(self, cmd: str, param: JsonLike, *, idempotent: bool = True, raise_business: bool = True) -> Any:
        """携带 sid 调用任意 cmd，返回 payload["ret"]。

        * sid 失效（20101/20102）时自动重新登录并重试一次。
        * 写入类调用请传 idempotent=False：网络超时时不自动重发，避免重复写入。
        * ret.ok == 0 时抛出 XToolsBusinessError（raise_business=False 则原样返回）。
        """
        sid = self.ensure_sid()
        try:
            payload = self._post(cmd, param, {"sid": sid}, idempotent=idempotent)
        except XToolsSessionExpired:
            logger.info("sid 已失效，重新登录后重试 cmd=%s", cmd)
            sid = self.login(force=True)
            payload = self._post(cmd, param, {"sid": sid}, idempotent=idempotent)
        ret = payload.get("ret")
        if raise_business and isinstance(ret, dict) and "ok" in ret and not _is_ok(ret.get("ok")):
            dt = str(param.get("dt", "")) if isinstance(param, dict) else ""
            raise XToolsBusinessError(str(ret.get("msg") or ret), cmd=cmd, dt=dt, raw=payload)
        return ret

    # ---- api.output 读取
    def output(self, dt: str, **params: Any) -> List[Dict[str, Any]]:
        """读取一页数据（最多 100 条）。params 直接放入 param，如 lastid=0、id=10、lasttime="2026-01-01"。"""
        ret = self.call("api.output", {"dt": dt, **params})
        data = ret.get("data") if isinstance(ret, dict) else ret
        if data is None:
            return []
        if isinstance(data, dict):
            # 个别接口以 {"0": {...}, "1": {...}} 或单条对象返回
            values = list(data.values())
            if values and all(isinstance(v, dict) for v in values):
                return values
            return [data]
        return list(data)

    def output_one(self, dt: str, id: Union[int, str], **params: Any) -> Optional[Dict[str, Any]]:
        rows = self.output(dt, id=id, **params)
        return rows[0] if rows else None

    def iter_output(
        self,
        dt: str,
        *,
        lastid: int = 0,
        max_pages: Optional[int] = None,
        **params: Any,
    ) -> Iterator[Dict[str, Any]]:
        """按 lastid 逐页遍历各页记录。以 id 递增为前提；页内无 id 或 id 不再增长时停止。"""
        pages = 0
        while True:
            rows = self.output(dt, lastid=lastid, **params)
            if not rows:
                return
            yield from rows
            ids = [i for i in (_to_int(str(row.get("id", "")).strip() or None) for row in rows) if i is not None]
            if not ids:
                return
            new_lastid = max(ids)
            if new_lastid <= lastid:
                return
            lastid = new_lastid
            pages += 1
            if max_pages is not None and pages >= max_pages:
                return

    # ---- api.input / api.update / api.cmdact
    def input(self, dt: str, data: Dict[str, Any], *, extend: Optional[int] = None, **extra: Any) -> Dict[str, Any]:
        """写入（新建）。返回 ret，如 {"ok":1,"msg":"...","id":123}。"""
        param: Dict[str, Any] = {"dt": dt}
        if extend is not None:
            param["extend"] = extend
        param.update(extra)
        param["data"] = data
        return self.call("api.input", param, idempotent=False)

    def update(self, dt: str, data: Dict[str, Any], *, extend: Optional[int] = None, **extra: Any) -> Dict[str, Any]:
        """修改。data 中需含定位条件（id，或 sn / No. / number 等编号）以及待修改字段。"""
        param: Dict[str, Any] = {"dt": dt}
        if extend is not None:
            param["extend"] = extend
        param.update(extra)
        param["data"] = data
        return self.call("api.update", param, idempotent=False)

    def cmdact(self, dt: str, data: Dict[str, Any], *, act: Optional[str] = None) -> Dict[str, Any]:
        """动作类接口：data 中的 act 指定动作（如 libinok / liboutok / chgst / exc / erp_libn / kaipiao）。"""
        if act is not None:
            data = {**data, "act": act}
        return self.call("api.cmdact", {"dt": dt, "data": data}, idempotent=False)

    # ---- api.fieldinfo
    def fieldinfo(self, dt: str, **params: Any) -> Any:
        ret = self.call("api.fieldinfo", {"dt": dt, **params})
        return ret.get("data") if isinstance(ret, dict) else ret

    def dictionary(self, dt: str, field: str) -> List[Dict[str, Any]]:
        """数据字典：[{"key":"1","value":"1.售前跟踪","flag":"USE|Default|NO USE"}, ...]"""
        data = self.fieldinfo(dt, field=field)
        return list(data or [])

    def field_names(self, dt: str) -> Dict[str, str]:
        """字段英文名 → 中文名。"""
        data = self.fieldinfo(dt, act="dbcn")
        return dict(data or {})

    def users(self, *, part: Optional[str] = None, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """人员 part 与姓名对照；不传参数返回全体人员。"""
        params: Dict[str, Any] = {"act": "pr2nm"}
        if part:
            params["part"] = part
        if name:
            params["name"] = name
        data = self.fieldinfo("customer", **params)
        return list(data or [])

    # ---- api.chgown / api.downfile
    def chgown(
        self,
        owner: str,
        *,
        id: Optional[Union[int, str]] = None,
        sn: Optional[str] = None,
        dt: str = "customer",
    ) -> Dict[str, Any]:
        """客户转移：owner 可为业务员姓名或 part；id 与 sn 二选一。"""
        param: Dict[str, Any] = {"dt": dt}
        if id is not None:
            param["id"] = id
        if sn is not None:
            param["sn"] = sn
        param["owner"] = owner
        return self.call("api.chgown", param, idempotent=False)

    def downfile(self, dt: str, id: Union[int, str], *, field: Optional[str] = None) -> List[Dict[str, Any]]:
        """附件列表，url 有效期约 2 小时。"""
        param: Dict[str, Any] = {"dt": dt, "id": str(id)}
        if field:
            param["field"] = field
        ret = self.call("api.downfile", param)
        if isinstance(ret, dict):
            return list(ret.get("list") or ret.get("data") or [])
        return list(ret or [])
