"""本地前台服务：只读访问镜像库，提供 JSON API 与静态页面。

* 只监听 127.0.0.1；连接以 query_only 打开，不向镜像库写入。
* 每个请求独立连接（线程安全）；人员、字典、客户对照等小表缓存在内存，镜像更新后自动重载。
* 客户关联：业务表的 cu_sn 为 "[id:N]" 或客户编号 sn；出库单 cu_sn 为纯数字客户 id。
* 人员：contract.who / gathering_note.who 为姓名；customer.owner / gathering.who / libout.who 为 part；action.who 为 ",M1,M2," 形式。

接口（均为 GET，返回 JSON）：
    /api/meta                       同步状态、字典、人员、可选年份、产品分类、地区
    /api/overview?year=             经营总览
    /api/orders?...                 订单列表        /api/orders/<id>    订单详情
    /api/customers?...              客户列表        /api/customers/<id> 客户详情
    /api/receivables?...            计划回款（应收）
    /api/receipts?...               回款记录
    /api/actions?...                工作日志（行动记录）
    0.5 新增（实现见 web/reports.py）：
    /api/sales?by=&years=&ytd=      销售分析（维度 × 年份，可带 who / customer_id / prod / class / group / state / type 筛选下钻）
    /api/customer_analysis?year=    客户分析（ABC 分层、新客、留存 / 复购、流失预警、按所有者）
    /api/salesperson?who=&year=     业务员看板
    /api/products?...               产品与库存      /api/product?sn=    产品详情
    /api/purchases?...              采购单          /api/purchases/<id> 采购单详情
    /api/pay_plans?...              付款计划        /api/cashflow?months=  现金流对照
    /api/contacts?...               联系人查询
    /api/export/<kind>?...          导出 Excel（与列表接口同样的筛选参数；kind 见 web/export.py）
"""

from __future__ import annotations

import datetime as dt
import difflib
import json
import logging
import re
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, quote, urlparse

from sync.specs import CONTRACT_CUSTOM_FIELDS
from sync.store import col_name
from web.auth import AccessControl
from web.export import EXPORT_MAX, Download, build_export
from web.reports import CID_EXPR, ORDER_RMB_EXPR, PRODUCT_JOIN, ReportQueries, _num, display_city

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = logging.getLogger("xtools.web")

CANCELLED = "3"  # contract.status 意外中止：金额统计时剔除
# 工作日志查重：与同一客户此前若干条比对，找“套模板 / 复制粘贴”的痕迹
DUP_PEERS = 10          # 每条记录回看同客户此前多少条
DUP_SCAN = 60           # 每个客户最多取多少条参与比对
DUP_MIN_LEN = 12        # 正文短于这个长度不比（问候语之类）
DUP_BLOCK = 8           # 连续相同 ≥ 8 个字才算重复片段
DUP_DIFF_AT = 0.3       # 覆盖率到这个值才去定位具体片段（difflib 较慢）
DUP_ALERT = 0.7         # 覆盖率 ≥ 70% 视为高度雷同，前台标红
DUP_TEXT_MAX = 240      # 返回的历史正文截断长度
DUP_SCAN_MAX = 2000     # “只看高相似”时，在当前筛选范围内最多扫描多少条
_DUP_STRIP = re.compile(r"[\s，。、；：（）()【】\[\]“”\"'’‘!！?？,.:;~·\-—…]+")


def _shingles(text: str, n: int = 4) -> set:
    """按 n 字滑窗切片，用交集比例衡量重复程度（比整串相似度更能抓住“大段照搬”）。"""
    t = _DUP_STRIP.sub("", text or "")
    if len(t) < n:
        return {t} if t else set()
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def _merge_spans(spans: List[Tuple[int, int]]) -> List[List[int]]:
    """把重复片段的 [起点, 长度] 合并成互不重叠、按位置排好的区间。"""
    out: List[List[int]] = []
    for start, size in sorted(spans):
        if out and start <= out[-1][0] + out[-1][1]:
            out[-1][1] = max(out[-1][1], start + size - out[-1][0])
        else:
            out.append([start, size])
    return out
OPEN_PLAN = ("2", "4")  # gathering.status 未回 / 部分回款
SEVERE_DAYS = 90        # 未回款计划逾期超过这么多天，客户标“严重逾期”（Richard 口径）
ORDER_KINDS = {"sample": "", "media": "色谱介质", "column": "色谱柱"}   # 订单页销售类型按钮：免费样品（金额 0）/ 填料（大类含“色谱介质”）/ 色谱柱
ACTION_RECORD = "3"     # action.cale 记录（日程 1 / 待办 2、4 是计划，不算拜访）
VISIT_TYPES = ("2", "3")  # action.type 市内拜访 / 市外拜访
VISIT_WINDOW = 365      # “近一年”的天数
# 2023 年以前的行动记录大多没填类型（type=0），按正文开头判断是否上门：先剥掉日期 / 时间 / 序号等引子，
# 首个分句里出现拜访类词算上门，但以电话 / 微信 / 预约 / 计划等开头的不算（“电话拜访”“约定下周拜访”是联系或计划，不是上门）
_VISIT_LEAD = re.compile(r"^[\s\d０-９.、,，:：()（）\-—/~]*(?:今天|今日|上午|下午|早上|中午|晚上|昨天|昨日|前天|本周|这周|上周|周[一二三四五六日天]|星期[一二三四五六日天]"
                         r"|\d{1,2}月\d{1,2}[日号]?|\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}|[\d.]+[日号])*[\s,，、:：]*")
_VISIT_WORDS = re.compile(r"^(?:去|到|赴|前往|再次|再|又|和|与|同|陪同?|带|跟)?[^，。；！？,;!?\n]{0,10}?(拜访|上门|现场|走访|登门|面谈|见面|拜见|参观)")
_VISIT_NOT = re.compile(r"^(?:[^，。；！？,;!?\n]{0,6})?(电话|微信|QQ|邮件|短信|网上|致电|来电|视频|线上|约|预约|计划|准备|打算|下次|下周|下月|明天|后天|近期|快递|寄|发|询|回复|联系|沟通|跟进|催|报价|开票)")


def is_visit(a_type: Any, subject: Any, content: Any) -> bool:
    """一条行动记录是否上门拜访：类型为市内 / 市外拜访；没填类型的按正文开头判断（见 _VISIT_WORDS / _VISIT_NOT）。"""
    t = str(a_type or "").strip()
    if t in VISIT_TYPES:
        return True
    if t not in ("", "0"):
        return False
    text = _VISIT_LEAD.sub("", str(content or subject or "").strip(), count=1)
    return bool(_VISIT_WORDS.search(text)) and not _VISIT_NOT.search(text)


DICT_FIELDS = {
    "contract": ["status", "type", "confirm", "st_send", "pay_mode", "payment", *CONTRACT_CUSTOM_FIELDS],
    "gathering": ["status"],
    "gathering_note": ["type", "ctype", "invoice"],
    "action": ["type", "cale"],
    "customer": ["life", "type", "cu_status", "cu_from", "industry", "rala_rating", "employees", "state"],
    "sendgoods": ["status", "sntype"],
    "contact": ["contype"],
    "purchase": ["type", "status0", "status", "confirm"],
    "pay_plan": ["status", "type", "ctype"],
    "product": ["status", "pmode"],
}
# 订单自定义字段中在列表 / 详情里重点展示的几项（正式公司字段名：j7 发票类型、j8 付款方式、j9 货期、j21 是否试用、j26 是否首单签约、j33 提成方案）
ORDER_TERMS = [("j7", "invoice_type"), ("j8", "pay_terms"), ("j9", "lead_time"), ("j21", "trial"), ("j26", "first_sign"), ("j33", "commission_plan")]
_ID_KEY = re.compile(r"^\[id:(\d+)\]$")
_MULTI = re.compile(r"^,(?:[^,]+,)+$")  # 多选字段 ",1,2,"

# 客户表 state 为 XTools 内部省份代码，字典未抓取时按该代码下最常见的城市 / 区推断省份
CITY_PROVINCE = {
    "北京市": "北京", "天津市": "天津", "上海市": "上海", "重庆市": "重庆", "石家庄市": "河北", "唐山市": "河北", "保定市": "河北", "太原市": "山西", "呼和浩特市": "内蒙古",
    "沈阳市": "辽宁", "大连市": "辽宁", "长春市": "吉林", "哈尔滨市": "黑龙江", "南京市": "江苏", "苏州市": "江苏", "无锡市": "江苏", "常州市": "江苏", "南通市": "江苏", "连云港市": "江苏", "泰州市": "江苏", "扬州市": "江苏",
    "杭州市": "浙江", "宁波市": "浙江", "温州市": "浙江", "绍兴市": "浙江", "台州市": "浙江", "湖州市": "浙江", "嘉兴市": "浙江", "金华市": "浙江",
    "合肥市": "安徽", "福州市": "福建", "厦门市": "福建", "南昌市": "江西", "济南市": "山东", "青岛市": "山东", "烟台市": "山东", "淄博市": "山东", "潍坊市": "山东", "临沂市": "山东", "德州市": "山东",
    "郑州市": "河南", "武汉市": "湖北", "长沙市": "湖南", "广州市": "广东", "深圳市": "广东", "珠海市": "广东", "佛山市": "广东", "东莞市": "广东", "中山市": "广东", "南宁市": "广西", "海口市": "海南",
    "成都市": "四川", "贵阳市": "贵州", "昆明市": "云南", "拉萨市": "西藏", "西安市": "陕西", "兰州市": "甘肃", "西宁市": "青海", "银川市": "宁夏", "乌鲁木齐市": "新疆", "香港": "香港", "澳门": "澳门", "台北市": "台湾",
}
DISTRICT_PROVINCE = {
    "朝阳区": "北京", "海淀区": "北京", "昌平区": "北京", "大兴区": "北京", "丰台区": "北京", "通州区": "北京", "东城区": "北京", "西城区": "北京", "顺义区": "北京", "房山区": "北京", "石景山区": "北京",
    "浦东新区": "上海", "金山区": "上海", "闵行区": "上海", "松江区": "上海", "嘉定区": "上海", "奉贤区": "上海", "徐汇区": "上海", "杨浦区": "上海", "静安区": "上海", "青浦区": "上海", "宝山区": "上海", "长宁区": "上海", "普陀区": "上海", "虹口区": "上海", "黄浦区": "上海",
    "和平区": "天津", "南开区": "天津", "河西区": "天津", "河东区": "天津", "河北区": "天津", "滨海新区": "天津", "西青区": "天津", "津南区": "天津", "北辰区": "天津", "东丽区": "天津", "武清区": "天津",
    "渝中区": "重庆", "江北区": "重庆", "沙坪坝区": "重庆", "九龙坡区": "重庆", "渝北区": "重庆", "南岸区": "重庆", "巴南区": "重庆", "北碚区": "重庆", "大渡口区": "重庆", "两江新区": "重庆",
}


def money(value: Any) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(value: Any) -> bool:
    """形如 YYYY-MM-DD（不判断年份是否合理；年份异常由 Query.date_flag 标记）。"""
    return isinstance(value, str) and bool(_DATE_RE.match(value))


class Lookups:
    """内存中的小表：人员、字典、客户对照、产品、字段中文名。"""

    def __init__(self, conn: sqlite3.Connection):
        self.users: Dict[str, Dict[str, Any]] = {}
        for r in conn.execute("SELECT part, name, status, dept FROM crm_user WHERE _deleted_at IS NULL ORDER BY id"):
            self.users[r["part"]] = {"part": r["part"], "name": r["name"] or r["part"], "active": str(r["status"]) == "0", "dept": r["dept"]}
        self.dicts: Dict[Tuple[str, str], Dict[str, str]] = {}
        for r in conn.execute("SELECT dt, field, key, value FROM dictionaries WHERE dt <> 'user'"):
            self.dicts.setdefault((r["dt"], r["field"]), {})[str(r["key"])] = r["value"] or ""
        self.field_names: Dict[str, Dict[str, str]] = {}
        for r in conn.execute("SELECT dt, field, name FROM field_names"):
            self.field_names.setdefault(r["dt"], {})[r["field"]] = r["name"] or ""
        self.name_to_part: Dict[str, str] = {u["name"]: part for part, u in self.users.items()}
        self.customers: Dict[int, Dict[str, Any]] = {}
        self.key_to_id: Dict[str, int] = {}
        for r in conn.execute("SELECT id, sn, cu_name, m_name, owner, life, type, cu_status, city, state, district, address FROM customer WHERE _deleted_at IS NULL"):
            self.customers[r["id"]] = dict(r)
            if r["sn"]:
                self.key_to_id[r["sn"]] = r["id"]
        self.products: Dict[str, Dict[str, Any]] = {}  # 按编号 sn（非空）
        self.products_by_id: Dict[int, Dict[str, Any]] = {}  # 按 id（含没有编号的产品，明细里以 "[id:N]" 引用）
        for r in conn.execute("SELECT id, sn, name, model, unit, class FROM product WHERE _deleted_at IS NULL"):
            d = dict(r)
            self.products_by_id[d["id"]] = d
            if d["sn"]:
                self.products[d["sn"]] = d
        self.salespeople: List[Dict[str, Any]] = [
            {"name": r["who"], "orders": r["n"], "part": self.name_to_part.get(r["who"])}
            for r in conn.execute("SELECT who, COUNT(*) n FROM contract WHERE _deleted_at IS NULL AND who <> '' GROUP BY who ORDER BY n DESC")
        ]
        # 每个客户的未回款计划（未回 / 部分回款，按计划日期），用于“严重逾期”标记：逾期天数在取用时按当天算，不随对照表缓存过期
        self.open_plans: Dict[int, List[Tuple[str, float]]] = {}
        for r in conn.execute(f"SELECT cu_sn, date, money FROM gathering WHERE _deleted_at IS NULL AND status IN ({','.join(repr(x) for x in OPEN_PLAN)}) AND date LIKE '____-__-__'"):
            cid = self.customer_id(r["cu_sn"])
            if cid is not None:
                self.open_plans.setdefault(cid, []).append((r["date"], _num(r["money"])))
        # 每个客户的行动记录（只取「记录」且日期合法的）：(日期, 是否上门)，按日期排好，用于客户页“拜访频度”；近一年 / 天数在取用时按当天算
        self.visit_log: Dict[int, List[Tuple[str, bool]]] = {}
        for r in conn.execute("SELECT cu_sn, type, subject, content, date FROM action WHERE _deleted_at IS NULL AND cale = ? AND date LIKE '____-__-__'", [ACTION_RECORD]):
            cid = self.customer_id(r["cu_sn"])
            if cid is not None:
                self.visit_log.setdefault(cid, []).append((r["date"], is_visit(r["type"], r["subject"], r["content"])))
        for log in self.visit_log.values():
            log.sort()
        self._load_product_classes(conn)
        self._load_states()
        self.loaded_at = time.time()

    # ---- 产品分类树：product.class 存的是分类标题；product_class（csstree）为 id / title / upid 树，根为“产品类别”
    def _load_product_classes(self, conn: sqlite3.Connection) -> None:
        nodes: Dict[int, Tuple[str, int]] = {}
        try:
            for r in conn.execute("SELECT id, title, upid FROM product_class WHERE _deleted_at IS NULL ORDER BY id"):
                nodes[int(r["id"])] = ((r["title"] or "").strip(), _int(r["upid"], 0))
        except sqlite3.Error:
            nodes = {}
        roots = {nid for nid, (_, up) in nodes.items() if up == 0 or up not in nodes}
        self.class_to_group: Dict[str, str] = {}
        self.group_titles: List[str] = []
        for nid, (title, up) in nodes.items():
            if up in roots and title and title not in self.group_titles:
                self.group_titles.append(title)
        self.group_titles.sort()
        for nid, (title, up) in nodes.items():
            if not title or title in self.class_to_group:
                continue
            cur, depth = nid, 0
            group = ""
            while cur in nodes and depth < 20:
                t, parent = nodes[cur]
                if parent in roots:
                    group = t
                    break
                cur, depth = parent, depth + 1
            self.class_to_group[title] = group or title
        counts: Dict[str, int] = {}
        for p in self.products_by_id.values():
            counts[p.get("class") or ""] = counts.get(p.get("class") or "", 0) + 1
        self.product_classes: List[Dict[str, Any]] = sorted(
            [{"title": t, "group": self.class_group(t), "count": n} for t, n in counts.items() if t], key=lambda x: (x["group"], -x["count"], x["title"]))

    def product(self, key: Any) -> Optional[Dict[str, Any]]:
        """明细里的产品引用 → 产品：编号 sn、"[id:N]"、"#N"（本地汇总键）或纯数字 id。"""
        if key is None or key == "":
            return None
        key = str(key).strip()
        m = _ID_KEY.match(key)
        if m:
            return self.products_by_id.get(int(m.group(1)))
        if key.startswith("#") and key[1:].isdigit():
            return self.products_by_id.get(int(key[1:]))
        p = self.products.get(key)
        if p is None and key.isdigit():
            return self.products_by_id.get(int(key))
        return p

    def class_group(self, title: Any) -> str:
        title = (title or "").strip() if isinstance(title, str) else ""
        if not title:
            return "（未分类）"
        return self.class_to_group.get(title, title)

    def classes_in_group(self, group: str) -> List[str]:
        return [c["title"] for c in self.product_classes if c["group"] == group]

    def classes_matching_group(self, keyword: str) -> List[str]:
        """大类名里含关键字（如“色谱柱”匹配“1.色谱柱”）的全部分类标题。"""
        return [c["title"] for c in self.product_classes if keyword in (c["group"] or "")]

    # ---- 省份：字典 customer.state 优先，否则按该代码下最常见的城市 / 区推断
    def _load_states(self) -> None:
        cities: Dict[str, Dict[str, int]] = {}
        districts: Dict[str, Dict[str, int]] = {}
        for c in self.customers.values():
            code = str(c.get("state") or "0")
            city = (c.get("city") or "").strip()
            if city:
                cities.setdefault(code, {})[city] = cities.setdefault(code, {}).get(city, 0) + 1
            district = (c.get("district") or "").strip()
            if district:
                districts.setdefault(code, {})[district] = districts.setdefault(code, {}).get(district, 0) + 1
        self.state_names: Dict[str, str] = {}
        self.state_city_text: Dict[str, str] = {}
        codes = set(cities) | set(districts) | {str(c.get("state") or "0") for c in self.customers.values()}
        for code in codes:
            top = sorted(cities.get(code, {}).items(), key=lambda kv: -kv[1])
            self.state_city_text[code] = "、".join(city for city, _ in top[:3])
            name = self.dicts.get(("customer", "state"), {}).get(code)
            if code in ("0", ""):
                name = "（未填地区）"
            if not name:
                for city, _ in top:
                    if city in CITY_PROVINCE:
                        name = CITY_PROVINCE[city]
                        break
            if not name:
                for district, _ in sorted(districts.get(code, {}).items(), key=lambda kv: -kv[1]):
                    if district in DISTRICT_PROVINCE:
                        name = DISTRICT_PROVINCE[district]
                        break
            self.state_names[code] = name or ("（未填地区）" if code in ("0", "") else f"地区 {code}")

    def state_name(self, code: Any) -> str:
        code = str(code or "0")
        return self.state_names.get(code) or self.dicts.get(("customer", "state"), {}).get(code) or (f"地区 {code}" if code not in ("0", "") else "（未填地区）")

    def state_cities(self, code: Any) -> str:
        return self.state_city_text.get(str(code or "0"), "")

    def states(self) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for c in self.customers.values():
            code = str(c.get("state") or "0")
            counts[code] = counts.get(code, 0) + 1
        return [{"key": code, "name": self.state_name(code), "cities": self.state_cities(code), "count": n} for code, n in sorted(counts.items(), key=lambda kv: -kv[1])]

    def supplier(self, cu_id: Any) -> Optional[Dict[str, Any]]:
        """采购单 / 付款计划的供应商（客户表 id）。"""
        cid = _int(cu_id, 0)
        if not cid:
            return None
        return self.customer(f"[id:{cid}]")

    def has_dict(self, dt_name: str, field: str) -> bool:
        return bool(self.dicts.get((dt_name, field)))

    def text_known(self, dt_name: str, field: str, key: Any) -> str:
        """字典里有才翻译；没有字典或代码未知时返回空串（用于代码本身没有意义的字段）。"""
        if key is None or key == "":
            return ""
        return self.dicts.get((dt_name, field), {}).get(str(key), "")

    def text_or(self, dt_name: str, field: str, key: Any, fallback: Dict[str, str]) -> str:
        """字典优先；字典未抓取时用内置对照；都没有则显示原始代码。"""
        if key is None or key == "":
            return ""
        d = self.dicts.get((dt_name, field))
        if d:
            return d.get(str(key), str(key))
        return fallback.get(str(key), f"状态 {key}")

    def decode(self, dt_name: str, field: str, value: Any) -> str:
        """按字典解码字段值；多选 ",1,2," 逐项解码；没有字典时原样返回。"""
        if value is None or value == "":
            return ""
        d = self.dicts.get((dt_name, field))
        s = str(value)
        if not d:
            return s
        if _MULTI.match(s):
            return "、".join(d.get(k, k) for k in s.strip(",").split(",") if k)
        return d.get(s, s)

    # ---- 解析
    def customer_id(self, key: Any, numeric_is_id: bool = False) -> Optional[int]:
        if not key:
            return None
        key = str(key).strip()
        m = _ID_KEY.match(key)
        if m:
            return int(m.group(1))
        if numeric_is_id and key.isdigit():
            return int(key)
        return self.key_to_id.get(key)

    def severe(self, cid: Any, today: Optional[dt.date] = None) -> Optional[Dict[str, Any]]:
        """客户是否“严重逾期”：名下有逾期超过 SEVERE_DAYS 天的未回款计划。返回 {days 最久逾期天数, amount 这些期的金额, count 期数, since 最早计划日期}，否则 None。"""
        plans = self.open_plans.get(_int(cid, 0)) if cid is not None else None
        if not plans:
            return None
        today = today or dt.date.today()
        hits = []
        for date, amount in plans:
            try:
                days = (today - dt.date.fromisoformat(date)).days
            except ValueError:
                continue
            if days > SEVERE_DAYS:
                hits.append((days, amount, date))
        if not hits:
            return None
        return {"days": max(h[0] for h in hits), "amount": round(sum(h[1] for h in hits), 2), "count": len(hits), "since": min(h[2] for h in hits)}

    def visit_stats(self, cid: Any, today: Optional[dt.date] = None) -> Optional[Dict[str, Any]]:
        """客户的拜访频度：近一年上门次数、上次上门日期与距今天数、累计上门次数、近一年其他联系（电话 / 微信等）次数、日志总条数。
        只算日期不晚于今天的「记录」；没有任何日志返回 None。"""
        log = self.visit_log.get(_int(cid, 0)) if cid is not None else None
        if not log:
            return None
        today = today or dt.date.today()
        today_s, since = today.isoformat(), (today - dt.timedelta(days=VISIT_WINDOW)).isoformat()
        visits = [d for d, v in log if v and d <= today_s]
        others = [d for d, v in log if not v and d <= today_s]
        if not visits and not others:
            return None
        last = visits[-1] if visits else None
        return {
            "visits": len(visits), "visits_12m": sum(1 for d in visits if d > since), "last_visit": last,
            "days_since": (today - dt.date.fromisoformat(last)).days if last else None,
            "contacts_12m": sum(1 for d in others if d > since), "logs": len(visits) + len(others),
            "last_log": max(visits[-1] if visits else "", others[-1] if others else "") or None,
        }

    def visit_key(self, cid: Any) -> float:
        """客户页按“拜访频度”排序用的数值键（注册为 SQL 函数）：近一年上门次数 × 10000 + 上次上门的新近度（9999 − 距今天数）；
        超一年没上门的只剩新近度（0 ～ 9633）；有日志但从未上门 −1；没有日志 −2。降序 = 拜访最勤的在前，升序 = 最久没去的在前。按天缓存。"""
        today = dt.date.today()
        cache = getattr(self, "_visit_keys", None)
        if cache is None or cache[0] != today:
            keys: Dict[int, float] = {}
            for c in self.visit_log:
                v = self.visit_stats(c, today)
                if not v:
                    keys[c] = -2.0
                elif not v["visits"]:
                    keys[c] = -1.0
                else:
                    keys[c] = v["visits_12m"] * 10000.0 + max(0, 9999 - (v["days_since"] or 0))
            cache = (today, keys)
            self._visit_keys = cache
        return cache[1].get(_int(cid, 0), -2.0)

    def customer(self, key: Any, numeric_is_id: bool = False) -> Optional[Dict[str, Any]]:
        cid = self.customer_id(key, numeric_is_id)
        if cid is None:
            return {"id": None, "name": str(key), "owner": None} if key else None
        c = self.customers.get(cid)
        if not c:
            return {"id": cid, "name": f"[已删除 {cid}]", "owner": None}
        return {"id": cid, "name": c["cu_name"] or c["m_name"] or f"[id:{cid}]", "owner": self.user_name(c["owner"]), "life": self.text("customer", "life", c["life"]),
                "severe": self.severe(cid)}

    def user_name(self, part: Any) -> str:
        if part is None:
            return ""
        part = str(part).strip()
        u = self.users.get(part)
        return u["name"] if u else part

    def names_from_codes(self, value: Any) -> List[str]:
        """action.who：",M1,M2," → 姓名列表；单个 part 或姓名也兼容。"""
        if not value:
            return []
        parts = [p for p in str(value).split(",") if p.strip()]
        return [self.user_name(p) for p in parts] or [str(value)]

    def text(self, dt_name: str, field: str, key: Any) -> str:
        if key is None or key == "":
            return ""
        return self.dicts.get((dt_name, field), {}).get(str(key), str(key))

    def part_to_name(self, part: str) -> str:
        return self.user_name(part)

    def dict_options(self) -> Dict[str, List[Dict[str, str]]]:
        out: Dict[str, List[Dict[str, str]]] = {}
        for dt_name, fields in DICT_FIELDS.items():
            for f in fields:
                items = self.dicts.get((dt_name, f), {})
                out[f"{dt_name}.{f}"] = [{"key": k, "value": v} for k, v in items.items()]
        return out


class Mirror:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._lookups: Optional[Lookups] = None
        self._stamp: Any = None
        self._checked = 0.0

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = 1")
        return conn

    def stamp(self, conn: sqlite3.Connection) -> Any:
        row = conn.execute("SELECT MAX(last_run_at), SUM(total_rows) FROM sync_state").fetchone()
        return (row[0], row[1]) if row else None

    def lookups(self, conn: sqlite3.Connection) -> Lookups:
        with self._lock:
            now = time.time()
            if self._lookups is None or now - self._checked > 20:
                self._checked = now
                stamp = self.stamp(conn)
                if self._lookups is None or stamp != self._stamp:
                    t0 = time.time()
                    self._lookups = Lookups(conn)
                    self._stamp = stamp
                    logger.info("已加载对照表：客户 %d、人员 %d、产品 %d（%.2fs）", len(self._lookups.customers), len(self._lookups.users),
                                len(self._lookups.products), time.time() - t0)
            return self._lookups


# ---------------------------------------------------------------------- 查询
class Query(ReportQueries):
    max_size = 500  # 导出时放大到 EXPORT_MAX

    def __init__(self, conn: sqlite3.Connection, lk: Lookups, params: Dict[str, str]):
        self.conn = conn
        self.lk = lk
        self.p = params
        self.today = dt.date.today()

    # ---- 参数
    def get(self, name: str, default: str = "") -> str:
        return (self.p.get(name) or default).strip()

    def page(self) -> Tuple[int, int, int]:
        size = min(max(_int(self.get("size"), 50), 1), self.max_size)
        page = max(_int(self.get("page"), 1), 1)
        return page, size, (page - 1) * size

    def customer_keys(self, cid: int) -> List[str]:
        keys = [f"[id:{cid}]"]
        c = self.lk.customers.get(cid)
        if c and c.get("sn"):
            keys.append(c["sn"])
        return keys

    def customer_clause(self, alias: str, clauses: List[str], args: List[Any], numeric_is_id: bool = False) -> None:
        cid = _int(self.get("customer_id"), 0)
        if cid:
            keys = [str(cid)] if numeric_is_id else self.customer_keys(cid)
            clauses.append(f"{alias}.cu_sn IN ({','.join('?' * len(keys))})")
            args.extend(keys)

    def name_search_clause(self, alias: str, q: str, args: List[Any]) -> str:
        like = f"%{q}%"
        args.extend([like, like, like, like])
        return (f"({alias}.cu_sn IN (SELECT '[id:' || id || ']' FROM customer WHERE cu_name LIKE ? OR m_name LIKE ?) "
                f"OR {alias}.cu_sn IN (SELECT sn FROM customer WHERE sn <> '' AND (cu_name LIKE ? OR m_name LIKE ?)))")

    def date_clause(self, alias: str, clauses: List[str], args: List[Any], col: str = "date") -> None:
        if self.get("from"):
            clauses.append(f"{alias}.{col} >= ?")
            args.append(self.get("from"))
        if self.get("to"):
            clauses.append(f"{alias}.{col} <= ?")
            args.append(self.get("to"))

    def rows(self, sql: str, args: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(sql, tuple(args))]

    def one(self, sql: str, args: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
        r = self.conn.execute(sql, tuple(args)).fetchone()
        return dict(r) if r else None

    # ---- 元数据
    def meta(self) -> Dict[str, Any]:
        states = self.rows("SELECT dt, total_rows, last_run_at, last_status, last_full_at, last_error FROM sync_state ORDER BY total_rows DESC")
        years = self.one("SELECT MIN(substr(date,1,4)) y0, MAX(substr(date,1,4)) y1 FROM contract WHERE _deleted_at IS NULL AND date LIKE '20__-__-__'") or {}
        y0, y1 = _int(years.get("y0"), self.today.year), _int(years.get("y1"), self.today.year)
        names = self.lk.field_names.get("contract", {})
        return {
            "today": self.today.isoformat(),
            "synced_at": max([s["last_run_at"] or "" for s in states] or [""]),
            "tables": states,
            "years": list(range(max(y0, 2000), max(y1, self.today.year) + 1))[::-1],
            "dicts": self.lk.dict_options(),
            "users": sorted(self.lk.users.values(), key=lambda u: (not u["active"], u["name"])),
            "salespeople": self.lk.salespeople,
            "product_groups": self.lk.group_titles,
            "product_classes": self.lk.product_classes,
            "product_statuses": [r["status"] for r in self.rows("SELECT status, COUNT(*) n FROM product WHERE _deleted_at IS NULL AND status <> '' GROUP BY status ORDER BY n DESC")],
            "states": self.lk.states(),
            "order_terms": [{"key": k, "field": f, "name": names.get(k) or k, "has_dict": self.lk.has_dict("contract", k)} for k, f in ORDER_TERMS],
            "libs": [{"key": r["lib"], "count": r["n"]} for r in self.rows("SELECT lib, COUNT(*) n FROM purchase WHERE _deleted_at IS NULL AND lib <> '' GROUP BY lib ORDER BY n DESC")],
        }

    # ---- 总览
    def overview(self) -> Dict[str, Any]:
        year = _int(self.get("year"), self.today.year)
        y_from, y_to = f"{year}-01-01", f"{year + 1}-01-01"
        py_from = f"{year - 1}-01-01"
        base = "FROM contract o WHERE o._deleted_at IS NULL AND o.status <> ?"
        month = self.today.strftime("%Y-%m")
        ytd_to = self.today.isoformat()
        ytd_prev_to = self.today.replace(year=self.today.year - 1).isoformat() if not (self.today.month == 2 and self.today.day == 29) else f"{self.today.year - 1}-02-28"

        def agg(sql: str, args: Sequence[Any]) -> Dict[str, Any]:
            r = self.one(sql, args) or {}
            return {"count": r.get("n") or 0, "amount": money(r.get("a"))}

        kpi = {
            "month_orders": agg(f"SELECT COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND substr(o.date,1,7) = ?", [CANCELLED, month]),
            "ytd_orders": agg(f"SELECT COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date <= ?", [CANCELLED, f"{self.today.year}-01-01", ytd_to]),
            "ytd_orders_prev": agg(f"SELECT COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date <= ?", [CANCELLED, f"{self.today.year - 1}-01-01", ytd_prev_to]),
            "month_receipts": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND substr(date,1,7) = ?", [month]),
            "ytd_receipts": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? AND date <= ?", [f"{self.today.year}-01-01", ytd_to]),
            "ytd_receipts_prev": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? AND date <= ?", [f"{self.today.year - 1}-01-01", ytd_prev_to]),
            "open_orders": agg("SELECT COUNT(*) n, SUM(CAST(sum AS REAL)) a FROM contract WHERE _deleted_at IS NULL AND status = '1'", []),
            "open_plans": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering WHERE _deleted_at IS NULL AND status IN ('2','4')", []),
            "overdue_plans": agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering WHERE _deleted_at IS NULL AND status IN ('2','4') AND date < ?", [ytd_to]),
        }
        monthly: Dict[str, Dict[str, Any]] = {}
        for r in self.rows(f"SELECT substr(o.date,1,7) m, COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date < ? GROUP BY m", [CANCELLED, py_from, y_to]):
            monthly.setdefault(r["m"], {})["orders"] = {"count": r["n"], "amount": money(r["a"])}
        for r in self.rows("SELECT substr(date,1,7) m, COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? AND date < ? GROUP BY m", [py_from, y_to]):
            monthly.setdefault(r["m"], {})["receipts"] = {"count": r["n"], "amount": money(r["a"])}
        series = []
        for yy in (year - 1, year):
            for mm in range(1, 13):
                key = f"{yy}-{mm:02d}"
                d = monthly.get(key, {})
                series.append({"month": key, "orders": d.get("orders", {"count": 0, "amount": 0.0}), "receipts": d.get("receipts", {"count": 0, "amount": 0.0})})
        top_customers = [
            {"customer": self.lk.customer(r["cu_sn"]), "count": r["n"], "amount": money(r["a"])}
            for r in self.rows(f"SELECT o.cu_sn, COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date < ? GROUP BY o.cu_sn ORDER BY a DESC LIMIT 10", [CANCELLED, y_from, y_to])
        ]
        top_sales = [
            {"name": r["who"], "count": r["n"], "amount": money(r["a"])}
            for r in self.rows(f"SELECT o.who, COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date < ? GROUP BY o.who ORDER BY a DESC LIMIT 10", [CANCELLED, y_from, y_to])
        ]
        top_products = [      # 按型号（product.name）合并各批号
            {"model_name": r["k"], "name": r["k"], "class": r["pcls"] or "", "batches": r["batches"] or 0,
             "amount": money(r["a"]), "quantity": r["q"], "orders": r["n"]}
            for r in self.rows(
                "SELECT COALESCE(NULLIF(p.name, ''), NULLIF(g.prod_name, ''), g.prod) k, MAX(COALESCE(p.class, '')) pcls, COUNT(DISTINCT g.prod) batches, "
                "SUM(CAST(g.sum AS REAL)) a, SUM(CAST(g.amount AS REAL)) q, COUNT(DISTINCT g.contract_id) n "
                f"FROM contract_goods g JOIN contract o ON o.id = g.contract_id {PRODUCT_JOIN} "
                "WHERE o._deleted_at IS NULL AND o.status <> ? AND o.date >= ? AND o.date < ? GROUP BY k ORDER BY a DESC LIMIT 10",
                [CANCELLED, y_from, y_to],
            )
        ]
        status_mix = [
            {"status": r["status"], "text": self.lk.text("contract", "status", r["status"]), "count": r["n"], "amount": money(r["a"])}
            for r in self.rows("SELECT status, COUNT(*) n, SUM(CAST(sum AS REAL)) a FROM contract WHERE _deleted_at IS NULL AND date >= ? AND date < ? GROUP BY status ORDER BY n DESC", [y_from, y_to])
        ]
        recent = [self.order_row(r) for r in self.enrich_orders(self.rows(self.ORDER_SELECT + " WHERE o._deleted_at IS NULL ORDER BY o.date DESC, o.id DESC LIMIT 8"))]
        year_total = agg(f"SELECT COUNT(*) n, SUM(CAST(o.sum AS REAL)) a {base} AND o.date >= ? AND o.date < ?", [CANCELLED, y_from, y_to])
        year_receipts = agg("SELECT COUNT(*) n, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND date >= ? AND date < ?", [y_from, y_to])
        return {"year": year, "kpi": kpi, "monthly": series, "year_total": year_total, "year_receipts": year_receipts,
                "top_customers": top_customers, "top_sales": top_sales, "top_products": top_products, "status_mix": status_mix, "recent_orders": recent}

    # ---- 订单
    ORDER_SELECT = "SELECT o.* FROM contract o"

    def enrich_orders(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为一页订单补上已回款金额与发货单数（先分页再关联，避免对全表逐行做子查询）。"""
        if not rows:
            return rows
        keys = [str(r["id"]) for r in rows] + [r.get("no_") or "" for r in rows]
        marks = ",".join("?" * len(keys))
        received: Dict[str, float] = {}
        for r in self.conn.execute(f"SELECT co_id, SUM(CAST(money AS REAL)) a FROM gathering_note WHERE _deleted_at IS NULL AND co_id IN ({marks}) GROUP BY co_id", keys):
            received[str(r["co_id"])] = money(r["a"])
        shipments: Dict[str, int] = {}
        for r in self.conn.execute(f"SELECT co_id, COUNT(*) n FROM sendgoods WHERE _deleted_at IS NULL AND co_id IN ({marks}) GROUP BY co_id", keys):
            shipments[str(r["co_id"])] = r["n"]
        for row in rows:
            k1, k2 = str(row["id"]), row.get("no_") or ""
            row["received"] = round(received.get(k1, 0.0) + (received.get(k2, 0.0) if k2 != k1 else 0.0), 2)
            row["shipments"] = shipments.get(k1, 0) + (shipments.get(k2, 0) if k2 != k1 else 0)
        return rows

    def order_row(self, r: Dict[str, Any]) -> Dict[str, Any]:
        row = {
            "id": r["id"], "no": r.get("no_"), "date": r.get("date"), "end_date": r.get("end_date"), "subject": r.get("subject"),
            "customer": self.lk.customer(r.get("cu_sn")), "amount": money(r.get("sum")), "money_type": r.get("money_type") or "RMB",
            "status": r.get("status"), "status_text": self.lk.text("contract", "status", r.get("status")),
            "confirm_text": self.lk.text("contract", "confirm", r.get("confirm")),
            "st_send": r.get("st_send"), "st_send_text": self.lk.text("contract", "st_send", r.get("st_send")),
            "type_text": self.lk.text("contract", "type", r.get("type")), "who": r.get("who"),
            "received": money(r.get("received")), "shipments": r.get("shipments") or 0, "memo": r.get("memo"),
            "payment_text": self.lk.text("contract", "payment", r.get("payment")), "pay_mode_text": self.lk.text("contract", "pay_mode", r.get("pay_mode")),
            "contact_name": r.get("name"), "mphone": r.get("mphone"), "addr": r.get("addr"),
        }
        # 自定义字段（发票类型 / 付款方式 / 货期 / 是否试用 / 首单签约 / 提成方案）：有字典时解码，没有字典时不显示代码
        for key, field in ORDER_TERMS:
            row[field] = self.lk.decode("contract", key, r.get(key)) if self.lk.has_dict("contract", key) else ""
        return row

    def orders(self) -> Dict[str, Any]:
        clauses, args = ["o._deleted_at IS NULL"], []
        q = self.get("q")
        if q:
            args.extend([f"%{q}%", f"%{q}%"])
            clauses.append(f"(o.no_ LIKE ? OR o.subject LIKE ? OR {self.name_search_clause('o', q, args)})")
        self.customer_clause("o", clauses, args)
        if self.get("who"):
            clauses.append("o.who = ?")
            args.append(self.lk.part_to_name(self.get("who")))
        if self.get("status"):
            clauses.append("o.status = ?")
            args.append(self.get("status"))
        if self.get("type"):
            clauses.append("o.type = ?")
            args.append(self.get("type"))
        if self.get("st_send"):
            clauses.append("o.st_send = ?")
            args.append(self.get("st_send"))
        for key, _ in ORDER_TERMS:  # 自定义字段筛选（j7 发票类型等）
            if self.get(key):
                clauses.append(f"o.{key} = ?")
                args.append(self.get(key))
        if self.get("month"):
            clauses.append("substr(o.date, 1, 7) = ?")
            args.append(self.get("month")[:7])
        if self.get("state"):
            args.extend([self.get("state"), self.get("state")])
            clauses.append("(o.cu_sn IN (SELECT '[id:' || id || ']' FROM customer WHERE state = ?) OR o.cu_sn IN (SELECT sn FROM customer WHERE sn <> '' AND state = ?))")
        if self.get("owner"):
            args.extend([self.get("owner"), self.get("owner")])
            clauses.append("(o.cu_sn IN (SELECT '[id:' || id || ']' FROM customer WHERE owner = ?) OR o.cu_sn IN (SELECT sn FROM customer WHERE sn <> '' AND owner = ?))")
        if self.get("prod"):  # 单个批号：编号或 "[id:N]" 两种引用都算；解析不到时当型号名，匹配该型号下所有批号
            prod = self.lk.product(self.get("prod"))
            if prod:
                clauses.append("o.id IN (SELECT contract_id FROM contract_goods WHERE prod IN (?, ?))")
                args.extend([prod.get("sn") or "\0", f"[id:{prod['id']}]"])
            else:
                clauses.append("o.id IN (SELECT contract_id FROM contract_goods WHERE prod IN "
                               "(SELECT sn FROM product WHERE name = ? AND sn <> '' UNION ALL SELECT '[id:' || id || ']' FROM product WHERE name = ?))")
                args.extend([self.get("prod"), self.get("prod")])
        if self.get("class"):
            clauses.append(f"o.id IN (SELECT g.contract_id FROM contract_goods g {PRODUCT_JOIN} WHERE COALESCE(p.class, '') = ?)")
            args.append(self.get("class"))
        if self.get("group"):
            titles = self.lk.classes_in_group(self.get("group"))
            if titles:
                clauses.append(f"o.id IN (SELECT g.contract_id FROM contract_goods g {PRODUCT_JOIN} WHERE COALESCE(p.class, '') IN ({','.join('?' * len(titles))}))")
                args.extend(titles)
            else:
                clauses.append("0")
        self.date_clause("o", clauses, args)
        # 销售类型按钮（Richard）：免费样品 = 金额为 0 的订单；填料 / 色谱柱 = 明细里有该大类产品的订单（一单两类都有时两边都算）
        kind_clauses = {k: self._order_kind_clause(k) for k in ORDER_KINDS}
        kind = self.get("kind")
        if kind in kind_clauses:
            c, a = kind_clauses[kind]
            clauses.append(c)
            args.extend(a)
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = self.one(f"SELECT COUNT(*) n, SUM(CASE WHEN o.status <> '3' THEN CAST(o.sum AS REAL) ELSE 0 END) a FROM contract o{where}", args) or {}
        sort = {"amount": "CAST(o.sum AS REAL) DESC, o.id DESC", "date_asc": "o.date ASC, o.id ASC"}.get(self.get("sort"), "o.date DESC, o.id DESC")
        rows = self.enrich_orders(self.rows(f"{self.ORDER_SELECT}{where} ORDER BY {sort} LIMIT ? OFFSET ?", [*args, size, offset]))
        # 三个按钮上的单数：按当前其他条件各算一次（不含按钮自身的条件）
        base_clauses = [c for c in clauses if kind not in kind_clauses or c != kind_clauses[kind][0]]
        base_args = args[: len(args) - len(kind_clauses[kind][1])] if kind in kind_clauses else list(args)
        kinds = {}
        for k, (c, a) in kind_clauses.items():
            r = self.one(f"SELECT COUNT(*) n FROM contract o WHERE {' AND '.join(base_clauses + [c])}", [*base_args, *a]) or {}
            kinds[k] = r.get("n") or 0
        return {"total": total.get("n") or 0, "amount": money(total.get("a")), "page": page, "size": size, "kind": kind if kind in kind_clauses else "",
                "kinds": kinds, "rows": [self.order_row(r) for r in rows]}

    def _order_kind_clause(self, kind: str) -> Tuple[str, List[Any]]:
        if kind == "sample":
            return "CAST(o.sum AS REAL) = 0", []
        titles = self.lk.classes_matching_group(ORDER_KINDS[kind])
        if not titles:
            return "0", []
        return (f"o.id IN (SELECT g.contract_id FROM contract_goods g {PRODUCT_JOIN} WHERE COALESCE(p.class, '') IN ({','.join('?' * len(titles))}))", list(titles))

    def order_detail(self, oid: int) -> Optional[Dict[str, Any]]:
        r = self.one(self.ORDER_SELECT + " WHERE o.id = ?", [oid])
        if not r:
            return None
        order = self.order_row(self.enrich_orders([r])[0])
        goods = []
        for g in self.rows("SELECT * FROM contract_goods WHERE contract_id = ? ORDER BY _seq", [oid]):
            prod = self.lk.product(g.get("prod")) or {}
            goods.append({"prod": g.get("prod"), "product_id": prod.get("id"), "name": prod.get("name") or g.get("prod_name"), "model": prod.get("model") or g.get("model"),
                          "unit": prod.get("unit"), "sku": g.get("sku"), "batchnum": g.get("batchnum"), "amount": g.get("amount"), "unit_price": money(g.get("un_price")),
                          "sum": money(g.get("sum")), "tax_rate": g.get("tax_rate"), "tax_money": money(g.get("tax_money")), "memo": g.get("memo")})
        receipts = [self.receipt_row(x) for x in self.rows(
            "SELECT * FROM gathering_note WHERE _deleted_at IS NULL AND (co_id = ? OR co_id = ?) ORDER BY date DESC, id DESC", [str(oid), r.get("no_") or ""])]
        plans = [self.plan_row(x) for x in self.rows(
            "SELECT * FROM gathering WHERE _deleted_at IS NULL AND (co_sn = ? OR co_sn = ?) ORDER BY date, serial", [r.get("no_") or "", str(oid)])]
        shipments = []
        for s in self.rows("SELECT s.*, (SELECT COUNT(*) FROM sendgoods_items i WHERE i.sendgoods_id = s.id) items FROM sendgoods s WHERE s._deleted_at IS NULL AND (s.co_id = ? OR s.co_id = ?) ORDER BY s.date DESC, s.id DESC", [str(oid), r.get("no_") or ""]):
            shipments.append({"id": s["id"], "date": s.get("date"), "sn": s.get("sn"), "status_text": self.lk.text("sendgoods", "status", s.get("status")), "who": s.get("who"),
                              "sendcomp": s.get("sendcomp"), "sendcode": s.get("sendcode"), "name": s.get("name"), "addr": s.get("addr"), "items": s.get("items") or 0, "memo": s.get("memo")})
        libouts = []
        for x in self.rows("SELECT l.*, (SELECT COUNT(*) FROM libout_items i WHERE i.libout_id = l.id) items FROM libout l WHERE l._deleted_at IS NULL AND l.co_sn = ? ORDER BY l.date DESC, l.id DESC", [r.get("no_") or ""]):
            libouts.append({"id": x["id"], "date": x.get("date"), "title": x.get("title"), "libname": x.get("libname"), "who": self.lk.user_name(x.get("who")), "items": x.get("items") or 0, "memo": x.get("memo")})
        actions = [self.action_row(a) for a in self.enrich_actions(self.rows(
            "SELECT a.*, k.name AS contact_name FROM action a LEFT JOIN contact k ON k.id = CAST(a.con_id AS INTEGER) WHERE a._deleted_at IS NULL AND a.co_id = ? ORDER BY a.date DESC, a.id DESC LIMIT 30", [str(oid)]))]
        terms = self.order_terms(oid)
        extras = [x for x in self.raw_extras("contract", oid, set(r.keys()) | {"goods"}) if x["key"] not in {t["key"] for t in terms}]
        return {"order": order, "goods": goods, "receipts": receipts, "plans": plans, "shipments": shipments, "libouts": libouts, "actions": actions, "terms": terms, "extras": extras}

    def order_terms(self, oid: int) -> List[Dict[str, Any]]:
        """订单自定义字段（合同条款等）：原始 JSON 里的 j* 字段，按字典解码；有字典的排前面。"""
        r = self.one("SELECT data FROM raw_records WHERE dt = 'contract' AND id = ?", [oid])
        if not r:
            return []
        names = self.lk.field_names.get("contract", {})
        data = json.loads(r["data"])
        out = []
        for k, v in data.items():
            if not re.match(r"^j\d+$", k) or v in (None, "", "0", 0) or isinstance(v, (list, dict)):
                continue
            has = self.lk.has_dict("contract", k)
            out.append({"key": k, "name": (names.get(k) or k).strip(), "value": self.lk.decode("contract", k, v), "raw": str(v), "decoded": has})
        return sorted(out, key=lambda x: (not x["decoded"], int(x["key"][1:])))

    def raw_extras(self, dt_name: str, rid: int, skip: set) -> List[Dict[str, str]]:
        """原始 JSON 中未进规范化表的非空字段（自定义字段 j1… 等），配字段中文名；有字典的字段按字典解码。"""
        r = self.one("SELECT data FROM raw_records WHERE dt = ? AND id = ?", [dt_name, rid])
        if not r:
            return []
        names = self.lk.field_names.get(dt_name, {})
        out = []
        for k, v in json.loads(r["data"]).items():
            if k in skip or col_name(k) in skip or v in (None, "", "0", 0, [], {}) or isinstance(v, (list, dict)):
                continue
            out.append({"key": k, "name": (names.get(k) or k).strip(), "value": self.lk.decode(dt_name, k, v)})
        return out

    # ---- 客户
    CUSTOMER_LIST_SQL = """
        WITH o AS (SELECT cu_sn, COUNT(*) n, SUM(CAST(sum AS REAL)) amt, MAX(date) last_date FROM contract WHERE _deleted_at IS NULL AND status <> '3' GROUP BY cu_sn),
             r AS (SELECT cu_sn, SUM(CAST(money AS REAL)) amt, MAX(date) last_date FROM gathering_note WHERE _deleted_at IS NULL GROUP BY cu_sn)
        SELECT c.id, c.sn, c.cu_name, c.m_name, c.owner, c.life, c.type, c.cu_status, c.city, c.district, c.state, c.industry, c.creatdate, c.moddate, c.tel, c.address,
               COALESCE(o1.n, 0) + COALESCE(o2.n, 0) AS orders,
               COALESCE(o1.amt, 0) + COALESCE(o2.amt, 0) AS order_amount,
               COALESCE(o1.last_date, o2.last_date) AS last_order,
               COALESCE(r1.amt, 0) + COALESCE(r2.amt, 0) AS receipts,
               (SELECT COUNT(*) FROM contact k WHERE k.customer_id = c.id) AS contacts
        FROM customer c
        LEFT JOIN o o1 ON o1.cu_sn = '[id:' || c.id || ']'
        LEFT JOIN o o2 ON c.sn <> '' AND o2.cu_sn = c.sn
        LEFT JOIN r r1 ON r1.cu_sn = '[id:' || c.id || ']'
        LEFT JOIN r r2 ON c.sn <> '' AND r2.cu_sn = c.sn
    """

    def customer_row(self, c: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": c["id"], "sn": c.get("sn"), "name": c.get("cu_name") or c.get("m_name"), "short": c.get("m_name"),
            "owner": self.lk.user_name(c.get("owner")), "owner_part": c.get("owner"), "severe": self.lk.severe(c["id"], self.today),
            "life_text": self.lk.text("customer", "life", c.get("life")), "type_text": self.lk.text("customer", "type", c.get("type")),
            "stage_text": self.lk.text("customer", "cu_status", c.get("cu_status")), "industry_text": self.lk.text("customer", "industry", c.get("industry")),
            "city": display_city(c.get("city"), c.get("district"), c.get("address")), "created": c.get("creatdate"), "modified": c.get("moddate"), "tel": c.get("tel"), "address": c.get("address"),
            "orders": c.get("orders") or 0, "order_amount": money(c.get("order_amount")), "last_order": c.get("last_order"),
            "receipts": money(c.get("receipts")), "contacts": c.get("contacts") or 0, "visits": self.lk.visit_stats(c["id"], self.today),
        }

    def customers(self) -> Dict[str, Any]:
        clauses, args = ["c._deleted_at IS NULL"], []
        q = self.get("q")
        if q:
            clauses.append("(c.cu_name LIKE ? OR c.m_name LIKE ? OR c.sn = ? OR c.id = ?)")
            args.extend([f"%{q}%", f"%{q}%", q, _int(q, -1)])
        for col in ("owner", "life", "type", "cu_status"):
            if self.get(col):
                clauses.append(f"c.{col} = ?")
                args.append(self.get(col))
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = (self.one(f"SELECT COUNT(*) n FROM customer c{where}", args) or {}).get("n") or 0
        key, direction = self.customer_sort()
        if key == "visits":                                     # 拜访频度在 Python 里算，注册成 SQL 函数给 ORDER BY 用（连接是每个请求新开的）
            self.conn.create_function("visit_key", 1, self.lk.visit_key, deterministic=True)
        order = f"{self.CUSTOMER_SORTS[key]} {direction.upper()} NULLS LAST, c.id DESC"
        rows = self.rows(f"{self.CUSTOMER_LIST_SQL}{where} ORDER BY {order} LIMIT ? OFFSET ?", [*args, size, offset])
        return {"total": total, "page": page, "size": size, "sort": key, "dir": direction, "rows": [self.customer_row(c) for c in rows]}

    # 客户列表的排序：表头箭头 / 下拉传 sort + dir；缺省按最近订单从新到旧，名称从 A 到 Z，其余从大到小
    CUSTOMER_SORTS = {"last": "last_order", "amount": "order_amount", "orders": "orders", "receipts": "receipts", "contacts": "contacts",
                      "visits": "visit_key(c.id)", "created": "c.creatdate", "name": "c.cu_name COLLATE NOCASE"}

    def customer_sort(self) -> Tuple[str, str]:
        key, direction = self.get("sort") or "last", (self.get("dir") or "").lower()
        if key not in self.CUSTOMER_SORTS:
            key = "last"
        if direction not in ("asc", "desc"):
            direction = "asc" if key == "name" else "desc"
        return key, direction

    def customer_detail(self, cid: int) -> Optional[Dict[str, Any]]:
        c = self.one(self.CUSTOMER_LIST_SQL + " WHERE c.id = ?", [cid])
        if not c:
            return None
        keys = self.customer_keys(cid)
        marks = ",".join("?" * len(keys))
        contacts = [
            {"id": k["id"], "name": k.get("name"), "headship": k.get("headship"), "department": k.get("department"), "mphone": k.get("mphone"), "phone": k.get("phone"),
             "email": k.get("email"), "weixin": k.get("weixin"), "remark": k.get("remark")}
            for k in self.rows("SELECT * FROM contact WHERE customer_id = ? ORDER BY _seq", [cid])
        ]
        orders = [self.order_row(r) for r in self.enrich_orders(self.rows(f"{self.ORDER_SELECT} WHERE o._deleted_at IS NULL AND o.cu_sn IN ({marks}) ORDER BY o.date DESC, o.id DESC LIMIT 50", keys))]
        receipts = [self.receipt_row(x) for x in self.rows(f"SELECT * FROM gathering_note WHERE _deleted_at IS NULL AND cu_sn IN ({marks}) ORDER BY date DESC, id DESC LIMIT 50", keys)]
        plans = [self.plan_row(x) for x in self.rows(f"SELECT * FROM gathering WHERE _deleted_at IS NULL AND status IN ('2','4') AND cu_sn IN ({marks}) ORDER BY date", keys)]
        actions = [self.action_row(a) for a in self.enrich_actions(self.rows(
            f"SELECT a.*, k.name AS contact_name FROM action a LEFT JOIN contact k ON k.id = CAST(a.con_id AS INTEGER) WHERE a._deleted_at IS NULL AND a.cu_sn IN ({marks}) ORDER BY a.date DESC, a.id DESC LIMIT 50", keys))]
        yearly = [
            {"year": r["y"], "count": r["n"], "amount": money(r["a"])}
            for r in self.rows(f"SELECT substr(date,1,4) y, COUNT(*) n, SUM(CAST(sum AS REAL)) a FROM contract WHERE _deleted_at IS NULL AND status <> '3' AND cu_sn IN ({marks}) GROUP BY y ORDER BY y", keys)
        ]
        extras = self.raw_extras("customer", cid, set(c.keys()) | {"contact", "cu_name", "m_name", "sn", "owner", "life", "type", "cu_status", "city", "district", "state", "industry", "creatdate", "moddate", "tel", "address"})
        return {"customer": self.customer_row(c), "contacts": contacts, "orders": orders, "receipts": receipts, "open_plans": plans, "actions": actions, "yearly": yearly, "extras": extras}

    # ---- 应收（计划回款）
    def plan_row(self, g: Dict[str, Any]) -> Dict[str, Any]:
        overdue = 0
        if str(g.get("status")) in OPEN_PLAN and _valid_date(g.get("date")):
            try:
                overdue = (self.today - dt.date.fromisoformat(g["date"])).days
            except ValueError:
                overdue = 0
        return {
            "id": g["id"], "date": g.get("date"), "serial": g.get("serial"), "amount": money(g.get("money")),
            "status": g.get("status"), "status_text": self.lk.text("gathering", "status", g.get("status")),
            "who": self.lk.user_name(g.get("who")), "customer": self.lk.customer(g.get("cu_sn")), "order_no": g.get("co_sn"),
            "order_id": self.order_id_by_no(g.get("co_sn")), "memo": g.get("memo"), "overdue_days": max(overdue, 0),
        }

    _no_cache: Dict[str, Optional[int]] = {}

    def order_id_by_no(self, no: Any) -> Optional[int]:
        if not no:
            return None
        no = str(no)
        if no.isdigit():
            return int(no)
        if no not in self._no_cache:
            r = self.one("SELECT id FROM contract WHERE no_ = ?", [no])
            self._no_cache[no] = r["id"] if r else None
        return self._no_cache[no]

    def receivables(self) -> Dict[str, Any]:
        clauses, args = ["g._deleted_at IS NULL"], []
        status = self.get("status", "open")
        if status == "open":
            clauses.append("g.status IN ('2','4')")
        elif status == "overdue":
            clauses.append("g.status IN ('2','4') AND g.date < ?")
            args.append(self.today.isoformat())
        elif status == "done":
            clauses.append("g.status = '1'")
        self.customer_clause("g", clauses, args)
        self.date_clause("g", clauses, args)
        q = self.get("q")
        if q:
            args.append(f"%{q}%")
            clauses.append(f"(g.co_sn LIKE ? OR {self.name_search_clause('g', q, args)})")
        # 业务员条件放最后：按业务员汇总表不受它影响，这样选了某人之后还能直接切到别人
        where_all, base_args = " WHERE " + " AND ".join(clauses), list(args)
        if self.get("who"):
            clauses.append("g.who = ?")
            args.append(self.get("who"))
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = self.one(f"SELECT COUNT(*) n, SUM(CAST(g.money AS REAL)) a FROM gathering g{where}", args) or {}
        today = self.today.isoformat()
        aging = self.one(
            "SELECT "
            "SUM(CASE WHEN g.date >= ? THEN CAST(g.money AS REAL) ELSE 0 END) AS not_due, "
            "SUM(CASE WHEN g.date < ? AND julianday(?) - julianday(g.date) <= 30 THEN CAST(g.money AS REAL) ELSE 0 END) AS d30, "
            "SUM(CASE WHEN julianday(?) - julianday(g.date) > 30 AND julianday(?) - julianday(g.date) <= 90 THEN CAST(g.money AS REAL) ELSE 0 END) AS d90, "
            "SUM(CASE WHEN julianday(?) - julianday(g.date) > 90 AND julianday(?) - julianday(g.date) <= 365 THEN CAST(g.money AS REAL) ELSE 0 END) AS d365, "
            "SUM(CASE WHEN julianday(?) - julianday(g.date) > 365 THEN CAST(g.money AS REAL) ELSE 0 END) AS d365p "
            f"FROM gathering g{where} AND g.status IN ('2','4')",
            [today] * 8 + list(args),
        ) or {}
        by_who = [
            {"who": self.lk.user_name(r["who"]), "part": r["who"], "count": r["n"], "amount": money(r["a"]),
             "overdue": money(r["od"]), "overdue_count": r["odn"] or 0,
             # 各账龄档的逾期金额，前台在业务员卡右下角用四宫格图标表示
             "aging": {k: money(r[k]) for k in ("d30", "d90", "d365", "d365p")}}
            for r in self.rows(
                "SELECT g.who, COUNT(*) n, SUM(CAST(g.money AS REAL)) a, SUM(CASE WHEN g.date < ? THEN CAST(g.money AS REAL) ELSE 0 END) od, "
                "SUM(CASE WHEN g.date < ? THEN 1 ELSE 0 END) odn, "
                "SUM(CASE WHEN g.date < ? AND julianday(?) - julianday(g.date) <= 30 THEN CAST(g.money AS REAL) ELSE 0 END) d30, "
                "SUM(CASE WHEN julianday(?) - julianday(g.date) > 30 AND julianday(?) - julianday(g.date) <= 90 THEN CAST(g.money AS REAL) ELSE 0 END) d90, "
                "SUM(CASE WHEN julianday(?) - julianday(g.date) > 90 AND julianday(?) - julianday(g.date) <= 365 THEN CAST(g.money AS REAL) ELSE 0 END) d365, "
                f"SUM(CASE WHEN julianday(?) - julianday(g.date) > 365 THEN CAST(g.money AS REAL) ELSE 0 END) d365p FROM gathering g{where_all} "
                "AND g.status IN ('2','4') GROUP BY g.who ORDER BY a DESC LIMIT 50",
                [today] * 9 + list(base_args))
        ]
        key, direction = self.plan_sort()
        rows = self.rows(f"SELECT g.* FROM gathering g{where} ORDER BY {self.PLAN_SORTS[key]} {direction}, g.id LIMIT ? OFFSET ?", [*args, size, offset])
        return {"total": total.get("n") or 0, "amount": money(total.get("a")), "page": page, "size": size, "sort": key, "dir": direction.lower(),
                "aging": {k: money(aging.get(k)) for k in ("not_due", "d30", "d90", "d365", "d365p")}, "by_who": by_who, "rows": [self.plan_row(g) for g in rows]}

    # 计划回款列表的排序：表头箭头传 sort + dir；"逾期" = 计划日期越早逾期越久，所以用 -julianday
    PLAN_SORTS = {"date": "g.date", "amount": "CAST(g.money AS REAL)", "serial": "CAST(g.serial AS REAL)",
                  "overdue": "-julianday(g.date)", "who": "g.who", "customer": "g.cu_sn"}
    TEXT_PLAN_SORTS = ("who", "customer")

    def plan_sort(self) -> Tuple[str, str]:
        key, direction = self.get("sort") or "date", (self.get("dir") or "").lower()
        if key == "date_desc":                                  # 0.6 之前的下拉值
            key, direction = "date", "desc"
        if key not in self.PLAN_SORTS:
            key = "date"
        if direction not in ("asc", "desc"):
            direction = "asc" if key in ("date", *self.TEXT_PLAN_SORTS) else "desc"
        return key, "ASC" if direction == "asc" else "DESC"

    # ---- 回款记录
    def receipt_row(self, n: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": n["id"], "date": n.get("date"), "amount": money(n.get("money")), "money_type": n.get("money_type") or "RMB",
            "type_text": self.lk.text("gathering_note", "type", n.get("type")), "ctype_text": self.lk.text("gathering_note", "ctype", n.get("ctype")),
            "invoice_text": self.lk.text("gathering_note", "invoice", n.get("invoice")), "serial": n.get("serial"),
            "who": n.get("who"), "owner": n.get("owner"), "customer": self.lk.customer(n.get("cu_sn")),
            "order_id": _int(n.get("co_id"), 0) or None, "order_no": n.get("order_no"), "memo": n.get("memo"),
        }

    def receipts(self) -> Dict[str, Any]:
        clauses, args = ["n._deleted_at IS NULL"], []
        if self.get("who"):
            clauses.append("n.who = ?")
            args.append(self.lk.part_to_name(self.get("who")))
        self.customer_clause("n", clauses, args)
        self.date_clause("n", clauses, args)
        if self.get("type"):
            clauses.append("n.type = ?")
            args.append(self.get("type"))
        q = self.get("q")
        if q:
            args.extend([f"%{q}%", f"%{q}%"])
            clauses.append(f"(n.memo LIKE ? OR n.co_id IN (SELECT CAST(id AS TEXT) FROM contract WHERE no_ LIKE ?) OR {self.name_search_clause('n', q, args)})")
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = self.one(f"SELECT COUNT(*) n, SUM(CAST(n.money AS REAL)) a FROM gathering_note n{where}", args) or {}
        by_month = [{"month": r["m"], "count": r["n"], "amount": money(r["a"])} for r in self.rows(
            f"SELECT substr(n.date,1,7) m, COUNT(*) n, SUM(CAST(n.money AS REAL)) a FROM gathering_note n{where} GROUP BY m ORDER BY m DESC LIMIT 24", args)][::-1]
        by_who = [{"who": r["who"], "count": r["n"], "amount": money(r["a"])} for r in self.rows(
            f"SELECT n.who, COUNT(*) n, SUM(CAST(n.money AS REAL)) a FROM gathering_note n{where} GROUP BY n.who ORDER BY a DESC LIMIT 15", args)]
        rows = self.rows(
            f"SELECT n.*, (SELECT no_ FROM contract c WHERE c.id = CAST(n.co_id AS INTEGER)) AS order_no FROM gathering_note n{where} ORDER BY n.date DESC, n.id DESC LIMIT ? OFFSET ?",
            [*args, size, offset])
        return {"total": total.get("n") or 0, "amount": money(total.get("a")), "page": page, "size": size, "by_month": by_month, "by_who": by_who,
                "rows": [self.receipt_row(n) for n in rows]}

    # ---- 工作日志（行动记录）
    def date_flag(self, value: Any) -> str:
        """日期质量标记：future = 晚于今天（录入错误，如 2224-06-12）；invalid = 空或格式异常；正常为空串。"""
        if not _valid_date(value):
            return "invalid"
        return "future" if value > self.today.isoformat() else ""

    def action_row(self, a: Dict[str, Any]) -> Dict[str, Any]:
        """一行 = CRM 中的一条行动记录（业务员自行录入，一条记录只挂一个客户与一个联系人）。

        CRM 的 subject 字段截断为 128 字，长记录的 subject 只是 content 的开头，展示时去重；
        content 为多段文字时保留换行。
        """
        subject, content = (a.get("subject") or "").strip(), (a.get("content") or "").strip()
        if content and (content == subject or content.startswith(subject)):
            text, title = content, ""
        elif content and subject:
            text, title = content, subject
        else:
            text, title = content or subject, ""
        return {
            "id": a["id"], "date": a.get("date"), "end_date": a.get("endate"), "date_flag": self.date_flag(a.get("date")),
            "cale_text": self.lk.text("action", "cale", a.get("cale")),
            "type": a.get("type"), "type_text": self.lk.text("action", "type", a.get("type")), "who": self.lk.names_from_codes(a.get("who")),
            "customer": self.lk.customer(a.get("cu_sn")), "contact": a.get("contact_name"), "subject": title,
            "content": text, "chars": len(text), "mentions": a.get("mentions") or [], "order_id": _int(a.get("co_id"), 0) or None,
            # 客户维度：这是第几次 / 共几次拜访、上一次拜访、该客户历史订单额
            "visit_no": a.get("visit_no"), "visit_total": a.get("visit_total"), "prev_visit": a.get("prev_visit"),
            "cust_amount": a.get("cust_amount"), "cust_orders": a.get("cust_orders"),
            # 联系人的联系方式（缺失时前台标⚠）
            "contact_phone": (a.get("contact_mphone") or a.get("contact_tel") or "").strip(),
            "contact_email": (a.get("contact_email") or "").strip(), "contact_weixin": (a.get("contact_weixin") or "").strip(),
            "dup": a.get("dup"),      # 同客户查重结果（dup=0 时不算）
        }

    def enrich_action_stats(self, rows: List[Dict[str, Any]]) -> None:
        """给每条记录补：该客户的第几次 / 共几次拜访、上一次拜访日期、该客户历史订单额（不含意外中止）。"""
        keys = {r.get("cu_sn") for r in rows if (r.get("cu_sn") or "").strip() not in ("", "[id:0]", "0")}
        if not keys:
            return
        marks = ",".join("?" * len(keys))
        seq: Dict[Any, Tuple[int, int, Optional[str]]] = {}
        for r in self.conn.execute(
                "SELECT id, ROW_NUMBER() OVER (PARTITION BY cu_sn ORDER BY date, id) rn, COUNT(*) OVER (PARTITION BY cu_sn) total, "
                f"LAG(date) OVER (PARTITION BY cu_sn ORDER BY date, id) prev FROM action WHERE _deleted_at IS NULL AND cu_sn IN ({marks})",
                list(keys)):
            seq[r["id"]] = (r["rn"], r["total"], r["prev"])
        cids = {self.lk.customer_id(k) for k in keys}
        cids.discard(None)
        amounts: Dict[int, Tuple[float, int]] = {}
        if cids:
            ckeys = [k for cid in cids for k in self.customer_keys(cid)]      # 客户在订单里有 "[id:N]" 与编号两种写法
            marks2 = ",".join("?" * len(ckeys))
            for r in self.conn.execute(
                    f"SELECT {CID_EXPR.format(t='o')} cid, SUM({ORDER_RMB_EXPR}) a, COUNT(*) n FROM contract o "
                    f"WHERE o._deleted_at IS NULL AND o.status <> '{CANCELLED}' AND o.cu_sn IN ({marks2}) GROUP BY cid", ckeys):
                if r["cid"] is not None:
                    amounts[r["cid"]] = (r["a"] or 0.0, r["n"] or 0)
        for r in rows:
            rn = seq.get(r["id"])
            if rn:
                r["visit_no"], r["visit_total"], r["prev_visit"] = rn[0], rn[1], rn[2] or None
            cid = self.lk.customer_id(r.get("cu_sn"))
            amt = amounts.get(cid)
            if amt:
                r["cust_amount"], r["cust_orders"] = money(amt[0]), amt[1]

    def enrich_action_dups(self, rows: List[Dict[str, Any]]) -> None:
        """与同一客户此前的 10 条日志比对：给出重复覆盖率、重复片段位置，以及那 10 条的摘要。"""
        keys = {r.get("cu_sn") for r in rows if (r.get("cu_sn") or "").strip() not in ("", "[id:0]", "0")}
        if not keys:
            return
        marks = ",".join("?" * len(keys))
        by_cust: Dict[str, List[Dict[str, Any]]] = {}
        for r in self.conn.execute(
                "SELECT id, cu_sn, date, who, type, subject, content FROM (SELECT id, cu_sn, date, who, type, subject, content, "
                "ROW_NUMBER() OVER (PARTITION BY cu_sn ORDER BY date DESC, id DESC) rn FROM action "
                f"WHERE _deleted_at IS NULL AND cu_sn IN ({marks})) WHERE rn <= {DUP_SCAN} ORDER BY date DESC, id DESC", list(keys)):
            by_cust.setdefault(r["cu_sn"], []).append(dict(r))
        for row in rows:
            lst = by_cust.get(row.get("cu_sn") or "")
            text = (row.get("content") or "") or (row.get("subject") or "")   # 不 strip：片段位置要和前台显示的正文对齐
            if not lst or len(text.strip()) < DUP_MIN_LEN:
                continue
            idx = next((i for i, x in enumerate(lst) if x["id"] == row["id"]), None)
            peers = lst[idx + 1: idx + 1 + DUP_PEERS] if idx is not None else lst[:DUP_PEERS]
            if not peers:
                continue
            cur_sh = _shingles(text)
            spans: List[Tuple[int, int]] = []
            best, best_peer, out_peers = 0.0, None, []
            for p in peers:
                ptext = ((p.get("content") or "").strip() or (p.get("subject") or "").strip())  # 对照文本可以 strip
                psh = _shingles(ptext)
                ratio = len(cur_sh & psh) / len(cur_sh) if cur_sh and psh else 0.0
                if ratio >= DUP_DIFF_AT:
                    for b in difflib.SequenceMatcher(None, text, ptext, autojunk=False).get_matching_blocks():
                        if b.size >= DUP_BLOCK:
                            spans.append((b.a, b.size))
                if ratio > best:
                    best, best_peer = ratio, p
                out_peers.append({
                    "id": p["id"], "date": p.get("date"), "who": self.lk.names_from_codes(p.get("who")),
                    "type_text": self.lk.text("action", "type", p.get("type")), "ratio": round(ratio, 3),
                    "content": ptext[:DUP_TEXT_MAX], "truncated": len(ptext) > DUP_TEXT_MAX,
                })
            row["dup"] = {
                "ratio": round(best, 3), "alert": best >= DUP_ALERT, "marks": _merge_spans(spans), "peers": out_peers,
                "best": {"id": best_peer["id"], "date": best_peer.get("date"), "who": self.lk.names_from_codes(best_peer.get("who"))} if best_peer and best > 0 else None,
            }

    def enrich_actions(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标出记录文字里提到的该客户其他联系人（按 CRM 联系人表匹配；未建档的人名识别不了）。"""
        cids = {self.lk.customer_id(r.get("cu_sn")) for r in rows}
        cids.discard(None)
        if not cids:
            return rows
        contacts: Dict[int, List[Tuple[int, str]]] = {}
        marks = ",".join("?" * len(cids))
        for k in self.conn.execute(f"SELECT customer_id, id, name FROM contact WHERE customer_id IN ({marks})", list(cids)):
            if k["name"] and len(k["name"].strip()) >= 2:
                contacts.setdefault(k["customer_id"], []).append((k["id"], k["name"].strip()))
        for r in rows:
            cid = self.lk.customer_id(r.get("cu_sn"))
            text = (r.get("content") or "") + "\n" + (r.get("subject") or "")
            primary = _int(r.get("con_id"), 0)
            found = []
            for kid, kname in contacts.get(cid, []):
                if kid != primary and kname in text and kname not in found:
                    found.append(kname)
            r["mentions"] = found
        return rows

    def actions(self) -> Dict[str, Any]:
        clauses, args = ["a._deleted_at IS NULL"], []
        if self.get("who"):
            clauses.append("(',' || a.who || ',') LIKE ?")
            args.append(f"%,{self.get('who')},%")
        if self.get("type"):
            clauses.append("a.type = ?")
            args.append(self.get("type"))
        if self.get("cale"):
            clauses.append("a.cale = ?")
            args.append(self.get("cale"))
        self.customer_clause("a", clauses, args)
        self.date_clause("a", clauses, args)
        q = self.get("q")
        if q:
            args.extend([f"%{q}%", f"%{q}%"])
            clauses.append(f"(a.subject LIKE ? OR a.content LIKE ? OR {self.name_search_clause('a', q, args)})")
        where = " WHERE " + " AND ".join(clauses)
        page, size, offset = self.page()
        total = (self.one(f"SELECT COUNT(*) n FROM action a{where}", args) or {}).get("n") or 0
        by_type = [{"type": r["type"], "text": self.lk.text("action", "type", r["type"]) or "未分类", "count": r["n"]}
                   for r in self.rows(f"SELECT a.type, COUNT(*) n FROM action a{where} GROUP BY a.type ORDER BY n DESC", args)]
        by_day = [{"date": r["d"], "count": r["n"]} for r in self.rows(
            f"SELECT a.date d, COUNT(*) n FROM action a{where} AND a.date LIKE '____-__-__' AND a.date <= ? GROUP BY a.date ORDER BY d DESC LIMIT 62", [*args, self.today.isoformat()])][::-1]
        who_counts: Dict[str, List[int]] = {}
        for r in self.rows(f"SELECT a.who, COUNT(*) n, SUM(length(COALESCE(NULLIF(a.content, ''), a.subject, ''))) chars FROM action a{where} GROUP BY a.who", args):
            for code in [p for p in str(r["who"] or "").split(",") if p.strip()] or [str(r["who"] or "")]:
                acc = who_counts.setdefault(code, [0, 0])
                acc[0] += r["n"]
                acc[1] += r["chars"] or 0
        by_who = [{"who": self.lk.user_name(k), "part": k, "count": v[0], "chars": v[1]} for k, v in sorted(who_counts.items(), key=lambda kv: -kv[1][0])[:20]]
        detail_sql = ("SELECT a.*, k.name AS contact_name, k.mphone AS contact_mphone, k.phone AS contact_tel, k.email AS contact_email, k.weixin AS contact_weixin "
                      "FROM action a LEFT JOIN contact k ON k.id = CAST(a.con_id AS INTEGER)")
        dup_on = self.get("dup", "1") not in ("0", "", "off", "false")
        dup_min = _int(self.get("dup_min"), 0)
        scanned = 0
        if dup_on and dup_min > 0:
            # 查重筛选：在当前条件下先扫一批，算完相似度再按相似度排序分页（找“照搬”用）
            scan = self.rows(f"SELECT a.id, a.cu_sn, a.date, a.who, a.type, a.subject, a.content FROM action a{where} "
                             f"ORDER BY a.date DESC, a.id DESC LIMIT {DUP_SCAN_MAX}", args)
            scanned = len(scan)
            self.enrich_action_dups(scan)
            hits = sorted((r for r in scan if (r.get("dup") or {}).get("ratio", 0) >= dup_min / 100),
                          key=lambda r: -r["dup"]["ratio"])
            total = len(hits)
            picked = hits[offset:offset + size]
            rows = []
            if picked:
                order = {r["id"]: i for i, r in enumerate(picked)}
                marks2 = ",".join("?" * len(picked))
                rows = self.rows(f"{detail_sql} WHERE a.id IN ({marks2})", [r["id"] for r in picked])
                rows.sort(key=lambda r: order.get(r["id"], 0))
                for r in rows:
                    r["dup"] = next((x["dup"] for x in picked if x["id"] == r["id"]), None)
            self.enrich_actions(rows)
            self.enrich_action_stats(rows)
        else:
            # 日期录错成未来（如 2224-06-12）的记录排到正常记录之后，不再顶在最新一条前面
            rows = self.enrich_actions(self.rows(
                f"{detail_sql}{where} ORDER BY (CASE WHEN a.date > ? THEN 1 ELSE 0 END), a.date DESC, a.id DESC LIMIT ? OFFSET ?",
                [*args, self.today.isoformat(), size, offset]))
            self.enrich_action_stats(rows)
            if dup_on:
                self.enrich_action_dups(rows)
        return {"total": total, "page": page, "size": size, "by_type": by_type, "by_day": by_day, "by_who": by_who,
                "dup_on": dup_on, "dup_alert": DUP_ALERT, "dup_min": dup_min, "dup_scanned": scanned,
                "rows": [self.action_row(a) for a in rows]}


# ---------------------------------------------------------------------- HTTP
ROUTES: List[Tuple[re.Pattern, Callable[[Query, re.Match], Any]]] = [
    (re.compile(r"^/api/meta$"), lambda q, m: q.meta()),
    (re.compile(r"^/api/overview$"), lambda q, m: q.overview()),
    (re.compile(r"^/api/orders$"), lambda q, m: q.orders()),
    (re.compile(r"^/api/orders/(\d+)$"), lambda q, m: q.order_detail(int(m.group(1)))),
    (re.compile(r"^/api/customers$"), lambda q, m: q.customers()),
    (re.compile(r"^/api/customers/(\d+)$"), lambda q, m: q.customer_detail(int(m.group(1)))),
    (re.compile(r"^/api/receivables$"), lambda q, m: q.receivables()),
    (re.compile(r"^/api/receipts$"), lambda q, m: q.receipts()),
    (re.compile(r"^/api/actions$"), lambda q, m: q.actions()),
    (re.compile(r"^/api/sales$"), lambda q, m: q.sales()),
    (re.compile(r"^/api/customer_analysis$"), lambda q, m: q.customer_analysis()),
    (re.compile(r"^/api/salesperson$"), lambda q, m: q.salesperson()),
    (re.compile(r"^/api/products$"), lambda q, m: q.products()),
    (re.compile(r"^/api/product$"), lambda q, m: q.product_detail()),
    (re.compile(r"^/api/purchases$"), lambda q, m: q.purchases()),
    (re.compile(r"^/api/purchases/(\d+)$"), lambda q, m: q.purchase_detail(int(m.group(1)))),
    (re.compile(r"^/api/pay_plans$"), lambda q, m: q.pay_plans()),
    (re.compile(r"^/api/cashflow$"), lambda q, m: q.cashflow()),
    (re.compile(r"^/api/contacts$"), lambda q, m: q.contacts()),
    (re.compile(r"^/api/export/([a-z_]+)$"), lambda q, m: export_query(q, m.group(1))),
]


def export_query(q: Query, kind: str) -> Any:
    q.max_size = EXPORT_MAX
    q.p = {**q.p, "size": str(EXPORT_MAX), "page": "1", "limit": str(EXPORT_MAX)}
    try:
        return build_export(q, kind)
    except KeyError:
        return None


class Handler(BaseHTTPRequestHandler):
    mirror: Mirror  # 由 make_server 注入
    access: AccessControl
    server_version = "xtools-web/0.6"

    def log_message(self, fmt: str, *args: Any) -> None:  # 访问日志降级为 debug
        logger.debug("%s " + fmt, self.address_string(), *args)

    def do_GET(self) -> None:  # noqa: N802
        denial = self.access.check(self.client_address[0], self.headers.get("Authorization"))
        if denial:
            return self.send_denied(*denial)
        url = urlparse(self.path)
        path = url.path
        if path in ("/", "/index.html"):
            return self.send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if path.startswith("/static/") and "/../" not in path:
            return self.send_file(STATIC_DIR / path[len("/static/"):], None)
        for pattern, func in ROUTES:
            m = pattern.match(path)
            if m:
                params = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=False).items()}
                return self.send_api(func, m, params)
        self.send_json({"error": "not found"}, 404)

    def send_api(self, func: Callable, m: re.Match, params: Dict[str, str]) -> None:
        t0 = time.time()
        conn = None
        try:
            conn = self.mirror.connect()
            lk = self.mirror.lookups(conn)
            result = func(Query(conn, lk, params), m)
            if result is None:
                return self.send_json({"error": "not found"}, 404)
            if isinstance(result, Download):
                self.send_download(result)
            else:
                self.send_json(result)
            logger.info("%s %s %.0fms", self.path.split("?")[0], json.dumps(params, ensure_ascii=False) if params else "", (time.time() - t0) * 1000)
        except sqlite3.Error as exc:
            logger.exception("数据库错误 %s", self.path)
            self.send_json({"error": f"数据库错误：{exc}"}, 500)
        except Exception as exc:  # noqa: BLE001
            logger.exception("接口异常 %s", self.path)
            self.send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
        finally:
            if conn is not None:
                conn.close()

    def send_json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_denied(self, status: int, message: str) -> None:
        logger.warning("拒绝访问 %s %s：%s", self.client_address[0], self.path.split("?")[0], message)
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        if status == 401:
            self.send_header("WWW-Authenticate", 'Basic realm="XTools", charset="UTF-8"')
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_download(self, d: Download) -> None:
        ascii_name = re.sub(r"[^A-Za-z0-9._-]+", "_", d.filename) or "export.xlsx"
        self.send_response(200)
        self.send_header("Content-Type", d.content_type)
        self.send_header("Content-Length", str(len(d.data)))
        self.send_header("Content-Disposition", f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(d.filename)}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(d.data)

    def send_file(self, path: Path, content_type: Optional[str]) -> None:
        try:
            path = path.resolve()
            if STATIC_DIR.resolve() not in path.parents and path != STATIC_DIR.resolve():
                raise FileNotFoundError(path)
            data = path.read_bytes()
        except (FileNotFoundError, IsADirectoryError):
            return self.send_json({"error": "not found"}, 404)
        if content_type is None:
            content_type = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                            ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}.get(path.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")   # 页面改版后不用再手动强制刷新
        self.end_headers()
        self.wfile.write(data)


def make_server(db_path: str | Path, host: str = "127.0.0.1", port: int = 8790, access: Optional[AccessControl] = None) -> ThreadingHTTPServer:
    mirror = Mirror(db_path)
    handler = type("BoundHandler", (Handler,), {"mirror": mirror, "access": access or AccessControl(host)})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server
