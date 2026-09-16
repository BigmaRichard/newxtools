# newxtools — XTools（超兔）CRM OPEN API 接入包

麦可旺志 Microwants · xtools 优化项目

依据《XToolsCRM OPEN API》文档（2026-09-01 导出，71 个接口）整理的接入准备材料与 Python 客户端。签名算法已用两版文档中的 32 组示例逐一核验；文档版本差异见《docs/00_文档版本变更记录.md》。

## 目录结构

```
newxtools/
├── README.md
├── .env.example              凭证模板（复制为 .env 填写；.env 不入库）
├── requirements.txt / pyproject.toml
├── xtools/                   Python 客户端包
│   ├── client.py             签名、登录、sid 缓存、自动重登、限频、读取分页、错误分类
│   ├── config.py             配置读取（环境变量 / .env）
│   ├── errors.py             异常定义
│   ├── catalog.json          71 个接口的机器可读清单（cmd / dt / act / 模块 / 版本）
│   └── api/                  按模块封装：customers / orders / products / finance / aftersales
├── scripts/
│   ├── smoke_test.py         只读冒烟测试（登录、字典、四模块各读一页）
│   ├── dump_dictionary.py    导出数据字典、字段中文名、人员对照
│   └── export_table.py       按 lastid / lasttime 导出任一表为 JSONL
├── tests/
│   ├── test_sign.py          签名离线测试（文档示例）
│   └── test_client_offline.py 登录 / 重登 / 限频 / 分页 / 错误映射（假服务器）
└── docs/
    ├── 00_文档版本变更记录.md      文档各版本差异与仓库对应调整
    ├── 01_接入准备清单.md          凭证、开通确认、环境、验收标准、风险
    ├── 02_接口机制与签名说明.md    请求结构、签名、会话、分页、写入语义、错误约定
    ├── 03_接口清单.md              71 个接口按模块分组
    ├── 04_首批四模块字段映射.md    客户 / 订单 / 产品 / 财务的字段与枚举
    ├── 05_同步方案设计.md          架构、读取策略、写回流程、阶段计划
    ├── XToolsCRM_OPEN_API_参考_20260901.md   原文档整理版（逐接口）
    └── XTools接入架构泳道全景图.html / .pdf
```

## 快速开始

安装依赖并运行离线测试（不需要凭证）：

```
cd newxtools && python3 -m pip install -r requirements.txt && python3 -m pytest tests -q
```

复制 `.env.example` 为 `.env`，填入 XTools 提供的六项凭证后运行只读冒烟测试：

```
cd newxtools && python3 scripts/smoke_test.py --verbose
```

## 代码示例

```python
from xtools import XTools, XToolsBusinessError

xt = XTools()                                   # 读取 .env / 环境变量

# 增量读取客户（含扩展字段与联系人）
for c in xt.customers.iter(lasttime="2026-09-01 00:00:00"):
    print(c["id"], c["sn"], c["cu_name"])

# 数据字典与人员对照
stages = xt.customers.dictionary("cu_status")
users = xt.client.users()

# 写入客户（失败时抛 XToolsBusinessError，msg 为 CRM 返回原因）
try:
    ret = xt.customers.create({
        "cu_name": "示例客户", "sn": "MW-C-000001", "life": "1",
        "contact": [{"name": "联系人", "mphone": "13800000000"}],
    })
except XToolsBusinessError as exc:
    print("写入失败：", exc.msg)

# 2026-09-01 版新增：修改联系人（不能带 cu_sn）、读取退货单
xt.customers.update_contact({"id": 30735, "mphone": "13800138000"})
for r in xt.orders.returns():
    print(r["id"], r["status"], r["st_libin"])

# 任意接口的直接调用
ret = xt.client.call("api.output", {"dt": "opport", "lastid": 0, "extend": 1})
```

## 凭证说明

网页登录账号密码不能用于 Open API。需向 XTools 客户专员申请开通并取得：appid、appkey、comkeyid、comkey、com、part。详见《docs/01_接入准备清单.md》第 2 节。
