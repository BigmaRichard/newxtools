#!/usr/bin/env python3
"""检索工作日志（行动记录）里提到、但在 CRM 中缺少联系方式的联系人，输出自包含 HTML 报表。

用法：
    python scripts/report_missing_contacts.py                      # 近 5 年，输出到 reports/
    python scripts/report_missing_contacts.py --years 3 --out reports/x.html
    python scripts/report_missing_contacts.py --jieba              # 装了 jieba 时补充其识别的人名并用其词典过滤
    python scripts/report_missing_contacts.py --sample 40          # 终端打印抽样结果，便于核对抽取效果

判定：
    未建档            正文里出现全名（姓 + 名），该客户联系人表里没有这个人
    未建档（仅姓氏）  只写了“彭老师”“李总”，该客户联系人表里没有这个姓的人
    已建档无联系方式  对上了联系人表里的人（按全名，或姓氏仅对应一人），但手机、电话、微信、QQ、邮箱都是空的
    关联联系人无联系方式  记录本身挂的联系人（con_id）没有任何联系方式

只读镜像库，不写入。报表含客户与人名，放在 reports/（已在 .gitignore 中，不进仓库）。
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.names import COMPOUND_SURNAMES, extract_names, load_vocab  # noqa: E402
from web.server import Mirror  # noqa: E402

TYPES = {
    "unregistered": "未建档",
    "surname_only": "未建档（仅姓氏）",
    "no_info": "已建档无联系方式",
    "linked_no_info": "关联联系人无联系方式",
}
INFO_FIELDS = [("mphone", "手机"), ("phone", "电话"), ("weixin", "微信"), ("qq", "QQ"), ("email", "邮箱")]
# 名字后面紧跟这些词，多半是公司 / 机构简称而不是人（“盛迪医药”“安谱检测”）
ORG_SUFFIX = ("医药", "科技", "生物", "药业", "制药", "有限", "公司", "检测", "仪器", "化学", "化工", "材料", "集团", "贸易", "实业", "研究院", "研究所", "大学",
              "学院", "医院", "中心", "技术", "工业", "产业", "股份", "药厂", "饮片", "试剂", "耗材", "商贸", "电子", "机械", "设备", "新材", "环保", "食品", "健康", "工程")


def surname_of(name: str) -> str:
    for cs in COMPOUND_SURNAMES:
        if name.startswith(cs):
            return cs
    return name[:1]


def contact_info(c: Dict[str, Any]) -> List[str]:
    return [label for key, label in INFO_FIELDS if (c.get(key) or "").strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="工作日志里缺少联系方式的联系人")
    parser.add_argument("--db", default=str(ROOT / "data" / "xtools_mirror.sqlite"))
    parser.add_argument("--years", type=float, default=5, help="检索最近几年，缺省 5")
    parser.add_argument("--since", help="起始日期 YYYY-MM-DD（给出时忽略 --years）")
    parser.add_argument("--out", help="输出 HTML 路径，缺省 reports/联系人缺失_工作日志_近N年_日期.html")
    parser.add_argument("--jieba", action="store_true", help="使用 jieba（需已安装）补充人名候选并过滤常见词")
    parser.add_argument("--sample", type=int, default=0, help="在终端打印 N 条抽样，便于核对")
    parser.add_argument("--limit", type=int, default=0, help="调试用：只处理前 N 条记录")
    args = parser.parse_args()

    today = dt.date.today()
    since = args.since or (today - dt.timedelta(days=round(365.25 * args.years))).isoformat()
    t0 = time.time()
    vocab_n = load_vocab()
    mirror = Mirror(args.db)
    conn = mirror.connect()
    lk = mirror.lookups(conn)
    staff = {u["name"].replace("(离职)", "").strip() for u in lk.users.values()} | {"麦可旺志", "Microwants", "微旺志"}
    staff.discard("boss")

    contacts_by_customer: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    contacts_by_id: Dict[int, Dict[str, Any]] = {}
    contacts_by_name: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in conn.execute("SELECT id, customer_id, name, headship, department, mphone, phone, weixin, qq, email FROM contact"):
        c = dict(r)
        c["name"] = (c.get("name") or "").strip()
        contacts_by_customer[c["customer_id"]].append(c)
        contacts_by_id[c["id"]] = c
        if c["name"]:
            contacts_by_name[c["name"]].append(c)

    sql = ("SELECT id, date, who, cu_sn, con_id, subject, content, type FROM action "
           "WHERE _deleted_at IS NULL AND date >= ? AND date <= ? AND date LIKE '____-__-__' ORDER BY date DESC, id DESC")
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"
    rows_out: List[Dict[str, Any]] = []
    texts: Dict[int, str] = {}
    persons: Dict[Tuple[Optional[int], str, str], Dict[str, Any]] = {}
    scanned = 0
    mention_total = 0
    for a in conn.execute(sql, (since, today.isoformat())):
        scanned += 1
        subject, content = (a["subject"] or "").strip(), (a["content"] or "").strip()
        text = content if (content and (content == subject or content.startswith(subject))) else (f"{subject}\n{content}" if subject and content else (content or subject))
        cid = lk.customer_id(a["cu_sn"])
        cust = lk.customers.get(cid) if cid else None
        cust_name = (cust["cu_name"] or cust["m_name"]) if cust else (a["cu_sn"] if a["cu_sn"] and a["cu_sn"] != "[id:0]" else "（未关联客户）")
        clist = contacts_by_customer.get(cid, []) if cid else []
        who = lk.names_from_codes(a["who"])
        findings: List[Dict[str, Any]] = []

        # 记录本身挂的联系人
        try:
            linked = contacts_by_id.get(int(a["con_id"] or 0))
        except ValueError:
            linked = None
        if linked and linked["name"] and not contact_info(linked):
            findings.append({"name": linked["name"], "type": "linked_no_info", "hint": f"记录关联的联系人（{linked.get('headship') or ''}）".replace("（）", "")})

        mentions = extract_names(text, known=[c["name"] for c in clist], exclude=staff, use_jieba=args.jieba,
                                 orgs=[cust_name, (cust or {}).get("m_name") or ""])
        mention_total += len(mentions)
        for m in mentions:
            if linked and m.name == linked["name"]:
                continue  # 已按关联联系人处理
            if m.source == "registered":
                matched = [c for c in clist if c["name"] == m.name]
                if any(contact_info(c) for c in matched):
                    continue
                findings.append({"name": m.name, "type": "no_info", "hint": "已建档" + (f"（{matched[0].get('headship')}）" if matched and matched[0].get("headship") else "")})
                continue
            if m.surname_only:
                sn = m.surname
                same = [c for c in clist if c["name"] and surname_of(c["name"]) == sn]
                if not same:
                    findings.append({"name": m.name, "type": "surname_only", "hint": "该客户下没有这个姓的联系人"})
                elif len(same) == 1:
                    if not contact_info(same[0]):
                        findings.append({"name": f"{m.name} → {same[0]['name']}", "type": "no_info", "hint": "按姓氏对应到已建档联系人"})
                elif all(not contact_info(c) for c in same):
                    findings.append({"name": m.name, "type": "no_info", "hint": "姓氏对应 " + "、".join(c["name"] for c in same[:4]) + "，均无联系方式"})
                continue
            # 全名，未在该客户下建档；先排除公司 / 机构简称
            if any((m.name + suf) in text or (m.name + suf) in cust_name for suf in ORG_SUFFIX) or cust_name.startswith(m.name):
                continue
            elsewhere = [c for c in contacts_by_name.get(m.name, []) if c["customer_id"] != cid]
            hint = ""
            if elsewhere:
                names = sorted({(lk.customers.get(c["customer_id"]) or {}).get("cu_name") or str(c["customer_id"]) for c in elsewhere})
                hint = "其他客户下有同名联系人：" + "；".join(names[:3]) + ("…" if len(names) > 3 else "")
            elif cust and m.name in (cust.get("cu_name") or ""):
                hint = "客户名称里含此人名，但联系人表没有"
            findings.append({"name": m.name, "type": "unregistered", "hint": hint, "source": m.source})

        for f in findings:
            key = (cid, f["name"], f["type"])
            p = persons.setdefault(key, {"customer_id": cid, "customer": cust_name, "name": f["name"], "type": f["type"], "count": 0, "first": a["date"], "last": a["date"], "who": set(), "hint": f["hint"]})
            p["count"] += 1
            p["first"] = min(p["first"], a["date"])
            p["last"] = max(p["last"], a["date"])
            p["who"].update(who)
            texts[a["id"]] = text
            rows_out.append({"id": a["id"], "date": a["date"], "who": "、".join(who), "name": f["name"], "type": f["type"], "hint": f["hint"],
                             "customer": cust_name, "customer_id": cid, "kind": lk.text("action", "type", a["type"])})
    conn.close()

    summary = {"scanned": scanned, "mentions": mention_total, "rows": len(rows_out), "persons": len(persons), "since": since, "until": today.isoformat(),
               "by_type": {k: sum(1 for r in rows_out if r["type"] == k) for k in TYPES}, "vocab": vocab_n, "jieba": args.jieba,
               "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "seconds": round(time.time() - t0, 1)}
    person_rows = sorted(({**p, "who": "、".join(sorted(p["who"]))} for p in persons.values()), key=lambda p: (-p["count"], p["last"]), reverse=False)

    if args.sample:
        import random
        random.seed(3)
        for r in random.sample(rows_out, min(args.sample, len(rows_out))):
            print(f"[{TYPES[r['type']]}] {r['date']} {r['who']} | {r['name']} | {r['customer']} | {r['hint']}\n    {texts[r['id']][:160].replace(chr(10), ' ')}")
    print(f"扫描 {scanned} 条记录，抽到人名 {mention_total} 个，问题条目 {len(rows_out)}，涉及 {len(persons)} 人；"
          + "；".join(f"{TYPES[k]} {v}" for k, v in summary["by_type"].items()) + f"；用时 {summary['seconds']}s")

    out = Path(args.out) if args.out else ROOT / "reports" / f"联系人缺失_工作日志_近{args.years:g}年_{today.strftime('%Y%m%d')}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(rows_out, person_rows, summary, texts), encoding="utf-8")
    print("已写入", out)
    return 0


def render_html(rows: List[Dict[str, Any]], persons: List[Dict[str, Any]], s: Dict[str, Any], texts: Dict[int, str]) -> str:
    data = json.dumps({"rows": rows, "persons": persons, "summary": s, "types": TYPES, "texts": {str(k): v for k, v in texts.items()}}, ensure_ascii=False).replace("</", "<\\/")
    title = f"工作日志提到但缺少联系方式的联系人（{s['since']} 至 {s['until']}）"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ --bg:#f5f5f3; --surface:#fff; --surface-2:#f7f7f5; --border:#e4e3df; --text:#17171a; --text-2:#55554f; --muted:#8a8a83; --accent:#2a78d6; --accent-soft:#e8f1fc; --warn:#b87a00; --bad:#d03b3b; --bad-soft:#fbe9e9; --good:#0ca30c; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#131312; --surface:#1c1c1b; --surface-2:#232322; --border:#2f2f2d; --text:#f2f2ee; --text-2:#c3c2b7; --muted:#8d8d86; --accent:#3987e5; --accent-soft:#1d2a3b; --warn:#e0a021; --bad:#e66767; --bad-soft:#3a2323; --good:#3fbf3f; }} }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--text); font:14px/1.5 -apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; }}
main {{ max-width:1500px; margin:0 auto; padding:18px 20px 60px; }}
h1 {{ font-size:20px; margin:0 0 4px; }} .sub {{ color:var(--muted); font-size:13px; margin-bottom:14px; }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 16px; margin-bottom:14px; }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-bottom:14px; }}
.kpi .label {{ color:var(--muted); font-size:12px; }} .kpi .value {{ font-size:22px; font-weight:600; font-variant-numeric:tabular-nums; }}
.filters {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; }}
.filters input, .filters select {{ font:inherit; color:inherit; background:var(--surface); border:1px solid var(--border); border-radius:7px; padding:6px 9px; }}
.filters input[type=text] {{ width:260px; }}
.btn {{ font:inherit; color:inherit; background:var(--surface); border:1px solid var(--border); border-radius:7px; padding:6px 12px; cursor:pointer; }} .btn:hover {{ background:var(--surface-2); }}
.tabs {{ display:flex; gap:4px; border-bottom:1px solid var(--border); margin-bottom:12px; }} .tabs a {{ padding:8px 14px; color:var(--text-2); cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px; font-weight:500; }} .tabs a.active {{ color:var(--accent); border-bottom-color:var(--accent); }}
table {{ width:100%; border-collapse:collapse; }} th, td {{ padding:7px 8px; text-align:left; border-bottom:1px solid var(--border); vertical-align:top; }}
th {{ color:var(--muted); font-weight:500; font-size:12px; white-space:nowrap; position:sticky; top:0; background:var(--surface); }}
td.nowrap {{ white-space:nowrap; }} .num {{ text-align:right; }}
.tag {{ display:inline-block; padding:1px 7px; border-radius:999px; font-size:12px; border:1px solid var(--border); background:var(--surface-2); color:var(--text-2); white-space:nowrap; }}
.tag.unregistered {{ color:var(--bad); background:var(--bad-soft); border-color:transparent; }} .tag.surname_only {{ color:var(--warn); }} .tag.no_info {{ color:var(--accent); background:var(--accent-soft); border-color:transparent; }} .tag.linked_no_info {{ color:var(--text-2); }}
.muted {{ color:var(--muted); }} .small {{ font-size:12px; }}
.text {{ white-space:pre-wrap; color:var(--text-2); max-width:760px; }} .text.clip {{ max-height:4.6em; overflow:hidden; position:relative; }}
.text mark {{ background:#ffe58a; color:#000; padding:0 2px; border-radius:2px; }}
.more {{ color:var(--accent); cursor:pointer; font-size:12px; }}
.pager {{ display:flex; gap:10px; align-items:center; justify-content:flex-end; margin-top:10px; color:var(--text-2); font-size:13px; }}
.note {{ color:var(--text-2); font-size:13px; }} .note li {{ margin:2px 0; }}
</style>
</head>
<body><main>
<h1>{html.escape(title)}</h1>
<div class="sub">麦可旺志 Microwants · 由 XTools 镜像生成于 {s['generated']} · 扫描行动记录 {s['scanned']:,} 条，抽到人名 {s['mentions']:,} 个 · 抽取用规则法{'（含 jieba 补充）' if s['jieba'] else ''}，结果供人工核对</div>
<div class="kpis">
  <div class="card kpi"><div class="label">问题条目（日志 × 联系人）</div><div class="value">{s['rows']:,}</div></div>
  <div class="card kpi"><div class="label">涉及联系人</div><div class="value">{s['persons']:,}</div></div>
  <div class="card kpi"><div class="label">未建档（全名）</div><div class="value">{s['by_type']['unregistered']:,}</div></div>
  <div class="card kpi"><div class="label">未建档（仅姓氏）</div><div class="value">{s['by_type']['surname_only']:,}</div></div>
  <div class="card kpi"><div class="label">已建档无联系方式</div><div class="value">{s['by_type']['no_info']:,}</div></div>
  <div class="card kpi"><div class="label">关联联系人无联系方式</div><div class="value">{s['by_type']['linked_no_info']:,}</div></div>
</div>
<div class="card">
  <div class="filters">
    <select id="fType"><option value="">全部类型</option><option value="unregistered">未建档（全名）</option><option value="surname_only">未建档（仅姓氏）</option><option value="no_info">已建档无联系方式</option><option value="linked_no_info">关联联系人无联系方式</option></select>
    <select id="fWho"><option value="">全部记录人</option></select>
    <select id="fYear"><option value="">全部年份</option></select>
    <input type="text" id="fQ" placeholder="客户 / 联系人 / 内容关键词">
    <button class="btn" id="btnCsv">导出当前筛选为 CSV</button>
    <span class="muted small" id="count"></span>
  </div>
</div>
<div class="tabs"><a class="active" data-tab="rows">按工作日志</a><a data-tab="persons">按联系人汇总</a><a data-tab="notes">说明</a></div>
<div class="card" id="tabRows"><div id="rows"></div></div>
<div class="card" id="tabPersons" style="display:none"><div id="persons"></div></div>
<div class="card" id="tabNotes" style="display:none"><ul class="note">
<li>一行 = 一条工作日志里提到的一位联系人；同一人被多条日志提到就有多行，“按联系人汇总”页合并显示。</li>
<li>未建档（全名）：正文里出现姓 + 名，而该客户的联系人表里没有这个人；若其他客户下有同名联系人会注明，可能是同一人挂在了别的客户下。</li>
<li>未建档（仅姓氏）：正文只写了“彭老师”“李总”这类姓氏加称谓，该客户下没有这个姓的联系人，需要业务员补全名。</li>
<li>已建档无联系方式：对上了联系人表里的人（按全名，或姓氏只对应一人），但手机、电话、微信、QQ、邮箱都是空的。</li>
<li>关联联系人无联系方式：这条日志在 CRM 里挂的联系人本身没有任何联系方式。</li>
<li>人名靠规则抽取（姓名 + 称谓、称谓 + 姓名等），会有漏抽和误抽；本公司人员已排除。正文里高亮的是抽到的名字，便于核对。</li>
<li>数据来自 XTools 镜像（每 30 分钟同步）；在 CRM 补录联系方式后，重新生成报表即可更新。</li>
</ul></div>
<script id="data" type="application/json">{data}</script>
<script>
'use strict';
const D = JSON.parse(document.getElementById('data').textContent);
D.rows.forEach((r) => {{ r.text = D.texts[String(r.id)] || ''; }});
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const $ = (s) => document.querySelector(s);
const PAGE = 100;
let page = 1, tab = 'rows';
const whos = [...new Set(D.rows.flatMap((r) => r.who.split('、')))].filter(Boolean).sort();
$('#fWho').innerHTML += whos.map((w) => `<option>${{esc(w)}}</option>`).join('');
const years = [...new Set(D.rows.map((r) => r.date.slice(0, 4)))].sort().reverse();
$('#fYear').innerHTML += years.map((y) => `<option>${{y}}</option>`).join('');
function filtered() {{
  const t = $('#fType').value, w = $('#fWho').value, y = $('#fYear').value, q = $('#fQ').value.trim().toLowerCase();
  return D.rows.filter((r) => (!t || r.type === t) && (!w || r.who.split('、').includes(w)) && (!y || r.date.startsWith(y)) &&
    (!q || (r.customer + ' ' + r.name + ' ' + r.text + ' ' + r.who).toLowerCase().includes(q)));
}}
function highlight(text, name) {{
  const n = name.split(' → ')[0].replace(/(老师|经理|主任|组长|博士|教授|总监|总工|总|工|董|哥|姐|女士|先生|小姐|负责人|工程师|主管|老板)$/, '');
  const h = esc(text);
  if (!n) return h;
  return h.split(esc(n)).join(`<mark>${{esc(n)}}</mark>`);
}}
function renderRows() {{
  const rows = filtered();
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  page = Math.min(page, pages);
  const slice = rows.slice((page - 1) * PAGE, page * PAGE);
  $('#count').textContent = `当前筛选 ${{rows.length.toLocaleString()}} 条`;
  $('#rows').innerHTML = `<table><thead><tr><th>工作日志日期</th><th>销售当事人（记录人）</th><th>联系人</th><th>客户单位</th><th>工作日志内容</th></tr></thead><tbody>
    ${{slice.map((r) => `<tr><td class="nowrap">${{r.date}}<div class="muted small">${{esc(r.kind)}}</div></td><td class="nowrap">${{esc(r.who)}}</td>
      <td class="nowrap"><b>${{esc(r.name)}}</b><div><span class="tag ${{r.type}}">${{D.types[r.type]}}</span></div>${{r.hint ? `<div class="muted small" style="max-width:220px;white-space:normal">${{esc(r.hint)}}</div>` : ''}}</td>
      <td style="max-width:220px">${{esc(r.customer)}}</td><td><div class="text clip">${{highlight(r.text, r.name)}}</div>${{r.text.length > 120 ? '<span class="more">展开</span>' : ''}}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">没有符合条件的记录</td></tr>'}}
    </tbody></table>
    <div class="pager"><span>第 ${{page}} / ${{pages}} 页</span><button class="btn" id="prev" ${{page <= 1 ? 'disabled' : ''}}>上一页</button><button class="btn" id="next" ${{page >= pages ? 'disabled' : ''}}>下一页</button></div>`;
  $('#prev') && $('#prev').addEventListener('click', () => {{ page--; renderRows(); window.scrollTo(0, 0); }});
  $('#next') && $('#next').addEventListener('click', () => {{ page++; renderRows(); window.scrollTo(0, 0); }});
  document.querySelectorAll('.more').forEach((m) => m.addEventListener('click', () => {{ const t = m.previousElementSibling; t.classList.toggle('clip'); m.textContent = t.classList.contains('clip') ? '展开' : '收起'; }}));
}}
function renderPersons() {{
  const t = $('#fType').value, w = $('#fWho').value, q = $('#fQ').value.trim().toLowerCase();
  const list = D.persons.filter((p) => (!t || p.type === t) && (!w || p.who.split('、').includes(w)) && (!q || (p.customer + ' ' + p.name + ' ' + p.who).toLowerCase().includes(q)));
  $('#count').textContent = `当前筛选 ${{list.length.toLocaleString()}} 人`;
  $('#persons').innerHTML = `<table><thead><tr><th>联系人</th><th>类型</th><th>客户单位</th><th class="num">提到次数</th><th>首次</th><th>末次</th><th>记录人</th><th>说明</th></tr></thead><tbody>
    ${{list.map((p) => `<tr><td class="nowrap"><b>${{esc(p.name)}}</b></td><td><span class="tag ${{p.type}}">${{D.types[p.type]}}</span></td><td>${{esc(p.customer)}}</td><td class="num">${{p.count}}</td><td class="nowrap">${{p.first}}</td><td class="nowrap">${{p.last}}</td><td>${{esc(p.who)}}</td><td class="muted small">${{esc(p.hint)}}</td></tr>`).join('') || '<tr><td colspan="8" class="muted">无</td></tr>'}}
    </tbody></table>`;
}}
function render() {{ if (tab === 'rows') renderRows(); else if (tab === 'persons') renderPersons(); }}
document.querySelectorAll('.tabs a').forEach((a) => a.addEventListener('click', () => {{
  tab = a.dataset.tab; document.querySelectorAll('.tabs a').forEach((x) => x.classList.toggle('active', x === a));
  $('#tabRows').style.display = tab === 'rows' ? '' : 'none'; $('#tabPersons').style.display = tab === 'persons' ? '' : 'none'; $('#tabNotes').style.display = tab === 'notes' ? '' : 'none';
  render();
}}));
['#fType', '#fWho', '#fYear'].forEach((s) => $(s).addEventListener('change', () => {{ page = 1; render(); }}));
$('#fQ').addEventListener('input', () => {{ page = 1; render(); }});
$('#btnCsv').addEventListener('click', () => {{
  const rows = filtered();
  const csv = ['工作日志日期,销售当事人（记录人）,联系人,类型,客户单位,说明,工作日志内容', ...rows.map((r) => [r.date, r.who, r.name, D.types[r.type], r.customer, r.hint, r.text].map((v) => '"' + String(v ?? '').replace(/"/g, '""').replace(/\\r?\\n/g, ' ') + '"').join(','))].join('\\n');
  const blob = new Blob(['\\ufeff' + csv], {{ type: 'text/csv;charset=utf-8' }});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = '联系人缺失_工作日志.csv'; a.click();
}});
render();
</script>
</main></body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
