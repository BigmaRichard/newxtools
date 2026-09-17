#!/usr/bin/env python3
"""联调回环测试（写入 → 回读核对），用于测试公司，覆盖首批四个模块各一条记录。

用法：
    python scripts/roundtrip_test.py                 # 在测试公司执行（默认拒绝正式公司 pc7699）
    python scripts/roundtrip_test.py --prefix MWT2   # 换一组编号再跑一遍
    python scripts/roundtrip_test.py --allow-production   # 明确允许在正式公司执行（不建议）

步骤（每步先按编号查重，已存在则跳过写入，直接回读）：
    1. 字典：客户来源 cu_from、产品单位 unit、回款付款方式 type
    2. 产品写入 → 按 sn 回读
    3. 企业客户写入（含 1 个联系人）→ 按 sn 回读（extend=1）
    4. 联系人修改（2026-09-01 版新增接口）→ 回读核对手机号
    5. 客户修改（备注）→ 回读核对
    6. 订单写入（1 条明细，引用上面的产品与客户）→ 按 No. 回读（extend=1）
    7. 回款记录写入（引用订单，memo 作唯一键）→ 按 memo 回读
    8. 汇总：各步结果、CRM 返回的 id、失败原因

说明：OPEN API 没有删除接口，写入的测试数据会留在测试公司；所有编号以 --prefix 开头，便于在 CRM 中识别。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xtools import XTools, XToolsBusinessError, XToolsConfig, XToolsError  # noqa: E402

PRODUCTION_COM = "pc7699"


class Report:
    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []

    def add(self, step: str, ok: bool, detail: str = "") -> None:
        self.rows.append({"step": step, "ok": ok, "detail": detail})
        print(f"[{'通过' if ok else '失败'}] {step}{'：' + detail if detail else ''}")

    def summary(self) -> int:
        failed = [r for r in self.rows if not r["ok"]]
        print("\n" + "=" * 60)
        print(f"回环测试结束：{len(self.rows) - len(failed)} 项通过，{len(failed)} 项失败")
        for r in failed:
            print(f"  - {r['step']}：{r['detail']}")
        return 1 if failed else 0


def first_key(items: List[Dict[str, Any]], default: Optional[str] = None) -> Optional[str]:
    """取字典中第一个可用（USE / Default）的 key。"""
    for it in items:
        flag = str(it.get("flag", "")).upper()
        if flag in ("USE", "DEFAULT"):
            return str(it.get("key"))
    return str(items[0]["key"]) if items else default


def safe_dictionary(xt: XTools, dt_name: str, field: str) -> List[Dict[str, Any]]:
    try:
        return xt.client.dictionary(dt_name, field)
    except XToolsError as exc:
        print(f"      字典 {dt_name}.{field} 读取失败（继续）：{exc}")
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description="XTools OPEN API 联调回环测试（写入 → 回读）")
    parser.add_argument("--prefix", default="MWT", help="测试编号前缀，缺省 MWT")
    parser.add_argument("--allow-production", action="store_true", help="允许在正式公司执行")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    config = XToolsConfig.from_env()
    if config.com == PRODUCTION_COM and not args.allow_production:
        print(f"当前 XTOOLS_COM={config.com} 为正式公司，本脚本会写入测试数据，已拒绝执行；如确需执行请加 --allow-production。")
        return 2
    print("配置：", json.dumps(config.masked(), ensure_ascii=False))

    p = args.prefix
    today = dt.date.today().isoformat()
    ids: Dict[str, Any] = {}
    prod_sn, cust_sn, order_no, receipt_memo = f"{p}-P0001", f"{p}-C0001", f"{p}-DD0001", f"{p}-RT-0001"
    rep = Report()
    xt = XTools(config)

    # 1. 字典
    try:
        cu_from = first_key(safe_dictionary(xt, "customer", "cu_from"), "1")
        unit = first_key(safe_dictionary(xt, "product", "unit"))
        pay_type = first_key(safe_dictionary(xt, "gathering_note", "type"), "1")
        rep.add("1 字典读取", True, f"cu_from={cu_from} unit={unit} 付款方式={pay_type}")
    except XToolsError as exc:
        rep.add("1 字典读取", False, str(exc))
        return rep.summary()

    # 2. 产品
    try:
        existing = xt.products.get(sn=prod_sn)
        if existing:
            ids["product"] = existing["id"]
            rep.add("2 产品写入", True, f"已存在，跳过写入 id={existing['id']}")
        else:
            data: Dict[str, Any] = {"name": "联调测试产品", "model": "T-1", "sku": "-", "sn": prod_sn, "price": 100, "memo": "OPEN API 联调写入，可删除"}
            if unit:
                data["unit"] = unit
            ret = xt.products.create(data)
            ids["product"] = ret.get("id")
            back = xt.products.get(sn=prod_sn)
            rep.add("2 产品写入", bool(back), f"id={ret.get('id')} msg={ret.get('msg')} 回读 name={back.get('name') if back else None}")
    except XToolsError as exc:
        rep.add("2 产品写入", False, str(exc))

    # 3. 客户 + 联系人
    contact_id: Optional[str] = None
    try:
        back = xt.customers.get(sn=cust_sn)
        if back:
            rep.add("3 客户写入", True, f"已存在，跳过写入 id={back['id']}")
        else:
            data = {
                "cu_name": f"联调测试客户（{p}，可删除）", "sn": cust_sn, "life": "1", "cu_from": cu_from,
                "state": "16", "city": "苏州市", "district": "工业园区", "address": "联调测试地址",
                "cu_remark": "OPEN API 联调写入",
                "contact": [{"id": 0, "name": "联调联系人", "headship": "采购", "mphone": "13800000001", "email": "test@example.com"}],
            }
            ret = xt.customers.create(data)
            back = xt.customers.get(sn=cust_sn)
            rep.add("3 客户写入", bool(back), f"msg={ret.get('msg')} 回读 id={back.get('id') if back else None}")
        if back:
            ids["customer"] = back["id"]
            contacts = back.get("contact") or []
            if isinstance(contacts, dict):
                contacts = list(contacts.values())
            contact_id = str(contacts[0]["id"]) if contacts else None
            print(f"      联系人数={len(contacts)} 首个联系人 id={contact_id}")
    except XToolsError as exc:
        rep.add("3 客户写入", False, str(exc))

    # 4. 联系人修改
    try:
        if not contact_id:
            rep.add("4 联系人修改", False, "未取得联系人 id（客户写入未成功或回读无 contact）")
        else:
            new_phone = "13800000002"
            ret = xt.customers.update_contact({"id": contact_id, "mphone": new_phone, "headship": "采购经理"})
            back = xt.customers.get(sn=cust_sn)
            contacts = (back or {}).get("contact") or []
            if isinstance(contacts, dict):
                contacts = list(contacts.values())
            got = next((c for c in contacts if str(c.get("id")) == contact_id), None)
            ok = bool(got) and str(got.get("mphone")) == new_phone
            rep.add("4 联系人修改", ok, f"msg={ret.get('msg')} 回读 mphone={got.get('mphone') if got else None}")
    except XToolsError as exc:
        rep.add("4 联系人修改", False, str(exc))

    # 5. 客户修改
    try:
        if "customer" not in ids:
            rep.add("5 客户修改", False, "客户不存在")
        else:
            remark = f"联调修改 {today}"
            ret = xt.customers.update({"id": ids["customer"], "cu_remark": remark})
            back = xt.customers.get(sn=cust_sn)
            ok = bool(back) and back.get("cu_remark") == remark
            rep.add("5 客户修改", ok, f"msg={ret.get('msg')} 回读 cu_remark={back.get('cu_remark') if back else None}")
    except XToolsError as exc:
        rep.add("5 客户修改", False, str(exc))

    # 6. 订单
    try:
        back = xt.orders.get(no=order_no)
        if back:
            ids["order"] = back["id"]
            rep.add("6 订单写入", True, f"已存在，跳过写入 id={back['id']}")
        else:
            data = {
                "subject": f"联调测试订单 {p}", "cu_sn": cust_sn, "No.": order_no, "sum": "200", "who": config.part,
                "memo": "OPEN API 联调写入", "name": "联调联系人", "tel": "13800000002", "addr": "联调测试地址",
                "date": today, "end_date": today,
                "goods": [{"id": 0, "prod": prod_sn, "amount": "2", "un_price": "100", "sum": "200", "tax_money": "0", "memo": "联调明细"}],
            }
            ret = xt.orders.create(data)
            back = xt.orders.get(no=order_no)
            goods = (back or {}).get("goods") or []
            if isinstance(goods, dict):
                goods = list(goods.values())
            ok = bool(back) and len(goods) == 1
            if back:
                ids["order"] = back["id"]
            rep.add("6 订单写入", ok, f"msg={ret.get('msg')} 回读 id={back.get('id') if back else None} 明细数={len(goods)} 金额={back.get('sum') if back else None}")
    except XToolsError as exc:
        rep.add("6 订单写入", False, str(exc))

    # 7. 回款记录
    try:
        found = list(xt.client.output("gathering_note", memo=receipt_memo))
        if found:
            rep.add("7 回款记录写入", True, f"已存在，跳过写入 id={found[0].get('id')}")
        else:
            data = {"cu_sn": cust_sn, "date": today, "invoice": "2", "serial": 1, "money": "200", "type": pay_type, "who": config.part, "memo": receipt_memo}
            if "order" in ids:
                data["co_id"] = ids["order"]
            ret = xt.finance.create_receipt(data)
            found = list(xt.client.output("gathering_note", memo=receipt_memo))
            ok = bool(found) and str(found[0].get("money", "")).startswith("200")
            rep.add("7 回款记录写入", ok, f"id={ret.get('id')} msg={ret.get('msg')} 回读 money={found[0].get('money') if found else None}")
    except XToolsError as exc:
        rep.add("7 回款记录写入", False, str(exc))

    print("\n写入的记录 id：", json.dumps(ids, ensure_ascii=False))
    return rep.summary()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except XToolsBusinessError as exc:
        print("业务错误：", exc)
        sys.exit(1)
