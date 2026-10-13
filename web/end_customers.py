"""订单的最终客户（经代理商购买时的终端客户）。

CRM 的 OPEN API 不返回订单的“第二关联客户 / 分销商”字段，最终客户只能从两处得到：

1. 本地手工对照 data/end_customers.json（优先），热加载，不进镜像库、不进仓库：
   {"agents": [9139, ...],                       # CRM 里没标成代理商、但其实是代理商的客户 id
    "orders": [{"order": "mw2024030118286", "customer_id": 11219, "note": "..."}]}
   order 可为订单号或订单 id；customer_id 为 0 / null 表示“这张单就是下单客户自己用的”，用来压掉自动识别的误判。
2. 自动识别（认出的客户与下单客户不同、且能唯一对上一个 CRM 客户时才算）：
   * 备注里“终端客户 / 最终客户 / 终端用户 / 最终用户 / 终端：”后面写的单位名（所有订单）；
   * 收货地址里出现的客户名（只看代理商的订单：课题组、分公司的地址里本来就带着上级单位名）。
   客户名先去掉“-色谱柱 / -子账号”之类的后缀、括号、地名前缀与公司后缀，得到主干（≥ 4 字）再比对；
   高校、研究所、医院不去地名（“深圳职业技术学院”≠“威海职业技术学院”）；
   同一主干有多个档案时取不带后缀的主档，仍有多个则不认（留给手工对照）。

代理商：CRM 客户类型“代理商”、行业“代理商 批发零售 / 商业流通”、名称带“（代）”，或在 agents 名单里。
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

_REGION = ("上海市", "北京市", "天津市", "重庆市", "上海", "北京", "天津", "重庆", "江苏省", "江苏", "浙江省", "浙江", "广东省", "广东", "山东省", "山东", "四川省", "四川",
           "湖北省", "湖北", "湖南省", "湖南", "河南省", "河南", "河北省", "河北", "安徽省", "安徽", "福建省", "福建", "江西省", "江西", "辽宁省", "辽宁", "吉林省", "吉林",
           "黑龙江省", "黑龙江", "山西省", "山西", "陕西省", "陕西", "甘肃省", "甘肃", "云南省", "云南", "贵州省", "贵州", "海南省", "海南", "广西", "内蒙古", "宁夏", "新疆", "西藏", "青海省", "青海",
           "苏州市", "苏州", "南京市", "南京", "杭州市", "杭州", "无锡市", "无锡", "常州市", "常州", "成都市", "成都", "武汉市", "武汉", "广州市", "广州", "深圳市", "深圳",
           "连云港市", "连云港", "泰州市", "泰州", "南通市", "南通", "宁波市", "宁波", "青岛市", "青岛", "济南市", "济南", "西安市", "西安", "合肥市", "合肥", "长沙市", "长沙", "郑州市", "郑州")
_INSTITUTION = ("大学", "学院", "研究所", "研究院", "医院", "中心", "学校", "科学院")
_SUFFIXES = ("股份有限公司", "有限责任公司", "集团有限公司", "有限公司", "股份公司", "公司")
_TAIL = re.compile(r"\s*(?:[-－—–]+|子账|主账).*$")
_PAREN = re.compile(r"[（(][^）)]*[）)]")
_MARK = re.compile(r"(?:(?:终端客户|最终客户|终端用户|最终用户)\s*[:：为是]?|终端\s*[:：为是])\s*([^\s，,；;。()（）\r\n/、]{2,30})")
AGENT_TYPES = {"4"}            # customer.type 代理商
AGENT_INDUSTRIES = {"6", "7"}  # customer.industry 商业流通 / 代理商 批发零售


_GENERIC = re.compile("医药|药业|制药|产业|集团|生物|科技|技术|化学|化工|新材料|材料|实验|仪器|设备|发展|工业|研究|研发|中药|饮片|药检|检测|分析|色谱|"
                      "有限|机械|贸易|商贸|健康|医疗|器械|工程|环保|食品|药物|制剂|原料|中心|所|院|省|市|区|县")


def name_core(name: Any) -> str:
    """客户名主干：去后缀账号、括号、公司后缀与地名前缀（高校等除外）。"""
    s = _TAIL.sub("", str(name or "").strip())
    s = _PAREN.sub("", s).strip()
    for suf in _SUFFIXES:
        if s.endswith(suf) and len(s) - len(suf) >= 4:
            s = s[: -len(suf)]
            break
    if not s.endswith(_INSTITUTION):
        changed = True
        while changed:
            changed = False
            for r in _REGION:
                rest = s[len(r):]
                if s.startswith(r) and len(rest) >= 4 and rest[0] not in "省市区县":
                    s, changed = rest, True
                    break
    return s.strip()


def distinctive(core: str) -> bool:
    """主干去掉行业泛词后还剩至少 2 个字，才拿来在地址 / 备注里找（“医药产业”“中药饮片”不算）。"""
    return len(_GENERIC.sub("", core)) >= 2


def _is_main_account(name: str) -> bool:
    return not _TAIL.search(name or "")


def is_agent_record(c: Dict[str, Any]) -> bool:
    name = (c.get("cu_name") or "") + (c.get("m_name") or "")
    return (str(c.get("type") or "") in AGENT_TYPES or str(c.get("industry") or "") in AGENT_INDUSTRIES
            or "（代）" in name or "(代)" in name)


class EndCustomerIndex:
    """客户名主干 → 客户 id，用于从备注 / 地址里认出单位。"""

    def __init__(self, customers: Dict[int, Dict[str, Any]]):
        self.by_core: Dict[str, List[Tuple[int, str]]] = {}
        for cid, c in customers.items():
            full = (c.get("cu_name") or c.get("m_name") or "").strip()
            core = name_core(full)
            if len(core) >= 4 and distinctive(core):
                self.by_core.setdefault(core, []).append((cid, full))
        self._buckets: Dict[str, List[str]] = {}
        for core in sorted(self.by_core, key=len, reverse=True):   # 长主干优先
            self._buckets.setdefault(core[:2], []).append(core)

    def _pick(self, core: str) -> Optional[int]:
        cands = self.by_core.get(core) or []
        if len(cands) == 1:
            return cands[0][0]
        mains = [cid for cid, full in cands if _is_main_account(full)]
        return mains[0] if len(mains) == 1 else None

    def find(self, text: str) -> Optional[int]:
        """text 里出现的客户；出现多个不同客户或同名多档时返回 None。"""
        if not text:
            return None
        hits: List[str] = []
        for i in range(len(text) - 3):
            for core in self._buckets.get(text[i:i + 2], ()):
                if text.startswith(core, i) and not any(core in h for h in hits):
                    hits.append(core)
                    break
        ids = {self._pick(h) for h in hits}
        if len(ids) != 1 or None in ids:
            return None
        return ids.pop()

    def find_name(self, name: str) -> Optional[int]:
        """备注里写的单位名：主干相同，或名称里出现某个客户的主干（“皓元医药” ↔ “上海皓元医药股份有限公司”）。"""
        core = name_core(name)
        if len(core) < 4:
            return None
        if core in self.by_core:
            return self._pick(core)
        return self.find(name)


def from_memo(memo: Any) -> Optional[str]:
    m = _MARK.search(str(memo or ""))
    if not m:
        return None
    name = m.group(1).strip()
    if re.match(r"^(不带|不放|直发|发货|客户的?$|地址)", name):
        return None
    return name


class EndCustomerFile:
    """data/end_customers.json 手工对照与代理商名单，热加载。"""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._agents: Set[int] = set()
        self._sig: Optional[Tuple[int, int]] = None
        self._checked = 0.0

    def _load(self) -> None:
        try:
            st = os.stat(self.path)
            sig = (st.st_mtime_ns, st.st_size)
        except FileNotFoundError:
            self._orders, self._agents, self._sig = {}, set(), None
            return
        if sig == self._sig:
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (OSError, ValueError):
            raw = {}
        if isinstance(raw, list):
            raw = {"orders": raw}
        orders: Dict[str, Dict[str, Any]] = {}
        for r in raw.get("orders") or []:
            key = str((r or {}).get("order") or "").strip()
            if not key:
                continue
            cid = r.get("customer_id")
            try:
                cid = int(cid) if cid not in (None, "") else 0
            except (TypeError, ValueError):
                continue
            orders[key] = {"customer_id": cid, "note": str(r.get("note") or "")}
        agents = {int(x) for x in raw.get("agents") or [] if str(x).strip().isdigit()}
        self._orders, self._agents, self._sig = orders, agents, sig

    def refresh(self, force: bool = False) -> None:
        with self._lock:
            now = time.time()
            if force or now - self._checked > 2:
                self._checked = now
                self._load()

    def get(self, order_id: Any, order_no: Any) -> Optional[Dict[str, Any]]:
        return self._orders.get(str(order_no or "").strip()) or self._orders.get(str(order_id or "").strip())

    def agents(self) -> Set[int]:
        return set(self._agents)

    def signature(self) -> Any:
        try:
            st = os.stat(self.path)
        except FileNotFoundError:
            return None
        return (st.st_mtime_ns, st.st_size)


def build_map(customers: Dict[int, Dict[str, Any]], manual: EndCustomerFile, orders: Iterable[Dict[str, Any]],
              own_id: Callable[[Any], Optional[int]]) -> Tuple[Dict[int, Tuple[int, str]], Set[int]]:
    """订单 id → (最终客户 id, 来源)，以及代理商客户 id 集合。own_id(cu_sn) 把订单客户字段解析成客户 id。"""
    manual.refresh(force=True)
    index = EndCustomerIndex(customers)
    agents = {cid for cid, c in customers.items() if is_agent_record(c)} | manual.agents()
    out: Dict[int, Tuple[int, str]] = {}

    def other(cid: Optional[int], own: Optional[int]) -> bool:
        """认出的是另一家：不是下单客户本身、不是代理商，也不是下单客户名里带着的上级单位（课题组 / 子账号）。"""
        if not cid or cid == own or cid in agents:
            return False
        own_name = (customers.get(own) or {}).get("cu_name") or "" if own else ""
        return name_core((customers.get(cid) or {}).get("cu_name") or "") not in own_name

    for o in orders:
        own = own_id(o.get("cu_sn"))
        m = manual.get(o.get("id"), o.get("no_"))
        if m is not None:
            if m["customer_id"] and m["customer_id"] != own:
                out[int(o["id"])] = (m["customer_id"], "手工" + (f"：{m['note']}" if m["note"] else ""))
            continue
        name = from_memo(o.get("memo"))
        if name:
            cid = index.find_name(name)
            if other(cid, own):
                out[int(o["id"])] = (cid, f"备注：{name}")
                continue
        if own in agents:
            cid = index.find(str(o.get("addr") or ""))
            if other(cid, own):
                out[int(o["id"])] = (cid, "收货地址")
    return out, agents
