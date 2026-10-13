"""上市公司客户与股价。

* data/listed_companies.json（本机，热加载，不进仓库）：
  [{"name": "恒瑞医药", "code": "sh600276", "h_code": "hk01276", "patterns": ["恒瑞医药", "盛迪医药"], "ids": [], "exclude": [], "note": "..."}]
  匹配规则同客户集团（web/local.py CustomerGroups）：id 在 ids 里或客户名含 patterns 片段，exclude 除外，多条命中取第一条。
  code 为腾讯行情代码：sh / sz / bj + 6 位为 A 股，hk + 5 位为 H 股；A+H 两地上市的另填 h_code（可省）。
* 行情取自腾讯（qt.gtimg.cn 实时、web.ifzq.gtimg.cn 日 K），现价缓存 QUOTE_TTL 秒；
  年初价 = 上一年最后一个交易日收盘价（前复权，送转除权后与现价可比），按（代码, 年份）缓存在 data/stock_quotes.json。取不到时对应字段为 None，不影响页面。
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .local import CustomerGroups

logger = logging.getLogger(__name__)

QUOTE_TTL = 300
TIMEOUT = 4


def stock_markets(param: Any) -> List[str]:
    """销售分析 stock 参数 → 要显示的市场：缺省 / "1" / "a,h" = A、H 都显示；"a" / "h" 只显示一个；"0" = 都不显示。"""
    p = str(param if param is not None else "").strip().lower()
    if p in ("", "1", "on", "true", "a,h", "h,a", "ah"):
        return ["A", "H"]
    return [m for m in ("A", "H") if m.lower() in p.replace(" ", "").split(",")]


def market(code: str) -> str:
    """A（sh / sz / bj）或 H（hk）。"""
    return "H" if str(code).lower().startswith("hk") else "A"


class ListedCompanies(CustomerGroups):
    """客户 → 上市公司（简称、代码）。"""

    def _load(self) -> None:
        old = self._sig
        super()._load()
        if self._sig == old and hasattr(self, "_codes"):
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        except (OSError, ValueError):
            raw = []
        codes: Dict[str, List[str]] = {}
        for r in raw if isinstance(raw, list) else []:
            if isinstance(r, dict) and r.get("name") and r.get("code"):
                cs = [str(r.get(k) or "").strip().lower() for k in ("code", "h_code")]
                codes[str(r["name"]).strip()] = sorted({c for c in cs if c}, key=lambda c: (market(c) == "H", c))
        self._codes = codes

    def listed_of(self, cid: Any, name: Any) -> Optional[Dict[str, Any]]:
        """{"name": 简称, "code": 首个代码（有 A 股取 A 股）, "codes": [A 股代码, H 股代码]}。"""
        hit = self.group_of(cid, name)
        codes = getattr(self, "_codes", {}).get(hit or "")
        return {"name": hit, "code": codes[0], "codes": list(codes)} if hit and codes else None

    def signature(self) -> Any:
        self.refresh()
        return self._sig


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("gbk", "ignore")


def _num(s: Any) -> Optional[float]:
    try:
        v = float(s)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


class StockQuotes:
    """现价（内存缓存）与年初价（文件缓存）。get(codes) → {code: {price, prev_close, base, change_pct, time, currency}}。"""

    def __init__(self, path: Path, fetch=_get):
        self.path = Path(path)
        self._fetch = fetch
        self._lock = threading.Lock()
        self._now: Dict[str, Dict[str, Any]] = {}
        self._at = 0.0
        self._base: Dict[str, Optional[float]] = {}
        self._warming = False
        try:
            self._base = json.loads(self.path.read_text(encoding="utf-8")).get("base") or {}
        except (OSError, ValueError, AttributeError):
            self._base = {}

    def _refresh_now(self, codes: Iterable[str]) -> None:
        want = sorted(set(codes))
        for i in range(0, len(want), 60):
            part = want[i:i + 60]
            try:
                text = self._fetch("https://qt.gtimg.cn/q=" + ",".join(part))
            except Exception as e:   # 网络不通：保留旧缓存
                logger.warning("取股价失败：%s", e)
                return
            for line in text.split(";"):
                if '="' not in line:
                    continue
                key, val = line.strip().split('="', 1)
                code = key.replace("v_", "").strip()
                f = val.rstrip('"').split("~")
                if len(f) > 31:
                    self._now[code] = {"price": _num(f[3]), "prev_close": _num(f[4]), "time": f[30], "stock_name": f[1]}

    def _warm(self, codes: Iterable[str], year: int) -> None:
        """后台补年初价（每只一次请求，首次可能要几十秒，不卡页面）。"""
        todo = [c for c in codes if f"{c}:{year}:qfq" not in self._base]
        if not todo or self._warming:
            return
        self._warming = True

        def run() -> None:
            try:
                for c in todo:
                    self._year_base(c, year)
            finally:
                self._warming = False
        threading.Thread(target=run, daemon=True).start()

    def _year_base(self, code: str, year: int) -> Optional[float]:
        key = f"{code}:{year}:qfq"
        if key in self._base:
            return self._base[key]
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,{year - 1}-12-01,{year - 1}-12-31,40,qfq"
        try:
            data = json.loads(self._fetch(url)).get("data") or {}
        except Exception as e:
            logger.warning("取年初价失败 %s：%s", code, e)
            return None
        rows = (data.get(code) or {}).get("qfqday") or (data.get(code) or {}).get("day") or []
        base = _num(rows[-1][2]) if rows else None
        with self._lock:
            self._base[key] = base
            snapshot = dict(self._base)
        try:
            self.path.write_text(json.dumps({"base": snapshot}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        return base

    def get(self, codes: Iterable[str], today: Optional[dt.date] = None) -> Dict[str, Dict[str, Any]]:
        codes = {c for c in codes if c}
        if not codes:
            return {}
        year = (today or dt.date.today()).year
        with self._lock:
            missing = [c for c in codes if c not in self._now]
            if time.time() - self._at > QUOTE_TTL:
                self._refresh_now(set(self._now) | codes)
                self._at = time.time()
            elif missing:
                self._refresh_now(missing)
            for c in missing:
                self._now.setdefault(c, {})   # 代码无效 / 网络不通时不每次重取，等下一轮 TTL
            out = {}
            for c in codes:
                q = dict(self._now.get(c) or {})
                base = self._base.get(f"{c}:{year}:qfq")
                price = q.get("price") or q.get("prev_close")
                q.update({"base": base, "currency": "HKD" if c.startswith("hk") else "CNY",
                          "change_pct": round((price - base) / base * 100, 1) if price and base else None})
                out[c] = q
        self._warm(codes, year)
        return out
