# newxtools — XTools（超兔）CRM OPEN API 接入包

麦可旺志 Microwants · xtools 优化项目

依据《XToolsCRM OPEN API》文档（2026-09-01 导出，71 个接口）整理的接入准备材料与 Python 客户端。签名算法已用两版文档中的 32 组示例逐一核验；文档版本差异见《docs/00_文档版本变更记录.md》。

## 目录结构

```
newxtools/
├── README.md
├── .env.example              凭证模板（复制为 .env 填写；.env 不入库）
├── requirements.txt / pyproject.toml
├── xtools/                   Python 客户端包（接入层）
│   ├── client.py             签名、登录、sid 缓存、自动重登、限频、读取分页、错误分类
│   ├── config.py             配置读取（环境变量 / .env）
│   ├── errors.py             异常定义
│   ├── catalog.json          71 个接口的机器可读清单（cmd / dt / act / 模块 / 版本）
│   └── api/                  按模块封装：customers / orders / products / finance / aftersales
├── sync/                     P0 只读镜像（同步层 + 存储层）
│   ├── specs.py              各表同步规格（模式、列、子表、重拉条件）
│   ├── store.py              SQLite：原始 JSON 表、规范化表、游标、字典、报表视图
│   └── engine.py             全量 / 增量 / 定期重拉 / 删除检测 / 字典刷新
├── web/                      本地前台（只读 HTTP 服务 + 单页界面）
│   ├── server.py             JSON API：总览 / 订单 / 客户 / 应收回款 / 工作日志；路由与导出下载
│   ├── auth.py               访问控制：来源网段（本机 / Tailscale）+ Basic 认证（手机访问用）
│   ├── reports.py            0.5 分析接口：销售分析、客户分析、业务员看板、产品与库存、采购与付款、现金流、联系人
│   ├── export.py             导出 Excel：各列表的列定义与取数
│   ├── xlsx.py               纯标准库 .xlsx 写入器
│   ├── names.py              行动记录正文里的人名抽取（规则法，jieba 可选）
│   └── static/index.html     页面（无外部依赖）
├── scripts/
│   ├── smoke_test.py         只读冒烟测试（登录、字典、四模块各读一页）
│   ├── roundtrip_test.py     联调回环测试：测试公司内写入产品 / 客户 / 联系人 / 订单 / 回款并回读核对（可重复执行）
│   ├── sync.py               只读镜像 CLI：--init / 增量 / --full / --status / --dict / --rebuild
│   ├── web.py                本地前台：http://127.0.0.1:8790（--host 0.0.0.0 供手机经 Tailscale 访问）
│   ├── report_missing_contacts.py  专项报表：工作日志里提到但缺少联系方式的联系人（HTML）
│   ├── install_launchd.py    Mac launchd：同步定时任务（每 30 分钟）/ --web 前台常驻
│   ├── dump_dictionary.py    导出数据字典、字段中文名、人员对照
│   └── export_table.py       按 lastid / lasttime 导出任一表为 JSONL
├── tests/
│   ├── test_sign.py          签名离线测试（文档示例）
│   ├── test_client_offline.py 登录 / 重登 / 限频 / 分页 / 错误映射（假服务器）
│   ├── test_sync_offline.py  镜像：全量 / 增量 / 断点续拉 / 删除检测 / 视图 / 字典（内存假数据）
│   ├── test_web_offline.py   前台 API（小型镜像库，含 0.5 分析接口与导出）
│   ├── test_xlsx.py          .xlsx 写入器
│   ├── test_web_auth.py      访问控制与安装脚本生成的访问密码
│   └── test_names.py         人名抽取规则
└── docs/
    ├── 00_文档版本变更记录.md      文档各版本差异与仓库对应调整
    ├── 01_接入准备清单.md          凭证、开通确认、环境、验收标准、风险
    ├── 02_接口机制与签名说明.md    请求结构、签名、会话、分页、写入语义、错误约定
    ├── 03_接口清单.md              71 个接口按模块分组
    ├── 04_首批四模块字段映射.md    客户 / 订单 / 产品 / 财务的字段与枚举
    ├── 05_同步方案设计.md          架构、读取策略、写回流程、阶段计划
    ├── 06_P0只读镜像使用说明.md    运行命令、同步策略、库结构与视图、常见问题
    ├── 07_本地前台使用说明.md      安装、页面、数据口径、接口
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

在测试公司做写入回环（产品 → 客户与联系人 → 联系人修改 → 客户修改 → 订单 → 回款，全部回读核对；正式公司默认拒绝执行）：

```
cd newxtools && python3 scripts/roundtrip_test.py
```

P0 只读镜像：首次全量并安装每 30 分钟一次的定时增量（详见《docs/06_P0只读镜像使用说明.md》）：

```
cd newxtools && .venv/bin/python scripts/sync.py --init; .venv/bin/python scripts/install_launchd.py
```

本地前台：安装为常驻服务并在浏览器打开（详见《docs/07_本地前台使用说明.md》）：

```
cd newxtools && .venv/bin/python scripts/install_launchd.py --web && open http://127.0.0.1:8790
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
