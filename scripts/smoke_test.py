#!/usr/bin/env python3
"""联调冒烟测试：验证凭证、签名、登录、会话复用与基础读取。

用法：
    python scripts/smoke_test.py            # 只读，不写入数据
    python scripts/smoke_test.py --verbose  # 打印每一步的原始响应

前置：仓库根目录存在 .env（参考 .env.example）。
检查项：
    1. 配置完整性（不打印密钥）
    2. 登录：取得 sid（10 秒内重复运行会复用缓存 sid）
    3. 用户读取（dt=user）
    4. 字段信息：人员对照（pr2nm）、客户表字段名（dbcn）、客户阶段字典（cu_status）
    5. 四个首批模块各读一页：customer / contract / product / gathering_note
    6. 报告：每步耗时、记录数、异常
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xtools import XTools, XToolsConfig, XToolsError  # noqa: E402


def step(title: str, func, *, verbose: bool = False):
    started = time.time()
    try:
        result = func()
    except XToolsError as exc:
        print(f"[失败] {title}：{exc}")
        if verbose and getattr(exc, "raw", None) is not None:
            print("       原始响应：", json.dumps(exc.raw, ensure_ascii=False)[:800])
        return None
    elapsed = time.time() - started
    summary = result if isinstance(result, str) else _summarize(result)
    print(f"[通过] {title}（{elapsed:.2f}s）{summary}")
    if verbose and not isinstance(result, str):
        print("       ", json.dumps(result, ensure_ascii=False)[:1200])
    return result


def _summarize(result) -> str:
    if isinstance(result, list):
        return f"：{len(result)} 条"
    if isinstance(result, dict):
        return f"：{len(result)} 个键"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="XTools OPEN API 冒烟测试（只读）")
    parser.add_argument("--verbose", action="store_true", help="打印原始响应")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        config = XToolsConfig.from_env()
    except XToolsError as exc:
        print(f"[失败] 配置：{exc}")
        return 2
    print("[通过] 配置：", json.dumps(config.masked(), ensure_ascii=False))

    xt = XTools(config)
    sid = step("登录（user.login）", lambda: xt.login(), verbose=args.verbose)
    if not sid:
        print("登录失败，后续检查跳过。请核对 appid / appkey / comkeyid / comkey / com / part，并确认服务器时间偏差在允许范围内。")
        return 1
    print(f"       sid 前 6 位：{sid[:6]}…（缓存于 {config.sid_cache}）")

    step("用户读取（dt=user）", lambda: xt.client.output("user", lastid=0), verbose=args.verbose)
    step("人员对照（api.fieldinfo act=pr2nm）", lambda: xt.client.users(), verbose=args.verbose)
    step("客户表字段名（api.fieldinfo act=dbcn）", lambda: xt.customers.field_names(), verbose=args.verbose)
    step("客户阶段字典（api.fieldinfo field=cu_status）", lambda: xt.customers.dictionary("cu_status"), verbose=args.verbose)
    step("客户读取一页（dt=customer, extend=1）", lambda: xt.customers.list(lastid=0), verbose=args.verbose)
    step("订单读取一页（dt=contract, extend=1）", lambda: xt.orders.list(lastid=0), verbose=args.verbose)
    step("产品读取一页（dt=product）", lambda: xt.products.list(lastid=0), verbose=args.verbose)
    step("回款记录一页（dt=gathering_note）", lambda: xt.client.output("gathering_note", lastid=0), verbose=args.verbose)
    step("订单退货单一页（dt=libreturn，2026-09-01 版新增）", lambda: xt.client.output("libreturn", lastid=0), verbose=args.verbose)
    step("发货通知单一页（dt=sr_notice，未开通外部库存时预期失败）", lambda: xt.client.output("sr_notice", lastid=0), verbose=args.verbose)
    print("冒烟测试结束。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
