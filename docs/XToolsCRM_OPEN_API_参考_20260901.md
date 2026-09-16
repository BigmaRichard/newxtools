# XToolsCRM OPEN API 参考（整理版）

麦可旺志 Microwants · xtools 优化项目 · 整理日期 2026-09-16

来源：apizza 导出文件《OPEN API_20260901.html》（XToolsCRM OPEN API，2026-09-01）。本文按原文档逐接口整理，仅调整排版、未改动参数与说明内容；文档原有的拼写与不一致之处保留原样，另见《01_接入准备清单》风险 R7。统一入口 `POST https://crm.xtcrm.com/open/index.xt`。与上一版（2026-05-22）的差异见《00_文档版本变更记录》。

## 目录

1. 登录接口（user.login）
2. 用户读取接口（api.output · dt=user）
3. 客户读取接口（api.output · dt=customer）
4. 客户自定义字段数据读取接口（api.output · dt=customerext）
5. 客户转移接口（api.chgown · dt=customer）
6. 企业客户写入接口（api.input · dt=customer）
7. 企业客户修改接口（api.update · dt=customer）
8. 企业客户自定义字段数据写入接口（api.input · dt=customerext）
9. 联系人修改接口（api.update · dt=contact）（本版新增）
10. 个人客户写入接口（api.input · dt=cuview）
11. 订单写入接口（api.input · dt=contract）
12. 订单读取接口（api.output · dt=contract）
13. 订单修改接口（api.update · dt=contract）
14. 订单分批发货（不计算库存的商品）接口（api.cmdact · dt=contract · act=sendGoods_no_stock）
15. 订单自定义明细读取接口（api.cmdact · dt=contract · act=getOtherItems）
16. 采购单写入接口（api.input · dt=purchase）
17. 采购单读取接口（api.output · dt=purchase）
18. 付款计划读取接口（api.output · dt=pay_plan）
19. 付款计划写入接口（api.input · dt=pay_plan）
20. 报价单写入接口（api.input · dt=price）
21. 报价单修改接口（api.update · dt=price）
22. 行动记录写入接口（api.input · dt=action）
23. 行动记录读取接口（api.output · dt=action）
24. 维修工单写入接口（api.input · dt=repairinfo）
25. 维修工单读取接口（api.output · dt=repairinfo）（本版有变更）
26. 计划回款读取接口（api.output · dt=gathering）
27. 计划回款修改接口（api.update · dt=gathering）
28. 计划回款写入接口（api.input · dt=gathering）
29. 回款记录写入接口（api.input · dt=gathering_note）
30. 回款记录读取接口（api.output · dt=gathering_note）
31. 开票记录写入接口（api.input · dt=bill）
32. 销售机会读取接口（api.output · dt=opport）
33. 流程读取接口（api.output · dt=process_exec）
34. 附件读取接口（api.downfile · dt=customer）
35. 批单报销修改接口（api.update · dt=cost）
36. 批单报销读取接口（api.output · dt=cost）
37. 费用明细读取接口（api.output · dt=costdetail）
38. 出差读取接口（api.output · dt=b_trip）
39. 项目读取接口（api.output · dt=project）
40. 入库单写入接口（api.input · dt=libin）
41. 入库单完成入库接口（api.cmdact · dt=libin · act=libinok）
42. 出库单读取接口（api.output · dt=libout）
43. 出库单写入接口（api.input · dt=libout）
44. 出库单完成出库接口（api.cmdact · dt=libout · act=liboutok）
45. 发货单读取接口（api.output · dt=sendgoods）
46. 产品表读取接口（api.output · dt=product）
47. 产品写入接口（api.input · dt=product）
48. 产品修改接口（api.update · dt=product）
49. 产品客制别名读取接口（api.output · dt=prod_alias）
50. 产品客制别名写入接口（api.input · dt=prod_alias）
51. 产品价格策略变更接口（api.cmdact · dt=product · act=chg_str_ps）
52. 产品分类写入接口（api.input · dt=csstree）
53. 产品分类读取接口（api.output · dt=csstree）
54. 收发货通知单读取接口（api.output · dt=sr_notice）
55. 收发货通知单状态变更接口（api.cmdact · dt=sr_notice · act=chgst）
56. 收发货通知单执行接口（api.cmdact · dt=sr_notice · act=exc）
57. 外部库存变更接口（api.cmdact · dt=libn · act=erp_libn）
58. 合同读取接口（api.output · dt=contract0）
59. 合同写入接口（api.input · dt=contract0）
60. 字段信息（数据字典）读取接口（api.fieldinfo · dt=customer）
61. 字段信息（字段名称）读取接口（api.fieldinfo · dt=customer · act=dbcn）
62. 字段信息（用户）读取接口（api.fieldinfo · dt=customer · act=pr2nm）
63. 领料单预生成接口（api.cmdact · dt=mes_process · act=preview）
64. 生产工艺工序（api.output · dt=mes_flow）
65. 获客线索读取接口（api.output · dt=jk_collect）
66. 获客线索写入接口（api.input · dt=jk_collect）
67. 开票申请的开票动作接口（api.cmdact · dt=bill_apply · act=kaipiao）
68. 发货单修改接口（api.update · dt=sendgoods）
69. 下游询价记录写入接口（api.input · dt=ask_price_note）
70. 采购退货单读取接口（api.output · dt=purreturn）（本版新增）
71. 订单退货单读取接口（api.output · dt=libreturn）（本版新增）


## 1. 登录接口

- 模块：基础 · cmd：`user.login`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | user.login |
| appid | string | 是 | 开发公司的应用ID，由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1527746854 |
| upr | json | 是 | 用户的登录信息 | 见下方示例 |
| param | json | 是 | 主要参数主体，登录时为空数组，无内容 | [] |
| md | string | 是 | 参数合法性校验码 | d9a145ef66734897f0f38dd42a471873 |

upr 示例：

```
{ "comkeyid":"xtoolsplusd002",//XTools公司分配给客户公司的comkeyid "com":"d002",//XToolsCRM系统中的客户公司内部编码 "part":"",//XToolsCRM系统中的客户公司的登录人part，不输入缺省为B1 "md":"d79d4e33a7771d8f0473f1bc0bd12f8e"//登录验证码 }
```

### 详细说明

```
登录参数说明：
{
"comkeyid":"xtoolsplusd002",//XTools公司分配给客户公司的comkeyid
"com":"d002", //XToolsCRM系统中的客户公司内部编码
 "part":"",//XToolsCRM系统中的客户公司的登录人part，不输入缺省为B1
"md":"d79d4e33a7771d8f0473f1bc0bd12f8e"//登录验证码
}

upr中的md计算方法为：（时间戳stamp+客户公司key+公司内部编码com+
登录人part)这个字符串的md5值
md的计算用例如下：
time:1527746854
comkey:xtoolsplusd002sjsjsj
com:d002
part:
计算md5前字符串:1527746854xtoolsplusd002sjsjsjd002
md5值:d79d4e33a7771d8f0473f1bc0bd12f8e

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
md的计算用例如下：
cmd:user.login
time:1527746854
appid:open00001_sajdjsjsj
appkey:open1slslslsdldlsdlds
param :[]
upr :{"comkeyid":"xtoolsplusd002","com":"d002","part":"","md":"d79d4e33a7771d8f0473f1bc0bd12f8e"}
生成字符串：
[]1527746854{"comkeyid":"xtoolsplusd002","com":"d002","part":"","md":"d79d4e33a7771d8f0473f1bc0bd12f8e"}user.loginopen1slslslsdldlsdlds
md5结果：d9a145ef66734897f0f38dd42a471873

注意：
登录接口10秒内只能调用一次，频繁调用会提示错误：
{
"ok":0,
"err":{"errno":30103,"errmsg":"请勿频繁登录，请尽量用SID访问接口"}
}
	登录接口返回的sid将用于其他接口的登录信息校验，sid 原则上是第二天凌晨服务器重启时才失效。但特殊情况，如系统重启或者用户操作了踢掉所有用户，则sid就会失效。为了安全期间，sid以30分钟有效期为准。
如果接口返回以下内容，则说明sid失效，需要重新登录：
{
 "ok":0,
 "err":{"errno":20101,"errmsg":"session已经失效，请进行重新登录!"}
 }
或
{
 "ok":0,
 "err":{"errno":20102,"errmsg":"session已经失效，请进行重新登录!"}
 }
即：需要重新登录的条件为：返回结果 为 ok 等于0 并且 err.errno为20101或20102 的情况下，需再次登录。
```

### 返回示例

```
                                {
    “ok”:1, //接口是否调用成功，1:接口成功，0:接口失败
    "ret":{
        "com":"d002",
        "part":"B1",
        "sid":"0391e431e97a5e79014242261f9ac6be",
        ...
    }
    
}
                            
```

## 2. 用户读取接口

- 模块：基础 · cmd：`api.output` · dt：`user`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549876028 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"4abda94f27512666f079e288ab44a287",//登录接口返回的sid } |
| param | json | 是 | 数据的读取参数 | {  	"dt":"user","lastid":0,"id":    10 } |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

### 详细说明

```
upr参数说明：在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。
{
"sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid
}

param参数说明：
{ "dt":"user",////读取数据的分类，user代表用户信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

md的计算逻辑：
假定参数对应数值如下：
param:{"dt":"user","lastid":0}
stamp:1552028002
upr: {"sid":"b56561c28a6bec6257e5a5916000837e"}
cmd: api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"user","lastid":0}1552028002{"sid":"b56561c28a6bec6257e5a5916000837e"}api.outputopen1slslslsdldlsdlds
md计算结果:8a4c78a92d67f09a0eaee3334aa8feb6

用户信息说明：
{
  'id' => string '10' (用户ID）
 'user' => string 'dhty' (用户登录名）
 'part' => string 'M9' (用户内部唯一管理代码Part)
 'name' => string '东皇太一1234567890qwertyuiopasdfghjk' (用户名字)
 'dept' => int 10000 (用户部门ID)
 'status' => string '0' (用户状态 0正常，1离职）
 'type' => string '1' (用户级别，0老板，1主管，2一般人员)
 'isadmin' => string '1' (是否有管理权限)
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 用户读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条用户数据
            [{用户1},{用户2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 3. 客户读取接口

- 模块：客户与联系人 · cmd：`api.output` · dt：`customer`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549876028 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"4abda94f27512666f079e288ab44a287",//登录接口返回的sid } |
| param | json | 是 | 客户的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{  	"dt":"customer",//读取数据的分类，customer代表客户信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
upr参数说明：在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。
{
"sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid
}

param参数说明：
{ "dt":"customer",//读取数据的分类，customer代表客户信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"extend":1,//客户扩展字段的读取， 0：主要信息读取， 1：增加扩展字段展示
"lasttime":"2019-12-31 12:01:15",//最后修改时间或者添加时间，本参数接受2种类型的数据，时间字符串或者时间戳 如：2019-12-31 12:01:15 = 1577764875
"life":"2,3",//生命周期的过滤条件，参数可选，需要的话，写入筛选值，多个用英文逗号隔开// 1:潜在;2:签约;3:重复购买;4:失效
"id":  10,//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
"type":1,//客户种类的过滤条件，读取客户种类字段内容，请参考字段信息（数据字典）读取接口
"cu_status":1,//客户阶段的过滤条件，读取客户阶段字段内容，请参考字段信息（数据字典）读取接口
"employees":4,//人员规模的过滤条件，读取人员规模字段内容，请参考字段信息（数据字典）读取接口
"name":"飞奥德",//根据名称读取客户信息
"sn":"CJKH000781",//客户编码查询
}

md的计算逻辑：
假定参数对应数值如下：
param:{"dt":"customer","id":10}
stamp:1549876028
upr:{"sid":"4abda94f27512666f079e288ab44a287"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"customer","id":10}1549876028{"sid":"4abda94f27512666f079e288ab44a287"}api.outputopen1slslslsdldlsdlds
md计算结果:79bdc07d245290beea7da0c9ec0fbb58

单条客户数据说明：
array (size=9)
 'id' => string '16864' ,//客户CRM内部ID
 'cu_name' => string '北京希艾欧管理技术有限公司' ，//客户名称
 'life' => string '1' ,//生命周期
 'sn' => string 'CU0001' ,//客户编码
 'address' => string '' ,//客户地址
 'cu_remark' => string '' ,//备注
 'cu_from' => string '5' ,//客户来源
'state' => string '9' ,//省份 1:安徽;2:北京;3:重庆;4:福建;5:甘肃;6:广东;7:广西;8:贵州;9:海南;10:河北;11:河南;12:黑龙江;13:湖北;14:湖南;15:吉林;16:江苏;17:江西;18:辽宁;19:内蒙古;20:宁夏;21:青海;22:山东;23:山西;24:陕西;25:上海;26:四川;27:天津;28:西藏;29:新疆;30:云南;31:浙江;32:香港;33:澳门;34:台湾;35:其它;
'city' => string '三沙市' ,//地级城市
'district' => string '西沙群岛' ,//区县
rala_rating' => string '3', //关系等级
'qydate' => string '2018-10-25', //首次签约日期
'creatdate' => string '2016-06-24', //创建日期
'moddate' => string '2022-12-01', //修改日期
 'tianyancha' => //下面信息为天眼查工商信息
 array (size=14)
 '企业名称' => string '北京希艾欧管理技术有限公司' (length=39)
 '注册号' => string '110108005508478' (length=15)
 '注册地址' => string '北京市海淀区中关村北大街178号二层201A' (length=52)
 '法人' => string '姚乐' (length=6)
 '经营状态' => string '在业' (length=6)
 '成立时间' => string '2003-03-03' (length=10)
 '注册资本' => string '101.01万人民币' (length=18)
 '经营范围' => string '技术开发、技术咨询、技术转让、技术服务、技术推广；计算机技术培训；基础软件服务；应用软件服务；计算机系统服务；会议服务；设计、制作、代理、发布广告。（企业依法自主选择经营项目，开展经营活动；依法须经批准的项目，经相关部门批准后依批准的内容开展经营活动；不得从事本市产业政策禁止和限制类项目的经营活动。）' (length=453)
 '行业' => string '科技推广和应用服务业' (length=30)
 '企业类型' => string '有限责任公司(自然人投资或控股)' (length=44)
 '组织机构代码' => string '747509796' (length=9)
 '统一信用代码' => string '91110108747509796U' (length=18)
 '登记机关' => string '北京市工商行政管理局海淀分局' (length=42)
 '核准时间' => string '2019-06-26' (length=10)
 'contact' => //下面为联系人信息
 array (size=1)
 0 =>
 array (size=6)
 'id' => string '10130' ,//联系人CRM ID
 'name' => string 'zhangsnal' ,//联系人姓名
'headship' => string '老板', //联系人职务
 'mphone' => string '' ,//电话号码
 'qq' => string '',//联系人qq
 'weixin' => string '' ,//联系人微信
 'email' => string '' ,//联系人email
 'sex' => string '2', //性别 2:男;1:女
 'islinkman' => string '0' //类型 0:联系人;1:主联系人;2:#个人客户;3:离职

扩展功能说明：
参数需要加入：extend=1

读取接口扩展字段信息说明：
'type' => '3'， //客户种类
'period' => '1' ,//客户阶段
'uid' => '3'， //上级客户ID
'info' => '该公司的公司简介内容',//扩展字段 公司简介内容
'tel' => '19973607343',//扩展字段 电话
'web' => 'www.xtools.cn',//扩展字段 网址
'country' => 28,//扩展字段 国家或地区 缺省是 中国 28
'industry' => 2,//扩展字段 行业 自定义设置内容
'employees' => 1,//扩展字段 人员规模 自定义设置内容
'm_name'=>'客户简称',//扩展字段 客户简称
'rala_rating' =>'3', //关系等级
'qydate' =>'2018-10-25', //首次签约日期
'bill_content'=>'开票信息',//开票信息
扩展数据展示内容如下：
array (size=23)
       'id' => string '10' (length=2) //客户ID
       'cu_name' => string '企业客户3' (length=13)//客户名称
       'life' => string '3' (length=1)//生命周期
       'sn' => string '00003' (length=5)//客户编码
       'cu_remark' => string '' (length=0)//备注
       'cu_from' => string '1' (length=1)//来源
       'state' => string '2' (length=1)//省份
       'city' => string '北京市' (length=9)//城市
       'district' => string '海淀区' (length=9)//地区
       'address' => string '' (length=0)//地址
       'type' => string '3' (length=1)//客户种类
       'owner' => string 'M36' (length=3)//客户所有者
       'period' => string '1' (length=1)//客户阶段
       'uid' => string '9' (length=1)//上级客户
       'info' => string '水电费盛大发售的' (length=24)//客户简介
       'tel' => string '' (length=0)//客户电话
       'web' => string '' (length=0)//网址
       'country' => string '28' (length=2)//国家
       'industry' => string '1' (length=1)//行业
       'employees' => string '4' (length=1)//人员规模
       'm_name' => string '企业客户3' (length=13)//简称,
       'rala_rating' => string '3', //关系等级
       'qydate' => string '2018-10-25', //首次签约日期
       'creatdate' => string '2016-06-24', //创建日期
       'moddate' => string '2022-12-01', //修改日期
       'tianyancha' => //天眼查信息
        array (size=0)
         empty
       'contact' => //对应联系人管理的数组对象
        array (size=1)
         0 =>
          array (size=7)
           'id' => string '11' (length=2)//联系人ID
           'name' => string '联系人-企业客户3' (length=23)//联系人名称
           'headship' => string '老板' (length=6)//职务
           'mphone' => string '123133' (length=6)//电话
           'qq' => string '' (length=0)//联系人QQ
           'weixin' => string '' (length=0)//联系人微信
           'email' => string '' (length=0)//联系人email地址
           'sex' => string '2', //性别 2:男;1:女
           'islinkman' => string '0' //类型 0:联系人;1:主联系人;2:#个人客户;3:离职
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 客户读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条客户数据
            [{客户1},{客户2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 4. 客户自定义字段数据读取接口

- 模块：客户与联系人 · cmd：`api.output` · dt：`customerext`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549936788 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"6a44d9130891288eae6bdd5ecd975d59",//登录接口返回的sid } |
| param | json | 是 | 客户扩展接口的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | b914bb54ea40aa9e27bfc696410402d4 |

param 示例：

```
{  	"dt":"customerext",//读取数据的分类，customerext代表客户扩展信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
md参数计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"customerext","id":10}
stamp:1549936788
upr:{"sid":"6a44d9130891288eae6bdd5ecd975d59"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"customerext","id":10}1549936788{"sid":"6a44d9130891288eae6bdd5ecd975d59"}api.outputopen1slslslsdldlsdlds
md计算结果:b914bb54ea40aa9e27bfc696410402d4
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 数据读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条客户扩展数据
            [{客户扩展数据1},{客户扩展数据2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 5. 客户转移接口

- 模块：客户与联系人 · cmd：`api.chgown` · dt：`customer`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.chgown |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549876028 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"4abda94f27512666f079e288ab44a287",//登录接口返回的sid } |
| param | json | 是 | 客户的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{  	"dt":"customer",//表名称，customer代表客户信息  	"id":0,CRM系统中的客户ID,有这个，就不用sn  	"sn":    "T00001"//客户编号，需要转换为客户的ID进行 保存  	"owner":"张三" //可以是业务员名字，或者part}
```

### 详细说明

```
客户转移参数说明：
{
"dt" : "customer",//表名称，customer代表客户信息
"id" : 0, //CRM系统中的客户ID,有这个，就不用sn
"sn" :  "T00001" //客户编号，接口会自动转换为客户的ID进行 处理，id和sn 2个参数用一个即可
"owner": "张三" //可以是业务员名字或者part，接口会自动转换为业务员的 part 进行 保存
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
请参考客户写入接口代码处理
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 客户转移状态，1：转移成功，0：转移失败
        msg:"客户转移成功" //返回文字描述，成功失败，错误提示等
        }
}
                            
```

## 6. 企业客户写入接口

- 模块：客户与联系人 · cmd：`api.input` · dt：`customer`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528078285 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid } |
| param | json | 是 | 写入客户的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 6913de14caa74767e360ce918497e085 |

param 示例：

```
{ "dt":"customer",//写入数据的分类，customer代表客户联系人的写入 "data"://写入数据分类内容 { "id":0,//客户的ID，新建客户的时候ID可以不写或者为0 "cu_name":"中国海上救援大队",//客户名称 "sn":"0067",//客户编号 "address":"中国上海",//地址 "cu_remark":"这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚",//备注 "cu_from":"1",//客户来源 "contact"://本客户的相关联系人，可多个，以数组的形式管理 [//数组主体，下面可输入多个联系人 {"id":0,//联系人ID,添加的时候可没有或输入0 "name":"刘大庆",//联系人姓名 "mphone":"15891023600",//联系人移动电话 "qq":"999999991000234",//联系人QQ "weixin":"wx_91884dx",//联系人微信 "email":"wq@sohu.com"//联系人邮件地址 }, //第二个联系人 {"id":0,//联系人ID，添加的时候可不填或输入0 "name":"留明海",//联系人姓名 "mphone":"15920066999 ",//联系人移动电话 "qq":" ",//联系人QQ "weixin":" ",//联系人微信 "email":" "//联系人邮件地址 } //可加入更多联系人 ] }}
```

### 详细说明

```
写入客户数据的内容
{
"dt":"customer",//写入数据的分类，customer代表客户联系人的写入
"data"://写入数据分类内容
{
"cu_name":"中国海上救援大队",//客户名称
"sn":"0067",//客户编号
"life":"1",//生命周期，缺省也是1， 生命周期的数字描述：1:潜在;2:签约;3:重复购买;4:失效
"address":"中国上海",//地址
"cu_remark":"这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚",//备注
"cu_from":"1",//客户来源
"state":"9",//省份 1:安徽;2:北京;3:重庆;4:福建;5:甘肃;6:广东;7:广西;8:贵州;9:海南;10:河北;11:河南;12:黑龙江;13:湖北;14:湖南;15:吉林;16:江苏;17:江西;18:辽宁;19:内蒙古;20:宁夏;21:青海;22:山东;23:山西;24:陕西;25:上海;26:四川;27:天津;28:西藏;29:新疆;30:云南;31:浙江;32:香港;33:澳门;34:台湾;35:其它;
"city":"三沙市",//地级城市
"district":"西沙群岛",//区县
"contact"://本客户的相关联系人，可多个，以数组的形式管理
[//数组主体，下面可输入多个联系人
{"id":0,//联系人ID,添加的时候可没有或输入0
"name":"刘大庆",//联系人姓名
"headship":"老板", //联系人职务
"mphone":"15891023600",//联系人移动电话
"qq":"999999991000234",//联系人QQ
"weixin":"wx_91884dx",//联系人微信
"email":"wq@sohu.com"//联系人邮件地址
},
//第二个联系人
{"id":0,//联系人ID，添加的时候可不填或输入0
"name":"留明海",//联系人姓名
"headship":"销售经理", //联系人职务
"mphone":"15920066999 ",//联系人移动电话
"qq":" ",//联系人QQ
"weixin":" ",//联系人微信
"email":" "//联系人邮件地址
}
//可加入更多联系人
]
}
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
md的计算用例如下：
cmd:api.input
time:1528078285
appid:open00001_sajdjsjsj
appkey:open1slslslsdldlsdlds
param 字符串:
{"dt":"customer","data":{"id":0,"cu_name":"中国海上救援大队","sn":"0067","address":"中国上海","cu_remark":"这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚","cu_from":"1","contact":[{"id":0,"name":"刘大庆","mphone":"15891023600","qq":"999999991000234","weixin":"wx_91884dx","email":"wq@sohu.com"},{"id":0,"name":"留明海","mphone":"15920066999 ","qq":" ","weixin":" ","email":" "}]}}
upr 字符串:
{"sid":"f6a55a89a2b4ff13be9cd6c147bca9e8"}
生成字符串：
{"dt":"customer","data":{"id":0,"cu_name":"中国海上救援大队","sn":"0067","address":"中国上海","cu_remark":"这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚","cu_from":"1","contact":[{"id":0,"name":"刘大庆","mphone":"15891023600","qq":"999999991000234","weixin":"wx_91884dx","email":"wq@sohu.com"},{"id":0,"name":"留明海","mphone":"15920066999 ","qq":" ","weixin":" ","email":" "}]}}1528078285{"sid":"f6a55a89a2b4ff13be9cd6c147bca9e8"}api.inputopen1slslslsdldlsdlds
md5结果：6913de14caa74767e360ce918497e085

扩展功能说明：
参数需要加入：extend=1

写入扩展字段信息说明：
'type' => '3'， //客户种类
'period' => '1' ,//客户阶段
'uid' => '3'， //上级客户ID
'info' => '该公司的公司简介内容',//扩展字段 公司简介内容
'tel' => '19973607343',//扩展字段 电话
'web' => 'www.xtools.cn',//扩展字段 网址
'country' => 28,//扩展字段 国家或地区 缺省是 中国 28
'industry' => 2,//扩展字段 行业 自定义设置内容
'employees' => 1,//扩展字段 人员规模 自定义设置内容
'm_name'=>'客户简称',//扩展字段 客户简称

客户写入扩展功能参数参考如下：
array("dt"=>"customer",//数据表 customer代表客户写入
"extend"=>1, //是否是扩展写入功能--> 1:是
       "data"=>array(
  "id"=>0,//客户ID 添加的时候，可以不传递
'cu_name'=>'api导入1加类型',//客户名称
'life'=>'1',//生命周期 1:潜在;2:签约;3:重复购买;4:失效
'sn'=>'cs000802',//客户编号
'address'=>'中国上海',//地址
'cu_remark'=>'这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚',//备注
'cu_from'=>'1',//来源
'address' =>'海南省三亚市',
        'cu_from' => '5',
        'state' =>'9',
        'city' =>'三沙市',
        'district' =>'西沙群岛',
'contact'=>array(
array(
'name'=>'刘大2',//联系人姓名
'headship' => '老板', //联系人职务
'mphone'=>'15891023600',//手机
'qq'=>'999999991000234',//QQ
'weixin'=>'wx_91884dx',//微信
'email'=>'wq@sohu.com'//邮箱
),array(
'id'=>0,//联系人ID 添加的时候，可以不传递
'name'=>'留明2',//联系人姓名
'headship' => '经理', //联系人职务
'mphone'=>'15920066999 ',//手机
'qq'=>' ',//QQ
'weixin'=>' ',//微信
'email'=>' '//邮箱
)
),//end 'contact'=>array(
'type'=>2, //扩展字段 客户类型 //潜在客户、普通客户、VIP客户、代理商、合作伙伴、失效客户
'period' =>1,//扩展字段 客户阶段
'uid' => 10,//扩展字段 上级客户ID
'info' => '该公司的公司简介内容',//扩展字段 公司简介内容
'tel' => '19973607343',//扩展字段 电话
'web' => 'www.xtools.cn',//扩展字段 网址
'country' => 28,//扩展字段 国家或地区 缺省是 中国 28
'industry' => 2,//扩展字段 行业 自定义设置内容
'employees' => 1,//扩展字段 人员规模 自定义设置内容
'm_name' => '客户简称',//扩展字段 客户简称
//其他扩展字段
 )//数据
);

备注：
如果想在创建客户的时候，改变所有者，有2种方案：
创建客户后，调用客户转移接口，改变客户所有者。
客户所有者就是open api登录人，可以在登录的接口中，part参数使用客户所有者
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 客户写入状态，1：写入成功，0：写入失败
        msg:’添加客户成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 7. 企业客户修改接口

- 模块：客户与联系人 · cmd：`api.update` · dt：`customer`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.update |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528078285 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid } |
| param | json | 是 | 修改客户的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 6913de14caa74767e360ce918497e085 |

param 示例：

```
{ "dt":"customer",//写入数据的分类，customer代表客户联系人的写入 "data"://写入数据分类内容 { "id":0,//客户的ID，新建客户的时候ID可以不写或者为0 "cu_name":"中国海上救援大队",//客户名称 "sn":"0067",//客户编号 "address":"中国上海",//地址 "cu_remark":"这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚",//备注 "cu_from":"1",//客户来源 "contact"://本客户的相关联系人，可多个，以数组的形式管理 [//数组主体，下面可输入多个联系人 {"id":0,//联系人ID,添加的时候可没有或输入0 "name":"刘大庆",//联系人姓名 "mphone":"15891023600",//联系人移动电话 "qq":"999999991000234",//联系人QQ "weixin":"wx_91884dx",//联系人微信 "email":"wq@sohu.com"//联系人邮件地址 }, //第二个联系人 {"id":0,//联系人ID，添加的时候可不填或输入0 "name":"留明海",//联系人姓名 "mphone":"15920066999 ",//联系人移动电话 "qq":" ",//联系人QQ "weixin":" ",//联系人微信 "email":" "//联系人邮件地址 } //可加入更多联系人 ] }}
```

### 详细说明

```
功能说明：
修改接口只针对一个数据表，如客户修改接口 只能修改客户表，不会变更联系人信息。
修改的字段可以只传调整的字段和修改条件。没有改变的内容可以不传。如生命周期改变，可以只传递字段life作为变更的字段，客户的id或者sn作为作为变更的条件传入。
客户的修改必须提供修改条件，修改条件需要传入客户的CRM系统id,因为别的系统可能不知道,可以提供客户编号sn到接口内，系统通过sn获取id.
客户ID不可调整，如果想修改客户编号sn，则必须提供客户id作为条件。如参数param可以是：:{"dt":"customer","data":{"id":2804,"sn":"C002804"}}

接口说明
修改客户数据的内容
{
"dt":"customer",//修改数据的分类，customer代表客户表修改

"data"://修改数据内容
{
"cu_name":"中国海上救援大队",//客户名称
"sn":"0067",//客户编号
"life":"1",//生命周期，缺省也是1， 生命周期的数字描述：1:潜在;2:签约;3:重复购买;4:失效
"address":"中国上海",//地址
"cu_remark":"这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚",//备注
"cu_from":"1",//客户来源
"state":"9",//省份 1:安徽;2:北京;3:重庆;4:福建;5:甘肃;6:广东;7:广西;8:贵州;9:海南;10:河北;11:河南;12:黑龙江;13:湖北;14:湖南;15:吉林;16:江苏;17:江西;18:辽宁;19:内蒙古;20:宁夏;21:青海;22:山东;23:山西;24:陕西;25:上海;26:四川;27:天津;28:西藏;29:新疆;30:云南;31:浙江;32:香港;33:澳门;34:台湾;35:其它;
"city":"三沙市",//地级城市
"district":"西沙群岛"//区县

}
}

扩展功能说明：
参数需要加入：extend=1

修改接口扩展字段信息说明：
'type' => '3'， //客户种类
'period' => '1' ,//客户阶段
'uid' => '3'， //上级客户ID
'info' => '该公司的公司简介内容',//扩展字段 公司简介内容
'tel' => '19973607343',//扩展字段 电话
'web' => 'www.xtools.cn',//扩展字段 网址
'country' => 28,//扩展字段 国家或地区 缺省是 中国 28
'industry' => 2,//扩展字段 行业 自定义设置内容
'employees' => 1,//扩展字段 人员规模 自定义设置内容
'm_name'=>'客户简称',//扩展字段 客户简称

客户写入扩展功能参数参考如下：

{
"dt":"customer",//修改数据的分类，customer代表客户表修改
"extend":1, //是否是扩展修改功能--> 1:是
"data"://修改数据内容
{
"cu_name":"中国海上救援大队",//客户名称
"sn":"0067",//客户编号
"life":"1",//生命周期，缺省也是1， 生命周期的数字描述：1:潜在;2:签约;3:重复购买;4:失效
"address":"中国上海",//地址
"cu_remark":"这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚",//备注
"cu_from":"1",//客户来源
"state":"9",//省份 1:安徽;2:北京;3:重庆;4:福建;5:甘肃;6:广东;7:广西;8:贵州;9:海南;10:河北;11:河南;12:黑龙江;13:湖北;14:湖南;15:吉林;16:江苏;17:江西;18:辽宁;19:内蒙古;20:宁夏;21:青海;22:山东;23:山西;24:陕西;25:上海;26:四川;27:天津;28:西藏;29:新疆;30:云南;31:浙江;32:香港;33:澳门;34:台湾;35:其它;
"city":"三沙市",//地级城市
"district":"西沙群岛"//区县
'type':2, //扩展字段 客户类型 //潜在客户、普通客户、VIP客户、代理商、合作伙伴、失效客户
'period':1,//扩展字段 客户阶段
'uid':10,//扩展字段 上级客户ID
'info':'该公司的公司简介内容',//扩展字段 公司简介内容
'tel':'19973607343',//扩展字段 电话
'web':'www.xtools.cn',//扩展字段 网址
'country':28,//扩展字段 国家或地区 缺省是 中国 28
'industry':2,//扩展字段 行业 自定义设置内容
'employees':1,//扩展字段 人员规模 自定义设置内容
'm_name':'客户简称',//扩展字段 客户简称
}
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 客户修改状态，1：修改成功，0：修改失败
        msg:’修改客户成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 8. 企业客户自定义字段数据写入接口

- 模块：客户与联系人 · cmd：`api.input` · dt：`customerext`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549937464 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"1f92796c29c7346c832947414ffa1216",//登录接口返回的sid } |
| param | json | 是 | 写入客户的扩展数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 9d7041b7b4ea935cdc9d04032fcf43f4 |

param 示例：

```
{ "dt":"customerext",//写入数据的分类，customerext代表客户扩展数据的写入 "data"://写入数据分类内容  {"sn":"00003","ext_item5":"测试","ext_item7":"12345"} }
```

### 详细说明

```
param中data数据的说明：
本数据为客户扩展数据修改的条件和内容载体。
条件为sn或者id,就是客户的内部编号或者CRM的ID.通过这个条件，找到对应的唯一一条客户扩展数据。
修改内容是以crm的字段为准, 都以ext_为开头。如果无法知道字段名称，可以先通过客户扩展数据读取接口读取数据后，再进行处理。

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"customerext","data":{"sn":"00003","ext_item5":"测试","ext_item7":"12345"}}
stamp:1549937464
upr:{"sid":"1f92796c29c7346c832947414ffa1216"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"customerext","data":{"sn":"00003","ext_item5":"测试","ext_item7":"12345"}}1549937464{"sid":"1f92796c29c7346c832947414ffa1216"}api.inputopen1slslslsdldlsdlds
md计算结果:9d7041b7b4ea935cdc9d04032fcf43f4
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 客户写入状态，1：写入成功，0：写入失败
        msg:’客户基本信息[id:10]修改成功！’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 9. 联系人修改接口

- 模块：客户与联系人 · cmd：`api.update` · dt：`contact` · 本版新增
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.update |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528078285 |
| upr | json | 是 | 用户的登录信息。登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid } |
| param | json | 是 | 修改联系人的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 6913de14caa74767e360ce918497e085 |

param 示例：

```
{"dt":"contact","extend":1,"data":{"id":"30735","name":"张安安","sex":"1", "appellation":"经理","department":"研发部","headship":"工程师", "preside":"产品设计","phone":"010-88889999","mphone":"13800138000", "mphone_s":"13900139000","fax":"010-88889998","email":"zhanganan@xample.com", "qq":"12345678","weixin":"zhang_weixin","wx_name":"张安安的微信昵称", "qq_name":"张安安的QQ昵称","h_phone":"010-66667777", "h_addr":"北京市海淀区中关村大街1号","h_pst":"100080","birthday":"1990-01-01", "remark":"API修改联系人测试", "cr_ty":1,"cr_sn":"110101199001010011","islinkman":1}}
```

### 详细说明

```
参数对应数值如下：
param:{"dt":"contact","extend":1,"data":{"id":"30735","name":"张安安","sex":"1","appellation":"经理","department":"研发部","headship":"工程师","preside":"产品设计","phone":"010-88889999","mphone":"13800138000","mphone_s":"13900139000","fax":"010-88889998","email":"zhanganan@xample.com","qq":"12345678","weixin":"zhang_weixin","wx_name":"张安安的微信昵称","qq_name":"张安安的QQ昵称","h_phone":"010-66667777","h_addr":"北京市海淀区中关村大街1号","h_pst":"100080","birthday":"1990-01-01","remark":"API修改联系人测试","contype":1,"py":"zhang'an an","cr_ty":1,"cr_sn":"110101199001010011","ww":"zhang_wangwang","skype":"zhang_skype","islinkman":1}}
stamp:1788228190
upr:{"sid":"915c6d3cfad03159942387e341608da1"}
cmd:api.update
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"contact","extend":1,"data":{"id":"30735","name":"张安安","sex":"1","appellation":"经理","department":"研发部","headship":"工程师","preside":"产品设计","phone":"010-88889999","mphone":"13800138000","mphone_s":"13900139000","fax":"010-88889998","email":"zhanganan@xample.com","qq":"12345678","weixin":"zhang_weixin","wx_name":"张安安的微信昵称","qq_name":"张安安的QQ昵称","h_phone":"010-66667777","h_addr":"北京市海淀区中关村大街1号","h_pst":"100080","birthday":"1990-01-01","remark":"API修改联系人测试","contype":1,"py":"zhang'an an","cr_ty":1,"cr_sn":"110101199001010011","ww":"zhang_wangwang","skype":"zhang_skype","islinkman":1}}1788228190{"sid":"915c6d3cfad03159942387e341608da1"}api.updateopen1slslslsdldlsdlds
md计算结果:47572be8b3d7f6ae4acff453a3b319d1

参数param内容说明：
{
	"dt": "contact", //数据表 contact 代表联系人修改
	"data":
		 {
				"id": "30735", //联系人ID，修改时必填且不能为 0
				//"cu_sn":"梦蝶北京", //注意：修改时不能传递 cu_sn，否则报错"对应客户不能修改，无法保存"
				"name": "张安安", //姓名
				"sex": "1", //性别 2:男;1:女
				"appellation": "经理", //称谓
				"department": "研发部", //部门
				"headship": "工程师", //职务
				"preside": "产品设计", //负责业务
				"phone": "010-88889999", //工作电话
				"mphone": "13800138000", //移动电话
				"fax": "010-88889998", //传真
				"email": "zhanganan@shturl.cc/",//邮箱
				"qq": "12345678", //QQ
				"weixin": "zhang_weixin", //微信
				"wx_name": "张安安的微信昵称", //微信昵称
				"qq_name": "张安安的QQ昵称", //QQ昵称
				"h_phone": "010-66667777", //家庭电话
				"h_addr": "北京市海淀区中关村大街1号",//家庭住址
				"h_pst": "100080", //邮编
				"birthday": "1990-01-01", //生日
				"remark": "API修改联系人测试", //备注
				"cr_ty": 1, //证件类型 1:身份证;2:军官证;3:护照;4:其他1;5:其他2
				"cr_sn": "110101199001010011", //证件号码
				"islinkman": 1, //类型 0:联系人;1:主联系人;2:#个人客户;3:离职
				"ext_sel1": 1, //用户画像字段1
				"ext_item1": "自定义字段2", //用户画像字段2
				 用户画像字段以：ext_sel和ext_item开头。
} }
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 联系人修改状态，1：修改成功，0：修改失败
        msg:’修改联系人成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 10. 个人客户写入接口

- 模块：客户与联系人 · cmd：`api.input` · dt：`cuview`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1627543373 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"411abc59277b0df4e4c95879a93d2680", //登录接口返回的sid } |
| param | json | 是 | 写入客户的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | aa20ffdf26a695c16e746bf57f27c7be |

param 示例：

```
{ "dt":"cuview",//数据表 cuview代表个人客户写入， "data"://写入数据分类内容 "data":{"id":0,"name":"张三一", "mphone":"19973607343","department":"华为工程部", "preside":"承接工程","sex":2,"cr_ty":"1","cr_sn":"410103*********76","sn":"","type":"2", "period":"1","cu_from":"1","weixin":"","email":"","address":"海南省三亚市", "remark":"客户备注信息","ext_item1":"测试自定义"}}
```

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
|  |  | string |  |  |

### 详细说明

```
写入个人客户数据的内容：
{ "dt":"cuview",//数据表 cuview代表个人客户写入
       "data":{
  "id":0,//客户ID 添加的时候，可以不传递
'name':'张三一',//姓名
'mphone':'19973607343',//移动电话
'department':'华为工程部',//公司/部门
'preside':'承接工程',//负责业务
'sex':2,//性别： 2:男;1:女
'cr_ty':'1',//证件类型：1:身份证;2:军官证;3:护照;4:其他1;5:其他
'cr_sn':'410103*********76',//证件号码
'sn':'',//客户编号
'type':'2',//客户种类 如果不提供，缺省是第一个
'period':'1',//客户阶段
'cu_from':'1',//来源
'weixin':'',//微信
'email':'',//邮件地址
'address':'海南省三亚市',
'remark':'客户备注信息',//客户备注
//自定义字段 请先确定自定义字段在系统中的名字，再进行内容提交
'ext_item1':'测试自定义',//自定义字段信息
 }//数据
}

假定参数对应数值如下：
param:{"dt":"cuview","data":{"id":0,"name":"张三一","mphone":"19973607343","department":"华为工程部","preside":"承接工程","sex":2,"cr_ty":"1","cr_sn":"410103*********76","sn":"","type":"2","period":"1","cu_from":"1","weixin":"","email":"","address":"海南省三亚市","remark":"客户备注信息","ext_item1":"测试自定义"}}
stamp:1627543373
upr:{"sid":"411abc59277b0df4e4c95879a93d2680"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:
{"dt":"cuview","data":{"id":0,"name":"张三一","mphone":"19973607343","department":"华为工程部","preside":"承接工程","sex":2,"cr_ty":"1","cr_sn":"410103*********76","sn":"","type":"2","period":"1","cu_from":"1","weixin":"","email":"","address":"海南省三亚市","remark":"客户备注信息","ext_item1":"测试自定义"}}1627543373{"sid":"411abc59277b0df4e4c95879a93d2680"}api.inputopen1slslslsdldlsdlds
md计算结果:aa20ffdf26a695c16e746bf57f27c7be
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 客户写入状态，1：写入成功，0：写入失败
        msg:’个人客户添加成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 11. 订单写入接口

- 模块：订单与发货 · cmd：`api.input` · dt：`contract`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528095120 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"e6cf1667f7811d36df0f483b01128132"} |
| param | json | 是 | 写入订单的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | e9204980c6b87bb9d7f88257a17c6672 |

param 示例：

```
{"dt":"contract","data":{"id":"id","subject":"外部下单035","cu_sn":"0067","No.":"DD0005","sum":"7025.36","who":"王天虹","memo":"memo","name":"张三","tel":"18910785591","addr":"中国北京海淀区中关村北大街151号428","date":"2018-06-25","end_date":"2018-05-25","goods":[{"id":0,"prod":"P0001","memo":"不知道P0001可否对应上，另外i号是否区分大小写，这些也需要注明","amount":"2","un_price":"3000","sum":"7000","tax_money":"1000"},{"id":0,"prod":"P0002","memo":"没有税金的产品","amount":"1","un_price":"25.36","sum":"25.36","tax_money":""}]}}
```

### 详细说明

```
参数param的说明：
{"dt":"contract",//写入数据的分类，contract代表订单写入
"data":
{
"id":"0",//订单ID,在添加写入时，id可以不填或者输入0
"subject":"外部下单035",//订单标题
"cu_sn":"0067",//客户编号
"No.":"DD0005",//订单编号
"type":1,//订单的分类
"sum":"7025.36",//总金额
"who":"B",//订单所有者的名字，如果名字在系统找不到，再以登录人写入
"memo":"memo",//订单备注
"name":"zjb1111",//收货人姓名
"tel":"18910785591",//收货人电话
"addr":"中国北京海淀区中关村北大街151号428",//收货人地址
"date":"2018-06-25",//订单日期
"end_date":"2018-05-25",//最晚发货日期
'money_type'=>'USD',//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
'money_rate'=>'629',//汇率，可不传递
"one_select"：2,//分类2
"goods"://订单明细数组，
[//第一条订单明细。
{
"id":0,//订单明细ID，订单写入时，id可不输入或输入0
'prod'=>'P0001',//产品编码
"amount":"2",//数量
"un_price":"3000",//单价
"sum":"7000",//产品总金额
"tax_money":"1000",//税金
"memo":"不知道P0001可否对应上，另外i号是否区分大小写，这些也需要注明"//单条产品的备注说明
},
//下面是第二条订单明细
{
"id":0,//订单明细ID，订单写入时，id可不输入或输入0
"prod":"P0002",//产品编号
"amount":"1",//数量
"un_price":"25.36",//单价
"sum":"25.36",//产品总金额
"tax_money":"0",//税金
"memo":"没有税金的产品"//单条产品的备注说明
},
//下面可以添加更多明细数据
]
}
}

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
计算用例如下：
cmd:api.input
stamp:1528095120
appid:open00001_sajdjsjsj
appkey:open1slslslsdldlsdlds
param 字符串:
{"dt":"contract","data":{"id":"id","subject":"外部下单035","cu_sn":"0067","No.":"DD0005","sum":"7025.36","who":"B","memo":"memo","name":"zjb1111","tel":"18910785591","addr":"中国北京海淀区中关村北大街151号428","date":"2018-06-25","end_date":"2018-05-25","goods":[{"id":0,"prod":"P0001","amount":"2","un_price":"3000","sum":"7000","tax_money":"1000","memo":"不知道P0001可否对应上，另外i号是否区分大小写，这些也需要注明"},{"id":0,"prod":"P0002","amount":"1","un_price":"25.36","sum":"25.36","tax_money":"","memo":"没有税金的产品"}]}}
upr 字符串:
{"sid":"e6cf1667f7811d36df0f483b01128132"}
生成字符串：
{"dt":"contract","data":{"id":"id","subject":"外部下单035","cu_sn":"0067","No.":"DD0005","sum":"7025.36","who":"B","memo":"memo","name":"zjb1111","tel":"18910785591","addr":"中国北京海淀区中关村北大街151号428","date":"2018-06-25","end_date":"2018-05-25","goods":[{"id":0,"prod":"P0001","amount":"2","un_price":"3000","sum":"7000","tax_money":"1000","memo":"不知道P0001可否对应上，另外i号是否区分大小写，这些也需要注明"},{"id":0,"prod":"P0002","amount":"1","un_price":"25.36","sum":"25.36","tax_money":"","memo":"没有税金的产品"}]}}1528095120{"sid":"e6cf1667f7811d36df0f483b01128132"}api.inputopen1slslslsdldlsdlds
md5结果：
e9204980c6b87bb9d7f88257a17c6672

如果上述参数不能满足您的需要，可以对本接口进行扩展应用。
扩展方法：

参数说明：
参数param的说明：
{"dt":"contract",//写入数据的分类，contract代表订单写入
"extend":1, //扩展参数标记：0:或者不提供本参数，代表本接口的基本调用， 1：代表本接口的扩展调用，可以追加额外的字段
"data":
{
"id":"0",//订单ID,在添加写入时，id可以不填或者输入0
"subject":"外部下单035",//订单标题
"cu_sn":"0067",//客户编号
"No.":"DD0005",//订单编号
...

扩展字段的说明：
订单主表扩展字段：
'status'=>'status',//订单状态 1：执行中，2：结束，3：意外中止
'state'=>'state',//省份
'city'=>'city',//城市
'mphone'=>'mphone',//收货人手机
'pst'=>'pst',//邮编
'cu_sub'=>'cu_user',//客户签约人
'status'=>'status',//状态
'pay_mode'=>'pay_mode',//付款方式
'payment'=>'payment'//结款方式
'prj_id'=>'prj_id',//项目ID
自定义扩展字段（每个公司都有不同）

订单明细字段扩展：
'tax_rate'=>'tax_rate',//税率
'zk'=>'zk'//折扣 本字段主要用于输出，数据库中没有本字段，因此修改，添加的时候本字段无用，输出的时候，是计算输出的。
'prod_name'=>'prod_name',//产品名称 数据库中没有本字段，主要用于录入订单，没有产品编码时，使用 品名，型号，规格，批次确定产品的功能
'model'=>'model',//产品型号 数据库中没有本字段，主要用于录入订单，没有产品编码时，使用 品名，型号，规格，批次确定产品的功能
'sku'=>'sku',//规格 SKU 数据库中没有本字段，主要用于录入订单，没有产品编码时，使用 品名，型号，规格，批次确定产品的功能
'batchnum'=>'batchnum'//批次 数据库中没有本字段，主要用于录入订单，没有产品编码时，使用 品名，型号，规格，批次确定产品的功能

扩展功能的param参数模拟数据说明：
array("dt"=>"contract",//数据表 contract 代表订单写入
"extend"=>1,//代表扩展接口
       "data"=>array(
  'id'=>'0',//订单ID
'subject'=>'DD00020接口添加',
'cu_sn'=>'0067',//客户编号，需要转换为客户的ID进行 保存
'No.'=>'DD00020',//订单编号
'sum'=>'7025.36',//总金额
'type'=>'1',//订单的分类
'status'=>2,订单状态 1：执行中，2：结束，3：意外中止
'who'=>'B1',//订单所有者
'memo'=>'memo',//备注
'name'=>'zjb1111',//收货人姓名
'tel'=>'18910785591',//收货人电话
'addr'=>'中国北京海淀区中关村北大街151号428',//收货人地址
'date'=>'2018-06-25',//签约日期
'end_date'=>'2018-05-25',//最晚发货日期
'money_type'=>'USD',//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
'money_rate'=>'629',//汇率，可不传递
'pay_mode'=>'1',//付款方式
'payment'=>7,//结款方式
'prj_id'=>0,//项目ＩＤ
'j3' => '2019-12-27',//CRM系统中设置的自定义字段1
       'j4' =>'90',//CRM系统中设置的自定义字段2
       'j6' =>'4',//CRM系统中设置的自定义字段3
       'j7' =>'2019-12-27',//CRM系统中设置的自定义字段4
       'j8' =>'2019-12-27',//CRM系统中设置的自定义字段5
       'j10' =>'2019-12-27',//CRM系统中设置的自定义自段6
       'j11' =>'2019-12-27',//CRM系统中设置的自定义字段7
       'j13' =>'2019-12-27',//CRM系统中设置的自定义字段8
       'j14' =>',1,2,',//CRM系统中设置的自定义字段9
       'j15' =>'文本测试缺省',//CRM系统中设置的自定义字段10
       'j16' =>'2',//CRM系统中设置的自定义字段11
'goods'=>array(
array(
'id'=>0,//订单明细ID 添加的时候，可以不传递
'prod'=>'',//产品编码，优先使用产品编码进行匹配，如果没提供本字段，则使用 品名，型号，规格，批次确定产品
'prod_name'=>'红米手机',//品名
'model'=>'4S',//型号，
'sku'=>'白色',//SKU，规格，
'batchnum'=>'',//批次，
'amount'=>'1',//订单数量
'un_price'=>'100',//单价
'sum'=>'99',//金额
'tax_money'=>'10',//税金 tax_money
'zk'=>90,
'tax_rate'=>'10',//税金 tax_rate
'memo'=>'不知道P0001可否对应上'//产品明细备注
),array(
'id'=>0,//订单明细ID 添加的时候，可以不传递
'prod'=>'1323456479sjdojwo',//产品ID,对应 外部的产品编号
'amount'=>'1',//订单数量
'un_price'=>'200',//单价
'sum'=>'230',//金额
'tax_money'=>'30',//税金 tax_money
'tax_rate'=>'15',//税金 tax_rate
'zk'=>90,
'memo'=>'没有税金的产品'//产品明细备注
)
)//end 'contact'=>array(
 )//数据
 );
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 订单写入状态，1：写入成功，0：写入失败
        msg:’添加订单成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 12. 订单读取接口

- 模块：订单与发货 · cmd：`api.output` · dt：`contract`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 订单的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{  	"dt":"contract",//读取数据的分类，contract代表订单信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
参数说明：
{ "dt":"contract",//读取数据的分类，contract代表订单信息
"id":  0,//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
"No.":"NO000012",//订单编号，类似ID号，有这个参数，lastid就不起作用
"lastid":0,//指定上次下载的最后一个ID,和参数id、No.二选一
"confirm":2,//审批  1:待申请|wait_0;2:同意|pass_1;3:否决|vote_1;4:待审|wait_1
"status":1,//状态：1:*执行中|suc_no;2:结束|stop;3:意外中止|cancel;-1:#预定;-2:#借出未还;-3:#关闭
"st_send":2,//发货状态 0:---;1:未出库;2:需发货;3:部分;4:全部
"date":"2025-04-10,2025-05-14",//签约日期，可以是一天（日期字符串或时间戳），也可以是一个区间。区间的话，用2个日期用(英文)逗号分隔
"payment":4//结款方式
}

md参数计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
md的计算用例如下：
cmd:api.output
time:1528102067
appid:open00001_sajdjsjsj
appkey:open1slslslsdldlsdlds
param 字符串:{"dt":"contract","lastid":0,"id":0}
upr 字符串:{"sid":"61c0028e6b7dbe7f63df43340ce494a3"}
生成字符串：
{"dt":"contract","lastid":0,"id":0}1528102067{"sid":"61c0028e6b7dbe7f63df43340ce494a3"}api.outputopen1slslslsdldlsdlds
md5结果：
ced67ca166b6a27897ff868ff45bbb9f
如果上述参数不能满足您的需要，可以对本接口进行扩展应用。

字段说明：
"id":"10",//订单ID
"subject":"外部下单035",//订单标题
"cu_sn":"0067",//客户编号
"No.":"DD0005",//订单编号
"type":1,//订单的分类
"sum":"7025.36",//总金额
"who":"B",//订单所有者的名字，如果名字在系统找不到，再以登录人写入
"memo":"memo",//订单备注
"name":"zjb1111",//收货人姓名
"tel":"18910785591",//收货人电话
"addr":"中国北京海淀区中关村北大街151号428",//收货人地址
"date":"2018-06-25",//订单日期
"end_date":"2018-05-25",//最晚发货日期
'money_type'=>'USD',//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
'money_rate'=>'629',//汇率，可不传递
'one_select':'2',//分类2
'cu_no':'0067',//复核客户编号
"goods"://订单明细数组，
[//第一条订单明细。
{
"id":209,//订单明细ID，
"prod":"P0001",//产品编号
"amount":"2",//数量
"un_price":"3000",//单价
"sum":"7000",//产品总金额
"tax_money":"1000",//税金
"memo":"不知道P0001可否对应上，另外i号是否区分大小写，这些也需要注明"//单条产品的备注说明
},
//下面是第二条订单明细
{
"id":210,//订单明细ID
"prod":"P0002",//产品编号
"amount":"1",//数量
"un_price":"25.36",//单价
"sum":"25.36",//产品总金额
"tax_money":"0",//税金
"memo":"没有税金的产品"//单条产品的备注说明
},
//下面可以添加更多明细数据
]
}

扩展方法：
参数说明：
参数param的说明：
{	"dt":"contract",//写入数据的分类，contract代表订单写入
"extend":1, //扩展参数标记：0:或者不提供本参数，代表本接口的基本调用， 1：代表本接口的扩展调用，可以追加额外的字段
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  0, //指定下载的一条数据的ID号,有这个参数，lastid就不起作用
"confirm":2,//审批  1:待申请|wait_0;2:同意|pass_1;3:否决|vote_1;4:待审|wait_1
"status":1,//状态：1:*执行中|suc_no;2:结束|stop;3:意外中止|cancel;-1:#预定;-2:#借出未还;-3:#关闭
"st_send":2,//发货状态 0:---;1:未出库;2:需发货;3:部分;4:全部
"date":"2025-04-10,2025-05-14",//签约日期，可以是一天（日期字符串或时间戳），也可以是一个区间。区间的话，用2个日期用(英文)逗号分隔
}

扩展字段的说明：
订单主表扩展字段：
'status'=>'status',//订单状态 1：执行中，2：结束，3：意外终止
'state'=>'state',//省份
'city'=>'city',//,//城市
'mphone'=>'mphone',//收货人手机
'pst'=>'pst',//邮编
'cu_sub'=>'cu_user',//客户签约人
'st_send'=>'st_send',//发货状态 0:---;1:未出库;2:需发货;3:部分;4:全部
'pay_mode'=>'pay_mode',//付款方式
'payment'=>'payment'//结款方式
'prj_id'=>'prj_id',//项目ID
'op_id'=>'op_id',//对应机会ID
'org_id'=>'org_id',//组织ID
'confirm'=>'confirm',//审批状态 0:非审批订单; 1:待申请; 2:同意; 3:否决; 4:待审
自定义扩展字段

订单明细字段扩展：
'tax_rate'=>'tax_rate',//税率
'zk'=>'zk'//折扣 本字段主要用于输出，数据库中没有本字段，因此修改，添加的时候本字段无用，输出的时候，是计算输出的。
'prod_name'=>'prod_name',//产品名称 数据库中没有本字段
'model'=>'model',//产品型号 数据库中没有本字段
'sku'=>'sku',//规格 SKU 数据库中没有本字段
'batchnum'=>'batchnum'//批次 数据库中没有本字段
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 订单读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条订单数据
            [{订单1},{订单2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 13. 订单修改接口

- 模块：订单与发货 · cmd：`api.update` · dt：`contract`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.update |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528095120 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"e6cf1667f7811d36df0f483b01128132"} |
| param | json | 是 | 修改订单的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | e9204980c6b87bb9d7f88257a17c6672 |

param 示例：

```
{"dt":"contract","data":{"id":"id","subject":"外部下单035","cu_sn":"0067","No.":"DD0005","sum":"7025.36","who":"王天虹","memo":"memo","name":"张三","tel":"18910785591","addr":"中国北京海淀区中关村北大街151号428","date":"2018-06-25","end_date":"2018-05-25","goods":[{"id":0,"prod":"P0001","memo":"不知道P0001可否对应上，另外i号是否区分大小写，这些也需要注明","amount":"2","un_price":"3000","sum":"7000","tax_money":"1000"},{"id":0,"prod":"P0002","memo":"没有税金的产品","amount":"1","un_price":"25.36","sum":"25.36","tax_money":""}]}}
```

### 详细说明

```
参数说明：
cmd: api.update

param参数：
订单修改字段和添加字段保存一致。修改时，只需提供数据有变化的字段即可，不变的字段不需要提供，但订单明细除外。
订单明细要求：当前已有订单的明细必须提供，当前订单明细没提供，但是在数据库中已存在的订单明细，将会在操作的过程中被删除。
当前订单明细在数据库已存在的，以修改处理；在数据库中不存在，以添加处理。

array("dt"=>"contract",//数据表 contract 代表订单写入
   "data"=>array(
  'id'=>'0',//订单ID
'subject'=>'修改数据的订单标题',
//'cu_sn'=>'0067',//客户编号，需要转换为客户的ID进行 保存
'No.'=>'DD00014',//订单编号
'sum'=>'7025.36',//总金额
'type'=>1,
'who'=>'B1',//订单所有者part或人员名称
'memo'=>'memo',//备注
'name'=>'zjb1111',//收货人姓名
'tel'=>'18910785591',//收货人电话
'addr'=>'中国北京海淀区中关村北大街151号428',//收货人地址
'date'=>'2018-06-25',//签约日期
'end_date'=>'2018-05-25',//最晚发货日期
'money_type'=>'USD',//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
'money_rate'=>'629',//汇率，可不传递
"one_select"：2,//分类2
'goods'=>array(
array(
'id'=>0,//联系人ID 添加的时候，可以不传递
'prod'=>'N0001',//产品ID,对应 外部的产品编号
'amount'=>'1',//订单数量
'un_price'=>'1000',//单价
'sum'=>'990',//金额
'tax_money'=>'10',//税金 tax_money
'memo'=>'不知道P0001可否对应上'//产品明细备注
),array(
'id'=>0,//联系人ID 添加的时候，可以不传递
'prod'=>'N0002',//产品ID,对应 外部的产品编号
'amount'=>'1',//订单数量
'un_price'=>'10',//单价
'sum'=>'9.9',//金额
'tax_money'=>'10',//税金 tax_money
'memo'=>'测试'//产品明细备注
),array(
'id'=>0,//联系人ID 添加的时候，可以不传递
'prod'=>'1323456479sjdojwo',//产品ID,对应 外部的产品编号
'amount'=>'1',//订单数量
'un_price'=>'200',//单价
'sum'=>'230',//金额
'tax_money'=>'30',//税金 tax_money
'memo'=>'没有税金的产品'//产品明细备注
)
)//end 'contact'=>array(
 )//数据
 );

如果上述参数不能满足您的需要，可以对本接口进行扩展应用。
参数说明：
参数param的说明：
{"dt":"contract",//写入数据的分类，contract代表订单写入
"extend":1, //扩展参数标记：0:或者不提供本参数，代表本接口的基本调用， 1：代表本接口的扩展调用，可以追加额外的字段
"data":
{
"id":"0",//订单ID和订单编号有一个即可
"subject":"外部下单035",//订单标题
//"cu_sn":"0067",//客户编号不需要，系统规定 订单客户不能被修改
"No.":"DD0005",//订单编号和订单ID有一个即可
...

扩展字段的说明：
订单主表扩展字段：
'status'=>'status',//订单状态 1：执行中，2：结束，3：意外中止
'state'=>'state',//省份
'city'=>'city',//城市
'mphone'=>'mphone',//收货人手机
'pst'=>'pst',//邮编
'cu_sub'=>'cu_user',//客户签约人
'status'=>'status',//状态
'pay_mode'=>'pay_mode',//付款方式
'payment'=>'payment'//结款方式
'prj_id'=>'prj_id',//项目ID
自定义扩展字段（每个公司都有不同）

订单明细字段扩展：
'tax_rate'=>'tax_rate',//税率
//'zk'=>'zk'//本字段主要用于输出，数据库中没有本字段，因此修改，添加的时候本字段无用，输出的时候，是计算输出的。

param扩展参数样例：
array("dt"=>"contract",//数据表 contract 代表订单写入
"extend"=>1, //扩展参数标记：0:或者不提供本参数，代表本接口的基本调用， 1：代表本接口的扩展调用，可以追加额外的字段
       "data"=>array(
  'id'=>'0',//订单ID和订单编号有一个即可
'subject'=>'修改数据的订单标题',
//'cu_sn'=>'0067',//客户编号在修改中不需要，因为系统规定订单客户不能被修改
'No.'=>'DD00014',//订单编号和订单ID只要一个就可以
'sum'=>'7025.36',//总金额
'type'=>1,//订单分类
'who'=>'B1',//订单所有者part或人员名称
'memo'=>'memo',//备注
'name'=>'zjb1111',//收货人姓名
'tel'=>'18910785591',//收货人电话
'addr'=>'中国北京海淀区中关村北大街151号428',//收货人地址
'date'=>'2018-06-25',//签约日期
'end_date'=>'2018-05-25',//最晚发货日期
'money_type'=>'USD',//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
'money_rate'=>'629',//汇率，可不传递
'payment'=>7,//结款方式
'j3' => '2019-12-27',//ＣＲＭ系统自定义字段1
    'j4' =>'90',//ＣＲＭ系统自定义字段2
    'j6' =>'4',//ＣＲＭ系统自定义字段3
    'j7' =>'2019-12-27',//ＣＲＭ系统自定义字段4
    'j8' =>'2019-12-27',//ＣＲＭ系统自定义字段5
    'j10' =>'2019-12-27',//ＣＲＭ系统自定义字段6
    'j11' =>'2019-12-27',//ＣＲＭ系统自定义字段7
    'j13' =>'2019-12-27',//ＣＲＭ系统自定义字段8
    'j14' =>',1,2,',//ＣＲＭ系统自定义字段9
    'j15' =>'文本测试缺省',//ＣＲＭ系统自定义字段10
    'j16' =>'2',//ＣＲＭ系统自定义字段11
'goods'=>array(
array(
'id'=>0,//联系人ID 添加的时候，可以不传递
'prod'=>'N0001',//产品ID,对应 外部的产品编号
'amount'=>'1',//订单数量
'un_price'=>'1000',//单价
'sum'=>'990',//金额
'tax_money'=>'10',//税金 tax_money
'zk'=>90,
'tax_rate'=>'10',//税金 tax_money
'memo'=>'不知道P0001可否对应上'//产品明细备注
),array(
'id'=>0,//联系人ID 添加的时候，可以不传递
'prod'=>'N0002',//产品ID,对应 外部的产品编号
'amount'=>'1',//订单数量
'un_price'=>'10',//单价
'sum'=>'9.9',//金额
'tax_money'=>'10',//税金 tax_money
'zk'=>90,
'tax_rate'=>'10',//税金 tax_money
'memo'=>'测试'//产品明细备注
),array(
'id'=>0,//联系人ID 添加的时候，可以不传递
'prod'=>'1323456479sjdojwo',//产品ID,对应 外部的产品编号
'amount'=>'1',//订单数量
'un_price'=>'200',//单价
'sum'=>'230',//金额
'tax_money'=>'30',//税金 tax_money
'tax_money'=>'15',//税金 tax_money
'zk'=>90,
'memo'=>'没有税金的产品'//产品明细备注
)
)//end 'contact'=>array(
 )//数据
 );
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 订单写入状态，1：写入成功，0：写入失败
        msg:’修改订单成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 14. 订单分批发货（不计算库存的商品）接口

- 模块：订单与发货 · cmd：`api.cmdact` · dt：`contract` · act：`sendGoods_no_stock`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1628757241 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | string | 是 | 订单分批发货参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 69be2d1efb953eabd93db80560eac9ec |

param 示例：

```
{   "dt":"contract",//读取数据的分类，contract代表订单信息   "data":{     "act":"sendGoods_no_stock",//动作分类，不计算库存的商品分批发货     "id":11298,//订单id     "No.":"NO.11223",//订单编号，与id 保证传入一个     "one_select":2,//发货单 分类2     "sntype":"2",发货单 发货方式     "package_type":"",//发货单 包裹类型     "sendcomp":"abc",//发货单 物流公司     "sendcode":"DH0001",//发货单 物流单号,     "cost":"300",//发货单 运费   'date'=>'2025-12-04',//发货日期  "memo":"备注11295",//发货单 备注     "goods":[//发货详情产品       {"pro_id":15350,//产品id         "sn":"",//产品编号         "amount":3,//产品数量         "plan":"备注15350"//产品备注       },       {"pro_id":15351,         "ns":"",         "amount":3,         "plan":"备注15351"       }     ]   } }
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"contract","data":{"act":"sendGoods_no_stock","id":11298,"No.":"NO.11223","one_select":2,"sntype":"2","package_type":"","sendcomp":"abc","sendcode":"DH0001","cost":"300",'date'=>'2025-12-04',"memo":"备注11295","goods":[{"pro_id":15350,"sn":"","amount":3,"plan":"备注15350"},{"pro_id":15351,"ns":"","amount":3,"plan":"备注15351"}]}}
stamp:1732777169
upr:{"sid":"f9d20f38b7e8412e438b9b16540c86ce"}
cmd:api.cmdact
appkey:open1slslslsdldlsdlds
计算前字符串::{"dt":"contract","data":{"act":"sendGoods_no_stock","id":11298,"one_select":2,"sntype":"2","package_type":"","sendcomp":"abc","sendcode":"DH0001","cost":"300","memo":"备注11295","goods":[{"pro_id":15350,"sn":"","amount":3,"plan":"备注15350"},{"pro_id":15351,"ns":"","amount":3,"plan":"备注15351"},{"pro_id":15352,"ns":"","amount":3,"plan":"备注15352"}]}}1732777169{"sid":"f9d20f38b7e8412e438b9b16540c86ce"}api.cmdactopen1slslslsdldlsdlds
md计算结果:cafa9bb483d3a32b5729f0c3e826b00c
订单分批发货写入参数说明：
{
    "act" : "sendGoods_no_stock",//动作分类，不计算库存的商品分批发货
    "id" : 11298,//订单id
    "No.":"NO.11223",//订单编号，与id 只用一个即可
    "one_select" : 2,//发货单 分类2
    "sntype":"2",//发货单 发货方式
    "package_type":"",//发货单 包裹类型
    "sendcomp":"abc",//发货单 物流公司
    "sendcode":"DH0001",//发货单 物流单号,
    "cost":"300", //发货单 运费
	"date":"2025-12-04",//发货日期
    "memo":"备注11295", //发货单 备注
    "goods" : [ //发货详情产品（只处理属于该订单的产品）,
      {
        "pro_id" : 15350,//产品id
        "sn":"",//产品编号，与 pro_id 只用一个即可
        "amount" : 3,//产品数量（如果数量超出订单产品数量，按订单产品数量发货）
        "plan" :"备注15350",//产品备注
      },
      {
        "pro_id" : 15351,
        "sn":"",
        "amount" : 3,
        "plan" :"备注15351"
      }
]
 }
```

### 返回示例

```
                                {"ok":1,"ret":{"ok":1,"msg":"完成分批发货成功"}}
                            
```

## 15. 订单自定义明细读取接口

- 模块：订单与发货 · cmd：`api.cmdact` · dt：`contract` · act：`getOtherItems`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1628757241 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | string | 是 | 订单自定义明细读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 69be2d1efb953eabd93db80560eac9ec |

param 示例：

```
{   "dt":"contract",//读取数据的分类，contract代表订单信息   "data":{     "act":"getOtherItems",//动作分类，订单自定义明细     "id":11875,//订单id } }
```

### 详细说明

```
假定参数对应数值如下：
假定参数对应数值如下：
param:{"dt":"contract","data":{"act":"getOtherItems","id":11875}}
stamp:1754015172
upr:{"sid":"04f227c235e6b4e390d1567c1a082433"}
cmd:api.cmdact
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"contract","data":{"act":"getOtherItems","id":11875}}1754015172{"sid":"04f227c235e6b4e390d1567c1a082433"}api.cmdactopen1slslslsdldlsdlds
md计算结果:dd30ce9e6715a6a681fb75d00fc03c1e

读取订单自定义明细参数说明：
:{"dt":"contract",//所属业务表，contract代表订单
   "data":
 {"act":"getOtherItems",  //接口命令分类：这个是获取订单自定义明细
 "id":11875                        //订单ID
 }
}

返回结果说明：
{
"ok":1,
"msg":"数据读取成功",
"items"://订单明细信息
	{"co_id":11875,
	  "mode":"模式",
     "cfg":"配置信息；模式不同，信息不同",
     "data":"明细信息"
     }
}
```

### 返回示例

```
                                {"ok":1,"ret":{"ok":1,"msg":"数据读取成功","items":{"co_id":11875,"mode":"模式","cfg":"配置信息","data":"明细信息"}}}
                            
```

## 16. 采购单写入接口

- 模块：财务 · cmd：`api.input` · dt：`purchase`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528095120 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"e6cf1667f7811d36df0f483b01128132"} |
| param | string | 是 | 写入采购单的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 92db730896c2d4047b9b63ed00ca949d |

param 示例：

```
{"dt":"purchase","extend":1,"data":{"id":"id","title":"测试采购单写入111","cu_sn":"0067","date":"2025-06-25","lib":"1","j1":"a","j2":"2025-12-01","j3":"c","puritem":[{"id":0,"prod":"SN19873","num":"1","price":"100","tax_rate":0,"memo":"测试 num price"},{"id":0,"prod":"20241129001","num":"2","price":"200","money":"230","memo":"测试2 num price money"},{"id":0,"prod":"A9F18216","num":"2","price":"200","tax_rate":"2","memo":"测试2 num price tax_rate"}]}}
```

### 详细说明

```
参数param的说明：
{
"dt": "purchase", 写入数据的分类，purchase代表采购单写入
 "data": {
"id": "", //采购单ID,在添加写入时，id可以不填或者输入0
 "title": "测试采购单写入111", //采购单标题
"cu_id": 1440,//客户id
 "cu_sn": "0067",//客户编号，需要转换为客户的ID进行 保存（与客户id传入一个即可）
 "No.": "PK8881",//采购单编号
 "date": "2025-06-25",//采购日期
 "eta": "2025-06-25",//预计到货日期
 "type": 1,//分类
 "status0": 1,//状态
 "lib": "1",//仓库
 "address": "2",//收获人地址
 "who":"B1",//经手人
 "money_type":"USD",//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
 "money_rate":"629",//汇率，可不传递
 "money":0,//采购单总金额
 "amount_before_tax": 0,//不含税总金额,
 "ref_cu_id" : '',//关联订单客户
 "ref_co_id" : "",//关联订单
 "prj_id" : "",//关联项目
 "j1": "a",//自定义字段1
 "j2": "2025-12-01",//自定义字段2
 "j3": "c",//自定义字段3
 "puritem": [//采购单明细数组
 {
"id": 0,//采购明细ID，采购单写入时，id可不输入或输入0
 "prod": "SN19873",//产品编码
 "num": "1",//数量
 "money": "230",//金额
 "price": "100",//单价
 "tax_rate": 0,//税率
 "memo": "测试 num price",//采购明细备注
 },
{
"id": 0,
"prod": "20241129001",
"num": "2",
"price": "200",

"memo": "测试2 num price money"
 }
]
}
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 报价单写入状态，1：写入成功，0：写入失败
        msg:"添加采购单成功"//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 17. 采购单读取接口

- 模块：财务 · cmd：`api.output` · dt：`purchase`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | string | 是 | 采购单的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{   "dt": "purchase",//读取数据的分类，purchase代表采购单信息  	   "lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	   "id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
参数说明：
{
 "dt": "purchase",//读取数据的分类，purchase代表采购单信息
 "lastid":0,//指定上次下载的最后一个ID,和参数id二选一
 "id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}
字段说明：
{
 "id": "1714"//采购单ID
 "title": "计算库存的采购入库以及结束退货"//采购单标题
 "cu_sn": "BH001"//客户编号,如果没有编号，返回：[id:5] 5为客户id
 "No.": ""//采购单编号
 "type": "0"//采购单分类
 "status0": "1"//状态
 "money": "6440.00"//采购单总金额
 "amount_before_tax": "5600.00"//不含税总金额
 "backsum": "0.00"//已付金额
 "cu_sub": ""//供应商联系人币种
 "return_yn": "1"//退货
 "status": "3"//入库状态
 "lib": "1"//仓库
 "who": "刘琪峰"//经手人
 "memo": ""//备注
 "eta": ""//预计到货日期
 "confirm": "2"//审批
 "ref_cu_id": "0"//关联订单客户
 "ref_co_id": "0"//关联订单
 "prj_id": "0"//关联项目
 "bl_flag": "0"//补单 0:否;1:是
 "sendcode": ""//物流单号
 "is_zhifa": "0"//供应商直发 0:否;1:是
 "address": "0"//收获人地址
 "date": "2025-01-10"//采购日期
 "money_type": "RMB"//币种
 "money_rate": "100"//汇率
 "puritem": {//采购明细数组
 [
        {
 "id": "5811"//采购明细id
 "prod": "D4DS0012M"//产品ID,对应 外部的产品编号
 "sku": "-"//
 "num": "100.000"//采购数量
 "price": "56.0000"//单价
 "money": "6440.00"//金额
 "backnum": "100.000"//已入库
 "memo": "OMRON/欧姆龙 安全门开关操作钥匙"//备注
 "tax_rate": "15.00"//税率
 "tax_money": "840.00"//税金
 "un_price_tax": "64.4000000000"//含税单价
 "prod_name": "安全开关附件"//产品名
 "model": "D4DS-K2"//型号
 "batchnum": ""//批次
 }
    ]
  }
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组
            [{采购单1},{采购单2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 18. 付款计划读取接口

- 模块：财务 · cmd：`api.output` · dt：`pay_plan`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | string | 是 | 行动记录的读取参数 | {"dt":"pay_plan","id":335} |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

### 详细说明

```
param参数的说明：
{
"dt":"pay_plan",//读取数据的分类，pay_plan代表付款计划信息
 "lastid":0,//指定上次下载的最后一个ID,和参数id二选一
 "id": 10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}
返回参数说明：
{
 "id" :  "335"//付款计划id
 "date" :  "2021-08-12"//计划付款日期
 "serial" :  "1"//期次
 "money_type" :  "RMB"//币种
 "money_rate" :  "100"//汇率
 "money" :  "200.00"//金额
 "money_memo" :  ""//外币备注
 "who" :  ""//负责人
 "status" :  "0"//状态
 "pu_id" :  "0"//采购单
 "cu_sn" :  "whsd00001"//供应商(客户)编号
 "ctype" :  "0"//分类
 "type" :  "0"//付款方式
 "exp_date" :  ""//发票预计日期
 "pay_com" :  ""//付款单位
 "rec_com" :  ""//收款单位
 "bank" :  ""//收款开户行
 "acc_no" :  ""//收款账号
 "others" :  ""//其他
 "memo" :  ""//备注
 "owner" :  "刘琪峰"//录入人
 "prj_id" :  "0"//项目
 "bill_num" :  ""//发票号
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 数据读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条付款计划数据
            [{付款计划1},{付款计划2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 19. 付款计划写入接口

- 模块：财务 · cmd：`api.input` · dt：`pay_plan`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549951800 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"5fd9f194d62533227df465568a024a3d",//登录接口返回的sid } |
| param | string | 是 | 写入付款计划的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | f106479a228a964469458bc2b2db8300 |

param 示例：

```
{"dt":"pay_plan","data":{"id":0,"date":"2021-08-12","serial":1,"money":"200","cu_sn":"whsd00001"}}
```

### 详细说明

```
参数param的说明：
{
 "dt": "pay_plan",//写入数据的分类，pay_plan代表付款计划写入
 "data": {
 "id": 0,//付款计划id，写入时不用传
 "date": "2021-08-12",//计划付款日期
 "serial": 1,//期次
 "money": "abcd",//金额
 "cu_sn": "whsd00001"//供应商(客户)编号
 "money_type":"RMB",//币种
 "money_rate":"10",//汇率
 "money_memo":"备注",//外币备注
 "who":"B1",//负责人
 "status":"1",//状态
 "pu_id":"",//采购单
 "ctype":"2",//分类
 "type":"2",//付款方式
 "exp_date":"2021-08-12",//发票预计日期
 "pay_com":"",//付款单位
 "rec_com":"",//收款单位
 "bank":"",//收款开户行
 "acc_no":"",//收款账号
 "others":"",//其他
 "memo":"备注",//备注
 }
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 报价单写入状态，1：写入成功，0：写入失败
        msg:"添加采购单成功"//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 20. 报价单写入接口

- 模块：订单与发货 · cmd：`api.input` · dt：`price`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528095120 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"e6cf1667f7811d36df0f483b01128132"} |
| param | json | 是 | 写入报价单的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | e9204980c6b87bb9d7f88257a17c6672 |

param 示例：

```
{ "dt": "price", "extend": 1, "data": { "title": "主题888", "cu_sn": "CJKH000296", "type": 1, "money_rate": 100, "date": "2024-12-10", "op_id": 0, "one_select": 1, "con_id": "con_id", "sname": "sname", "s_contact": "s_contact", "pgoods": "pgoods", "pgath": "pgath", "ptrans": "ptrans", "memo": "memo", "status": "status", "j1": 13, "j2": 1, "j3": 30, "j4": 4, "j5": 48, "j6": 1, "j7": 2, "j9": 60, "pricedetail": [ { "id": 0, "prod": "P0001", "num": "1", "price": "100", "money": "99", "tax_money": "10", "zk": 90, "tax_rate": "10", "mark": "不知道P0001可否对应上，另号是否区分大小写，这些也需要注" }, { "id": 0, "prod": "SN19873", "num": "1", "price": "200", "money": "230", "tax_money": "30", "zk": 90, "mark": "没有税金的产品" } ] } }
```

### 详细说明

```
参数param的说明：
{"dt":"price",//写入数据的分类，price代表报价单写入
"data":
{
"title":"外部下单035",//报价单标题
"cu_sn":"0067",//客户编号
"No.":"DD0005",//报价单编号
"type":1,//报价单的分类
'money_type'=>'USD',//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
'money_rate'=>'629',//汇率，可不传递
"date":"2024-12-10",//日期
"op_id":"234",//对应销售机会的id
"one_select":1,//分类2
"con_id":"B1",//接收人
"sname":"M1",//报价单所有者的名字，如果名字在系统找不到，再以登录人写入
"s_contact":"18910785591",//报价人联系方式
"pgoods":"每一周交付一次",//交付说明
"pgath":"每月1号结款",//付款说明
"ptrans":"精包装，顺丰快运，最晚三天到货",//包装运输说明
"memo":"这是标准的合约，一切解释权归商家所有",//备注
"status":"1,//转成订单
"j1":13,//自定义扩展字段（每个公司都有不同）
"j2":1,
"j3":30,
"j4":4,
"j5":48,
"j6":1,
"j7":2,
"j9":60,
"pricedetail"://报价单明细数组，
[//第一条报价单明细。
{
"id":0,//报价单明细ID，报价单写入时，id可不输入或输入0
"prod":"P0001",//产品编码
"num":"2",//数量
"price":"3000",//单价
"money":"7000",//产品总金额
"tax_money":"1000",//税金
"mark":"不知道P0001可否对应上，另号是否区分大小写，这些也需要注"//单条产品的备注说明
},
//下面是第二条报价单明细
{
"id":0,//报价单明细ID，报价单写入时，id可不输入或输入0
"prod":"P0002",//产品编号
"num":"1",//数量
"price":"25.36",//单价
"money":"25.36",//产品总金额
"tax_money":"0",//税金
"mark":"没有税金的产品"//单条产品的备注说明
},
//下面可以添加更多明细数据
]
}
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 报价单写入状态，1：写入成功，0：写入失败
        msg:"添加报价单成功"//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 21. 报价单修改接口

- 模块：订单与发货 · cmd：`api.update` · dt：`price`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.update |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528095120 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"e6cf1667f7811d36df0f483b01128132"} |
| param | json | 是 | 修改报价单的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | e9204980c6b87bb9d7f88257a17c6672 |

param 示例：

```
{"dt":"price","extend":1,"data":{"id":"","title":"主题777","No.":"BJD17158526990023","date":"2024-12-09","j1":13,"j2":1,"j3":300,"j4":400,"j5":48,"j6":1,"j7":2,"j9":900,"pricedetail":[{"prod":"SN19873","price":3000,"num":3,"tax_rate":30,"tax_money":3000,"un_price_tax":3000,"money":3000,"mark":"测试修改明细"}]}}
```

### 详细说明

```
参数说明：
cmd: api.update

param参数：
报价单修改字段和添加字段保存一致。修改时，只需提供数据有变化的字段即可，不变的字段不需要提供，但报价单明细除外。
报价单明细要求：当前已有报价单的明细必须提供，当前报价单明细没提供，但是在数据库中已存在的报价单明细，将会在操作的过程中被删除。
当前报价单明细在数据库已存在的，以修改处理；在数据库中不存在，以添加处理。

参数param的说明：
{"dt":"price",//写入数据的分类，price代表报价单写入
"data":
{
"title":"外部下单035",//报价单标题
"No.":"DD0005",//报价单编号
"type":1,//报价单的分类
'money_type'=>'USD',//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
'money_rate'=>'629',//汇率，可不传递
"date":"2024-12-10",//日期
"op_id":"234",//对应销售机会的id
"one_select":1,//分类2
"con_id":"B1",//接收人
"sname":"M1",//报价单所有者的名字，如果名字在系统找不到，再以登录人写入
"s_contact":"18910785591",//报价人联系方式
"pgoods":"每一周交付一次",//交付说明
"pgath":"每月1号结款",//付款说明
"ptrans":"精包装，顺丰快运，最晚三天到货",//包装运输说明
"memo":"这是标准的合约，一切解释权归商家所有",//备注
"status":"1,//转成订单
"j1":13,//自定义扩展字段（每个公司都有不同）
"j2":1,
"j3":30,
"j4":4,
"j5":48,
"j6":1,
"j7":2,
"j9":60,
"pricedetail"://报价单明细数组，
[//第一条报价单明细。
{
"id":0,//报价单明细ID，
"prod":"",//产品编码 与id传入一个即可
"num":"2",//数量
"price":"3000",//单价
"money":"7000",//产品总金额
"tax_money":"1000",//税金
"mark":"不知道P0001可否对应上，另外i号是否区分大小写，这些也需要注明"//单条产品的备注说明
},
//下面是第二条报价单明细
{
"id":0,//报价单明细ID，
"prod":"P0002",//产品编号
"num":"1",//数量
"price":"25.36",//单价
"money":"25.36",//产品总金额
"tax_money":"0",//税金
"mark":"没有税金的产品"//单条产品的备注说明
},
//下面可以添加更多明细数据
]
}
}
```

## 22. 行动记录写入接口

- 模块：客户与联系人 · cmd：`api.input` · dt：`action`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549951800 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"5fd9f194d62533227df465568a024a3d",//登录接口返回的sid } |
| param | json | 是 | 写入行动待办记录的的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | f106479a228a964469458bc2b2db8300 |

param 示例：

```
{"dt":"action","data":{"id":0,"cale":"3","subject":"测试标题","content":"行动历史记录的内容描述","cu_sn":"00003","date":"2019-01-31"}}
```

### 详细说明

```
param中数据的说明：
{
"dt":"action",//数据分类，action代表行动记录，待办
"data":{
"id":0, //行动记录ID,写入时，id=0
"cale":"3",//数据类型，1:日程;2:待办任务;3:记录;4:*待办任务
"subject":"测试标题",//标题 cale=3: 记录的时候，标题可以不要。
"content":"行动历史记录的内容描述",//内容描述
"type":1,//行动的分类，请参考 数据字典自定义内容。
"cu_sn":"00003",//客户编码
"con_id":120,//客户的联系人ID
"who":"M2,M4,",//执行人或
"date":"2019-01-31",//日期---YYYY-MM-DD
"op_id":0, //对应销售机会ID，
"prj_id":103, //对应项目ID， 注意：op_id,prj_id只能有一个有数据，不能同时存在。
"co_id":10334, //对应合约ID， 注意：项目，机会，合约和上面的客户必须是一致的，不能随意输入。
}
}

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"action","data":{"id":0,"cale":"3","subject":"测试标题","content":"行动历史记录的内容描述","cu_sn":"00003","date":"2019-01-31"}}
stamp:1549951800
upr:{"sid":"5fd9f194d62533227df465568a024a3d"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"action","data":{"id":0,"cale":"3","subject":"测试标题","content":"行动历史记录的内容描述","cu_sn":"00003","date":"2019-01-31"}}1549951800{"sid":"5fd9f194d62533227df465568a024a3d"}api.inputopen1slslslsdldlsdlds
md计算结果:f106479a228a964469458bc2b2db8300
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 行动记录写入状态，1：写入成功，0：写入失败
        msg:’行动/待办添加成功！’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 23. 行动记录读取接口

- 模块：客户与联系人 · cmd：`api.output` · dt：`action`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | json | 是 | 行动记录的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{  	"dt":"action",//读取数据的分类，action代表行动记录信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
param参数的说明：
{
"dt":"action",//读取数据的分类，action代表行动记录信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"action","lastid":10}
stamp:1549954821
upr:{"sid":"96c584001f27e93c443e8eb0ee77e9b4"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"action","lastid":10}1549954821{"sid":"96c584001f27e93c443e8eb0ee77e9b4"}api.outputopen1slslslsdldlsdlds
md计算结果:14772c52c44faeaf973c0778f66c4fc8

字段说明：
{
       'id':62, //数据ID
       'cale' :'4', //数据类型，1:日程;2:待办任务;3:记录;4:*待办任务
       'subject':'标题' ,//标题 cale=3: 记录的时候，标题可以不要。
       'content':'内容描述',//内容
       'type':3,//行动的分类，参考数据字典内容
       'cu_sn':'[id:6921]', ////客户编码
       'con_id':120,//客户下单联系人ID
       'who':'M2,M4,',//执行人，可多人
       'date':'2017-02-17', //日期
       'endate':'2017-02-12', //结束日期
       'op_id':'0', //对应销售机会ID
       'prj_id':'0', //对应项目ID
       'co_id':'0', //对应合约ID
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 数据读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条行动记录数据
            [{行动记录1},{行动记录2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 24. 维修工单写入接口

- 模块：售后与其他 · cmd：`api.input` · dt：`repairinfo`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549956700 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"5c08e77b2100df75bc4ae3c45a65754c",//登录接口返回的sid } |
| param | json | 是 | 写入维修工单的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | c1c5949fb503920268a9cf5de80bfd50 |

param 示例：

```
{"dt":"repairinfo","data":{"id":0,"No.":"WDGD000000039","who":"王天虹","date":"2019-02-01","recv_time":"08:30","cu_sn":"00004","name":"张三","tel":"7528350","phone":"18910785590","repairinfo":[{"id":0,"prod":"1323456479sjdojwo","pdate":"2018-01-01","sdate":"2018-10-01","info":"无法正常开机了","notice":"需要上门维修","bx_status":1,"dept":1}]}}
```

### 详细说明

```
param参数说明：
{
	   "dt":"repairinfo",//数据表分类，repairinfo代表维修工单
       "data":{
				"id":0,//维修工单ID ---0代表插入
				'No.':'WDGD000000039',//维修工单流水--编号
				'who':'B1',//接单人 可以是 part或者用户名字
				'date':'2019-02-01',//接件日期 日期---YYYY-MM-DD
				'recv_time':'08:30',//接件时间
				'cu_sn':'00004',//客户编号，需要转换为客户的ID进行 保存
				'name':'zjb',//联系人姓名
				'tel':'7528350',//联系人电话
				'phone':'18910785590',//联系人手机 //
				'repairinfo':
				[//维修工单的副表
					{
						'id':0,//维修单的扩展表ID，添加的时候为0
						'prod':'1323456479sjdojwo',//产品ID,对应 外部的产品编号
						'pdate':'2018-01-01',//产品生产日期
						'sdate':'2018-10-01',//产品销售日期
						'info':'无法正常开机了',//维修问题故障描述
						'notice':'需要上门维修',//沟通要点
						'bx_status':1,//是否保修期内 1:在保;2:出保
						'dept':1//承接部门
					}
				]

			}
}

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"repairinfo","data":{"id":0,"No.":"WDGD000000039","who":"B1","date":"2019-02-01","recv_time":"08:30","cu_sn":"00004","name":"zjb","tel":"7528350","phone":"18910785590","repairinfo":[{"id":0,"prod":"1323456479sjdojwo","pdate":"2018-01-01","sdate":"2018-10-01","info":"无法正常开机了","notice":"需要上门维修","bx_status":1,"dept":1}]}}
stamp:1549956700
upr:{"sid":"5c08e77b2100df75bc4ae3c45a65754c"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"repairinfo","data":{"id":0,"No.":"WDGD000000039","who":"B1","date":"2019-02-01","recv_time":"08:30","cu_sn":"00004","name":"zjb","tel":"7528350","phone":"18910785590","repairinfo":[{"id":0,"prod":"1323456479sjdojwo","pdate":"2018-01-01","sdate":"2018-10-01","info":"无法正常开机了","notice":"需要上门维修","bx_status":1,"dept":1}]}}1549956700{"sid":"5c08e77b2100df75bc4ae3c45a65754c"}api.inputopen1slslslsdldlsdlds
md计算结果:c1c5949fb503920268a9cf5de80bfd50
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 维修工单写入状态，1：写入成功，0：写入失败
        msg:’添加维修工单成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 25. 维修工单读取接口

- 模块：售后与其他 · cmd：`api.output` · dt：`repairinfo` · 本版有变更：20260901（补充返回字段说明）
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549956079 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"0c3e041b927ddd0294017119ce459d92",//登录接口返回的sid } |
| param | json | 是 | 维修工单的读取参数 | {"dt":"repairinfo","lastid":10} |
| md | string | 是 | 参数合法性校验码 | 0274476693a99ad573231cf0c90b8055 |

### 详细说明

```
param参数说明：
{
"dt":"repairinfo",//读取数据的分类，repairinfo代表维修工单信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
 }

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"repairinfo","lastid":10}
stamp:1549956079
upr:{"sid":"0c3e041b927ddd0294017119ce459d92"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"repairinfo","lastid":10}1549956079{"sid":"0c3e041b927ddd0294017119ce459d92"}api.outputopen1slslslsdldlsdlds
md计算结果:0274476693a99ad573231cf0c90b8055

字段说明：
{
"id":"11", //维修工单主单ID
"No.":"1", //维修单编号 维修工单流水--编号
"who":"刘琪峰", //接单人
"date":"2016-06-23", //接单日期
"recv_time":"06:00", //接单时间
"cu_sn":"BH002", //客户编码
"name":"地方", //联系人
"tel":"", //联系人电话
"phone":"", //联系人手机
"repairinfo": //维修信息
 [
 {
 "id":"1", //维修单的扩展表ID
 "prod":"6901236344033", //维修产品编码
 "pdate":"", //生产日期
 "sdate":"", //销售日期
 "info":"", //维修问题故障描述
 "notice":"", //沟通要点
 "bx_status":"1", //是否保修期内 1:在保;2:出保
 "dept":"1" //承接部门
 }]},
"goods": //维修配件及服务明细
[
{
"id":"20593",//明细ID
"pid":"11477",//产品ID
"pro_name":"服务",//产品名称
"model":"",//产品型号
"spec":"-",//SKU 规格
"amount":"1.000",//数量
"un_price":"260.0000",//单价
"sum":"260.00",//总金额
"rep_sum":"0.00",//厂家承担金额
"memo":""//备注
}
]
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 数据读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条维修工单数据
            [{维修工单1},{维修工单2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 26. 计划回款读取接口

- 模块：财务 · cmd：`api.output` · dt：`gathering`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | json | 是 | 计划回款的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{ 	"dt":"gathering",//读取数据的分类，gathering代表计划回款信息 	      "lastid":0,//指定上次下载的最后一个ID,和参数id二选一 	      "id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用   }
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"gathering","id":53}
stamp:1577424117
upr:{"sid":"6183ea4727ef97f264eebf42887984cc"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"gathering","id":53}1577424117{"sid":"6183ea4727ef97f264eebf42887984cc"}api.outputopen1slslslsdldlsdlds
md计算结果:71c4f37ec5772e259bd4fa6fc6eeca99

param参数说明：
{ "dt":"gathering",//读取数据的分类，gathering代表计划回款信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10,//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
"memo":"D001"  //通过备注进行数据唯一校验，这个是备注字段是否存在这样的内容；即等于
}

返回字段信息说明：
array (
       'id' => string '53' ,// 计划回款ID
       'date' => string '2016-08-23' //计划回款日期
       'serial' => string '1' ,//期次
       'money' => string '1195.74' ,//金额
       'status' => string '2' ，//是否回款
       'who' => string 'B1' ，//所有者
       'principal' => string '' ,//负责人
       'cu_sn' => string 'DHF056983333' ,//对应客户编号
       'co_sn' => string 'DD2016080124' ,//对应合同订单编号
       'prj_id' => string '0' ,//对应项目ID
       'memo' => string '' //备注信息
)
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 数据读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条计划回款数据
            [{计划回款1},{计划回款2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 27. 计划回款修改接口

- 模块：财务 · cmd：`api.update` · dt：`gathering`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.update |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528078285 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid } |
| param | json | 是 | 计划回款的修改信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 6913de14caa74767e360ce918497e085 |

param 示例：

```
{"dt":"gathering","data":{"id":553,"date":"2019-12-27","serial":"1","memo":"备注信息","money":"1195.74","status":"2","who":"B1","principal":"负责人","co_sn":"DD2016080124","prj_id":"0"}}
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"gathering","data":{"id":553,"date":"2019-12-27","serial":"1","money":"1195.74","status":"2","who":"B1","principal":"","co_sn":"DD2016080124","prj_id":"0","memo":"备注信息"}}
stamp:1577436357
upr:{"sid":"19b41e79e92ce567852832a943df2e8b"}
cmd:api.update
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"gathering","data":{"id":553,"date":"2019-12-27","serial":"1","money":"1195.74","status":"2","who":"B1","principal":"","co_sn":"DD2016080124","prj_id":"0","memo":"备注信息"}}1577436357{"sid":"19b41e79e92ce567852832a943df2e8b"}api.updateopen1slslslsdldlsdlds
md计算结果:b276c0e35aa0af1a9a09487b8ba4dad2

参数说明：
{"dt":"gathering",
"data":
{
"id":553,//修改计划回款的ID
"date":"2019-12-27",//计划回款日期
"serial":"1",//期次
"money":"1195.74",//金额
"status":"2",//是否回款
"who":"B1",//所有者
"principal":"",//负责人
//"cu_sn":"DHF056983333",//注意，按照CRM规定，客户不可以修改，不能提供本参数
"co_sn":"DD2016080124",//对应合同订单号
"prj_id":"0",//项目ID
"memo":"备注信息"//备注信息
}
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 修改状态，1：修改成功，0：修改失败
        msg:’修改计划回款成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 28. 计划回款写入接口

- 模块：财务 · cmd：`api.input` · dt：`gathering`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549951800 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"5fd9f194d62533227df465568a024a3d",//登录接口返回的sid } |
| param | json | 是 | 写入计划回款的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | f106479a228a964469458bc2b2db8300 |

param 示例：

```
{"dt":"gathering","data":{"id":0,"date":"2019-12-27","serial":"1","memo":"备注信息","money":"1195.74","status":"2","who":"B1","principal":"负责人","cu_sn":"DHF056983333","co_sn":"DD2016080124","prj_id":"0"}}
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"gathering","data":{"id":0,"date":"2019-12-27","serial":"1","money":"1195.74","status":"2","who":"B1","principal":"","cu_sn":"DHF056983333","co_sn":"DD2016080124","prj_id":"0","memo":"备注信息"}}
stamp:1577427519
upr:{"sid":"d871332e80a708c818f77bd19c41bb1b"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"gathering","data":{"id":0,"date":"2019-12-27","serial":"1","money":"1195.74","status":"2","who":"B1","principal":"","cu_sn":"DHF056983333","co_sn":"DD2016080124","prj_id":"0","memo":"备注信息"}}1577427519{"sid":"d871332e80a708c818f77bd19c41bb1b"}api.inputopen1slslslsdldlsdlds
md计算结果:713a055f276ff1d7e59354113326713f

参数说明：
{"dt":"gathering",
"data":
{
"id":0,//新建 id=0
"date":"2019-12-27",//计划回款日期
"serial":"1",//期次
"money":"1195.74",//金额
"status":"2",//是否回款
"who":"B1",//所有者
"principal":"",//负责人
"cu_sn":"DHF056983333",//对应客户编码
"co_sn":"DD2016080124",//对应合同订单号
"prj_id":"0",//项目ID
"memo":"备注信息"//备注信息
}
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 写入状态，1：写入成功，0：写入失败
        msg:’计划回款添加成功！’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 29. 回款记录写入接口

- 模块：财务 · cmd：`api.input` · dt：`gathering_note`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1628737838 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"729d74edf717c634aeb611c0bb927ca3",//登录接口返回的sid } |
| param | json | 是 | 回款记录的写入参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 44c5577e091e82c3853bb95b88f85cd0 |

param 示例：

```
{ 	"dt":"gathering_note",//写入数据的分类，gathering_note代表回款记录信息 	      "data":{"cu_sn":"5642324","co_id":"74","date":"2021-08-12","invoice":"1","serial":2,"money":"100","type":1,"ctype":2,"who":"M1"},//指定添加信息
```

### 详细说明

```
添加回款记录参数param说明：
{
 "dt":    "gathering_note",//数据表 gathering_note代表回款记录写入
 "data":{

			 'cu_sn':'5642324',//回款所属的客户编码

				'co_id':'74',//订单ID或者订单编号 不关联订单可以不传

				'date':'2021-08-12',//回款日期 必须输入项目

				'invoice':'1',//已开发票 1:是;2:否;3:无需开票

				'serial':2,//期次

				'money':'100',//回款金额 必须输入项目

				'type':1,//付款方式 必须输入项目

				'ctype':2,//分类

				'who':'M1'//所有者，这个是所有者内部part

			 }//数据

};

假定参数对应数值如下：
param:{"dt":"gathering_note","data":{"cu_sn":"5642324","co_id":"74","date":"2021-08-12","invoice":"1","serial":2,"money":"100","type":1,"ctype":2,"who":"M1"}}
stamp:1628737838
upr:{"sid":"729d74edf717c634aeb611c0bb927ca3"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"gathering_note","data":{"cu_sn":"5642324","co_id":"74","date":"2021-08-12","invoice":"1","serial":2,"money":"100","type":1,"ctype":2,"who":"M1"}}1628737838{"sid":"729d74edf717c634aeb611c0bb927ca3"}api.inputopen1slslslsdldlsdlds
md计算结果:44c5577e091e82c3853bb95b88f85cd0
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 写入状态，1：写入成功，0：写入失败
        msg:’回款记录添加成功！’,//文字说明字符串，写入成功提示，或者失败原因
        id:100//添加的数据ID
        }
}
                            
```

## 30. 回款记录读取接口

- 模块：财务 · cmd：`api.output` · dt：`gathering_note`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | json | 是 | 回款记录的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{ 	"dt":"gathering_note",//读取数据的分类，gathering_note代表回款记录信息 	      "lastid":0,//指定上次下载的最后一个ID,和参数id二选一 	      "id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用   }
```

### 详细说明

```
param参数说明：
{ "dt":"gathering_note",//读取数据的分类，gathering_note代表回款记录信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10,//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
"memo":"D001"  //通过备注进行数据唯一校验，这个是备注字段是否存在这样的内容；即等于
}

假定参数对应数值如下：
param:{"dt":"gathering_note","id":4}
stamp:1620377730
upr:{"sid":"3d8874900e795e821c140c422e70e103"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"gathering_note","id":4}1620377730{"sid":"3d8874900e795e821c140c422e70e103"}api.outputopen1slslslsdldlsdlds
md计算结果:a7e5ddae81d5dd06511b5a3abc1a6490

返回字段信息说明：
   'id' => string '4' //回款记录ID
       'cu_sn' => string '[id:5]' //回款所属的客户编码
       'co_id' => string '0' //合同/订单 ID
       'date' => string '2016-06-22' //日期
       'invoice' => string '1' //已开发票 1:是;2:否;3:无需开票
       'serial' => string '-1' //期次
       'money' => string '2499.00' //回款金额
       'type' => string '2' //付款方式
       'ctype' => string '0' //分类
       'gtype' => string '0' //类型
       'owner' => string '马里奥' //创建人
       'who' => string '刘琪琪' //所有者
'memo'=> string '刘琪峰 2024-01-22 10:22:35 结算失败。'//备注
'money_type'=>'money_type'//币种
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 数据读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条回款记录数据
            [{回款记录1},{回款记录2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 31. 开票记录写入接口

- 模块：财务 · cmd：`api.input` · dt：`bill`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528095120 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"aa9dd4bda646ea60c48518688320574b"} |
| param | string | 是 | 写入开票记录的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 0d2a57b0f17d8d66885278f7cb219bad |

param 示例：

```
:{"dt":"bill","data":{"id":0,"cu_sn":"11111","billsn":"fp444","date":"2024-11-20","money":444,"type":5,"who":"M2","money_type":"RMB","money_rate":444,"content":"内容444","serial":2}}
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"bill","data":{"id":0,"cu_sn":"11111","billsn":"fp444","date":"2024-11-20","money":444,"type":5,"who":"M2","money_type":"RMB","money_rate":444,"content":"内容444","serial":2}}
stamp:1732168886
upr:{"sid":"aa9dd4bda646ea60c48518688320574b"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"bill","data":{"id":0,"cu_sn":"11111","billsn":"fp444","date":"2024-11-20","money":444,"type":5,"who":"M2","money_type":"RMB","money_rate":444,"content":"内容444","serial":2}}1732168886{"sid":"aa9dd4bda646ea60c48518688320574b"}api.inputopen1slslslsdldlsdlds
md计算结果:0d2a57b0f17d8d66885278f7cb219bad
开票记录写入参数说明：
{
 "dt":"bill",
 "data":{
  "cu_sn":"111111",//开票所属的客户编码
  "co_sn":"20241206003",//合同/订单号
  "co_id":12392,//订单id,与合同/订单号(co_sn)传入一个即可
  "type":5,//票据类型
  "tax_rate":0,//税率
  "content":"开票内容",//开票内容

  "money":2000,//票据金额
"billsn":"fp444",//发票号码
  "money_type":"RMB",//币种
  "money_rate":100,//汇率
"date":"2024-11-20",//开票日期
  "serial":0,//期次
  "who":"B1",//经手人
  "cu_sub":"",//客户收件人
  "sthk":0,//是否回款
  "stjh":0,//回款计划
  "sendcode":"",//物流单号
  "mphone":"15801111111",//收货人手机
  "address":"发票收货地址",//发票收货地址
  "memo":"备注"//备注
 }
}
```

### 返回示例

```
                                {"ok" :  1,
  "ret" : 
    {
      "ok" :  1,
      "msg" :  "开票记录添加成功！",
      "id" :  767
    }
}
                            
```

## 32. 销售机会读取接口

- 模块：客户与联系人 · cmd：`api.output` · dt：`opport`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | json | 是 | 销售机会的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{  	"dt":"opport",//读取数据的分类，opport代表销售机会信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
param参数的说明：
{
"dt":"opport",//读取数据的分类，opport代表销售机会信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"opport","id":10}
stamp:1620270954
upr:{"sid":"1002684ecc98a66cfbb884fd36f03358"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"opport","id":10}1620270954{"sid":"1002684ecc98a66cfbb884fd36f03358"}api.outputopen1slslslsdldlsdlds
md计算结果:6c2723933d3b41851d822f8181c038ba

字段说明：
       'id' => string '10' //销售机会的ID
       'oppname' => string '测试用' //销售机会主题
       'cu_sn' => string '[id:6921]' //客户编号
       'date' => string '2017-06-29' //发现日期
       'expdate' => string '2019-05-24' //预计签约日期
       'exprev' => string '53000.00' //预期金额
       'oppowner' => string 'B1' //负责人
       'phase' => string '3' //阶段，客户自定义设置
       'status' => string '1' //状态：1:*跟踪;2:成功;3:失败;4:搁置;5:失效
       'cu_require' => string '' //客户需求
      'creatdate' => string '2017-03-16' //创建日期
      'moddate' => string '2018-01-16' //修改日期
      'amstamp' => string '2018-01-16' //更新日期
'provider' => string '' //提供人

扩展功能param参数的说明：
{
"dt":"opport",//读取数据的分类，opport代表销售机会信息
"extend":1,//1：使用扩展功能，0：不使用扩展功能
"id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

扩展字段说明：
'cu_sub'=>23,//客户联系人-->联系人ID
'type'=>'2',//类型 客户自定义设置
'probability'=>'100',//可能性
'leadsource'=>'1',//来源 客户自定义设置
'pnote'=>'阶段备注',//阶段备注
'st_time' => string '1498718994', //阶段停留时间，单位为：秒；如果想改为单位：天，需要将本数据除以86400
'mult_select' =>string '河南省-郑州市-中原区-须水镇',//多级分类， 注意：本字段中文名称可设置，因此显示名称各不相同
'ext_sel1' => string '4' //自定义字段1
'ext_item1' => string '很好' //自定义字段2
'ext_item2' => string ',2,3,' //自定义字段3
'ext_item3' => string '39' //自定义字段4
'ext_date1' => string '2017-06-29' //自定义字段5
...
'creatdate' => string '2017-03-16' //创建日期
'moddate' => string '2018-01-16' //修改日期
'amstamp' => string '2018-01-16' //更新日期
'provider' => string '' //提供人

说明：
自定义字段对应的中文名称获取方法：
可以将指定的内容在CRM系统中输入特殊信息，然后用这个接口读取该条信息，进行比较。
在CRM中找到这个字段的输入框，查看该位置的html源代码，如：<input class="form-control" type="text" required="required" name="dt_opport_ext_item1" onkeyup="javascript:chkByteLen( this , 255 );" value="很好">，其中name属性就是数据表名加字段名生成的。从这个地方可以找到的对应的字段信息。
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 数据读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条销售机会数据
            [{销售机会1},{销售机会2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 33. 流程读取接口

- 模块：售后与其他 · cmd：`api.output` · dt：`process_exec`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 流程的读取参数 | {"dt":"process_exec","db_name":"project","db_id":94} |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

### 详细说明

```
接口参数说明：
{
 "dt":"process_exec",//流程数据表的分类
 "db_name":"project",//对应流程关联的对象，如：project 代表项目的流程
 "db_id":94             //指定关联对象的数据ID,如本数据代表：关联项目ID为94的流程
}

假定参数对应数值如下：
param:{"dt":"process_exec","db_name":"project","db_id":94}
stamp:1582184333
upr:{"sid":"0e554d3cfaacb4189a2de9502ae29d40"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"process_exec","db_name":"project","db_id":94}1582184333{"sid":"0e554d3cfaacb4189a2de9502ae29d40"}api.outputopen1slslslsdldlsdlds
md计算结果:d4a030776f13b2af69d060b714b5dd6e

数据表字段说明：
{
    'id' : '42',//关联对象的流程ID
    'name' : '项目流程',//流程名字
    'db_name' : 'project',//关联数据的分类，project代表关联项目
    'db_id' : '94', //关联数据的数据ID
    'status' : '1', ////主流程状态 0:未开始;1:执行中;2:终止;3:结束
    'memo' : '' ,//主流程备注
    'process_step_exec' :
     [
		{
           'id' : '698', //步骤ID
           'number' : '1', //步骤号
           'summary' : '开始', //流程名
           'type' : '5', // 分类 0:且;1:或;2:异或;3;方形;4:菱形;5:开始;6:结束
           'content' : '', //步骤说明
           'actual_person' : '', //实际执行人
           'scheduled_time' : '2020-02-20 11:51:23', //计划完成时间
           'complete_time' : '', //完成/跳过时间
           'takeover_time' : '', //接手时间
           'notified_time' : '', //发送消息通知时间
           'executive' : //执行人信息
            {
             'type' : 'nobody' ,   //执行人分类
             'value': {},   //执行人信息存储的位置
             'name' : '不限',   //执行人分类 对应的中文描述
			},
           'status' : '等待', //步骤状态
           'offset_days' : '0.00', //完成期限
           'memo' : '', //步骤备注
         },
		 {
           ...
		 }
	]
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条流程数据
            [{流程1},{流程2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 34. 附件读取接口

- 模块：基础 · cmd：`api.downfile` · dt：`customer`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.downfile |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549876028 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"4abda94f27512666f079e288ab44a287",//登录接口返回的sid } |
| param | json | 是 | 读取附件的参数 | {  	"dt":"customer",//表名称，customer代表客户信息  	"id":"25"//客户ID} |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

### 详细说明

```
读取附件的参数说明：
{
"dt" : "customer",//表名称，customer代表客户信息 costdetail 代表费用明细，cost代表批单。其他请参考对应的接口
"id" : 25, // 对应数据ID
"field" : "pic",//字段附件的字段名，可选参数：传此值表示只获取当前字段附件的文件列表，不传只获取所有非字段附件的文件（归属数据附件）
                     //新数据有的表如产品、联系人表，不传字段参数，全部作为附件上传，字段图片的话，读取第一个图片附件

}

假定参数对应数值如下：
param:{"dt":"costdetail","id":"285"}
stamp:1581315848
upr:{"sid":"476562f58e591ae7d6afabe2987f3a10"}
cmd:api.downfile
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"costdetail","id":"285"}1581315848{"sid":"476562f58e591ae7d6afabe2987f3a10"}api.downfileopen1slslslsdldlsdlds
md计算结果:a9ca053b884df6c2b38577780a74f916

返回数据说明：
{
 'ok' : 1 (1 接口调用成功， 0 接口调用失败)
   'list' : (附件列表)
    [
      {
       'id' : '970' (附件内部编码)
       'name' : '发货.png' (附件文件名)
       'size' : '372296' (附件大小)
       'ok' : 1 (本数据附件调用成功， 1:成功，0:失败)
       'url' : 'https://xt-upload.oss-cn-hangzhou.aliyuncs.com/da91/costdetail/285/227e8ed23ca77ed16f56f1ecba25133f?OSSAccessKeyId=LTAIrEBvvBX3ratU&Expires=1581319448&Signature=TWuL5LvLEa5wsatrLxz8SxCsAdc%3D' (附件下载路径，有时效性，2个小时内有效)
  },{
       'id' : '969' (附件内部编码)
       'name' : 'qa20191226111045 (1).csv' (附件文件名)
       'size' : '107' (附件大小)
       'ok' : 1(本数据附件调用成功， 1:成功，0:失败)
       'url' : 'https://xt-upload.oss-cn-hangzhou.aliyuncs.com/da91/costdetail/285/15baff75d5f036073f12e0e4b4df73a9?OSSAccessKeyId=LTAIrEBvvBX3ratU&Expires=1581319448&Signature=gBWytjD3rzgkPucAYpQ9mmoZ5M4%3D' (附件下载路径，有时效性，2个小时内有效)
  }
]
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 附件读取状态，1：读取成功，0：读取失败
        data://返回附件的数组，如：多条附件数据
            [{附件1},{附件2}]
        }
}
                            
```

## 35. 批单报销修改接口

- 模块：财务 · cmd：`api.update` · dt：`cost`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.update |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528078285 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid } |
| param | json | 是 | 批单报销的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 6913de14caa74767e360ce918497e085 |

param 示例：

```
{ "dt":"cost",//写入数据的分类，cost代表批单报销 "data"://写入数据分类内容 { "id":0,...}
```

### 详细说明

```
功能说明：
修改接口只针对批单报销一个数据表，费用明细不会处理。
修改时可以只传调整的字段和修改条件。没有改变的内容可以不传。
批单报销的id或者批单报销的编号number作为作为变更的条件传入。

参数param的内容说明：
{
"dt":"cost",//修改数据的分类，cost 代表 批单报销
"data"://修改数据传入内容
{
"id":3,//批单报销ID
"number":"20200109001",//批单报销编码，如果ID存在，则此字段为可修改字段；如果不提供ID,则系统通过编码找批单报销ID，然后修改以下字段
"who":"陈默",//审批人
"aprv_st":"1",//审批状态 0:未审批;1:同意|pass_1;2:否决|vote_1;3:审批中
"aprv_nr":"2020-01-19 10:20 陈默审批 通过",//审批内容
"baox_st":"1",//报销状态 0:未报销;1:报销中;2:已报销
"baox_my":"20",//报销金额
"aprv_status":"4"  //0:非审批; 1:未提交; 2:已提交; 3:审批中; 4:同意; 5:否决; 6:已撤销
}
}

假定参数对应数值如下：
param:{"dt":"cost","data":{"id":3,"who":"陈默","aprv_st":"1","aprv_nr":"2020-01-19 10:20 陈默审批 通过","baox_st":"1","baox_my":"20"}}
stamp:1579511106
upr:{"sid":"5de7730a86237f1498cf4d3ce749ca16"}
cmd:api.update
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"cost","data":{"id":3,"who":"陈默","aprv_st":"1","aprv_nr":"2020-01-19 10:20 陈默审批 通过","baox_st":"1","baox_my":"20"}}1579511106{"sid":"5de7730a86237f1498cf4d3ce749ca16"}api.updateopen1slslslsdldlsdlds
md计算结果:fddb610993dffc1e8bfa6d4f93561865

--------------------------------------------------------------------------------------
特殊情况说明：
参数data下的"aprv_status"和"aprv_st"表面上有些重复，但逻辑使用不同。
aprv_st 只是一个审批状态的记录，可多次重复编辑修改操作。
aprv_status 是CRM系统真正的审批状态，如果aprv_status=4（同意）或aprv_status=5（否决）,则CRM系统中的审批状态将结束，并且不可再次操作数据。
因此，如果想同步CRM系统的审批数据并且不再变更，请提供aprv_status，否则请不要提供aprv_status参数。
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 修改状态，1：修改成功，0：修改失败
        msg:’修改批单报销成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 36. 批单报销读取接口

- 模块：财务 · cmd：`api.output` · dt：`cost`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 批单报销的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{  	"dt":"cost",//读取数据的分类，cost代表批单报销信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
param参数说明：
{
"dt":"cost",//读取数据的分类，cost代表批单报销信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

假定参数对应数值如下：
param:{"dt":"cost","id":1}
stamp:1579506469
upr:{"sid":"a6bee1177851be7b8fa5a0e3517afd1e"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"cost","id":1}1579506469{"sid":"a6bee1177851be7b8fa5a0e3517afd1e"}api.outputopen1slslslsdldlsdlds
md计算结果:665cabd3a2825231186b9da294b44508

获取数据字段说明：
{
       'id' =>'1' (批单报销ID)
       'number' =>'20200117001' (批单报销编号)
       'type' =>'3' (报销类型 具体设置 参考CRM系统自定义设置)
       'date' =>'2020-01-17' (申请日期)
       'sum' =>'123.00' (合计金额)
       'baox_st1' =>'0' (报销状态 0:未报销;1:部分报销;2:已报销)
       'baox_my1' =>'0.00' (报销金额)
       'b_trip_id' =>'0' (关联出差ID)
       'aprv_st' =>'1' (API审批状态 0:未审批;1:同意|pass_1;2:否决|vote_1;3:审批中)
       'aprv_nr' =>'2020-01-19 10:20 陈默审批 通过' (API审批内容)
       'baox_my' =>'20.00' (API报销金额)
       'baox_st' =>'1' (API报销状态 0:未报销;1:报销中;2:已报销)
       'who' =>'陈默' (审批人)
       'part' =>'张三' (申请人)
       'aprv_status' =>'4' (审批状态 0:非审批|fsp_1;1:未提交|wtj_1;2:已提交|up_1;3:审批中;4:同意|pass_1;5:否决|vote_1;6:已撤销|yichexiao_1)
       'memo' =>'' (说明)
       'costdetail' => [
          {
           'id' =>'320' (费用明细ID)
           'money' =>'123.00' (金额)
           'num' =>'1' (票据张数)
           'type' =>'3' (费用类别 请参考自定义设置内容)
           'bill_type' =>'0' (发票类别 请参考自定义设置内容)
           'bill_tax' =>'0' (发票税率 请参考自定义设置内容)
           'human' =>'0' (人数)
           'cu_sn' =>'' (客户 编码)
           'date' =>'2020-01-17' (日期)
           'name' =>'张三' (经手人)
           'reimburse' =>'1' (报销 1:-;2:已报销|pass_1)
           'use' =>'' (用途)
           'memo' =>'' (备注)
  }
 ]
}

如果想减少数据读取的内容，可以参考下面的扩展参数进行实现。
param参数扩展说明：
{
"dt":"cost",//读取数据的分类，cost代表批单报销信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  0,//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
"lasttime":1583202524,//规定数据读取的时间起点，就是从这个时间点，以后修改或新建的才会读取。
 时间点可以接受时间戳(注意必须是10位数字)或者时间字符串(如：2020-03-03 10:39:05)
"baox_st1":2, //报销的状态，0:未报销;1:部分报销;2:已报销
"aprv_status":2 //报销的状态，0:非审批; 1:未提交; 2:已提交; 3:审批中; 4:同意; 5:否决; 6:已撤销
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条批单报销数据
            [{批单报销1},{批单报销2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 37. 费用明细读取接口

- 模块：财务 · cmd：`api.output` · dt：`costdetail`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 费用明细的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{  	"dt":"costdetail",//读取数据的分类，costdetail代表费用明细信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
param参数说明：
{ "dt":"costdetail",//读取数据的分类，costdetail代表费用明细信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

假定参数对应数值如下：
param:{"dt":"costdetail","id":5}
stamp:1579497855
upr:{"sid":"b32830bd678c3e1d14d7125c0348fea3"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"costdetail","id":5}1579497855{"sid":"b32830bd678c3e1d14d7125c0348fea3"}api.outputopen1slslslsdldlsdlds
md计算结果:7908e3f751c5fd6d80c3bc2ad565e8c1

获取数据字段说明：
{
       'id' =>'5' (费用明细ID)
       'money' =>'67.00' (金额)
       'num' =>'1' (票据张数)
       'type' =>'2' (费用类别 请参考自定义设置内容)
       'bill_type' =>'0' (发票类别 请参考自定义设置内容)
       'bill_tax' =>'0' (发票税率 请参考自定义设置内容)
       'human' =>'0' (人数)
       'cu_sn' =>'进度条69' (客户 编码)
       'date' =>'2016-07-21' (日期)
       'name' =>'刘琪琪' (经手人)
       'reimburse' =>'2' (报销 1:-;2:已报销|pass_1)
       'use' =>'' (用途)
       'memo' =>'' (备注)
       'b_trip_id' =>'0' (出差ID)
       'cost_id' =>'0' (批单报销ID)
       'action_id' =>'0' (行动ID)
       'confirm' =>'1' (审批状态)
       'who' =>'王天虹' (审批人)
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条费用明细数据
            [{费用明细1},{费用明细2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 38. 出差读取接口

- 模块：售后与其他 · cmd：`api.output` · dt：`b_trip`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 出差的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{  	"dt":"b_trip",//读取数据的分类，b_trip代表出差信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
param参数说明：
{ "dt":"b_trip",//读取数据的分类，b_trip代表出差信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

假定参数对应数值如下：
param:{"dt":"b_trip","id":74}
stamp:1579488618
upr:{"sid":"8c15b3aecba8ccf4a9e4266db81f6fe0"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"b_trip","id":74}1579488618{"sid":"8c15b3aecba8ccf4a9e4266db81f6fe0"}api.outputopen1slslslsdldlsdlds
md计算结果:b5e262ec3c087ccaf8dbd1ccb373d3cf

获取数据字段说明：
{
   'id' =>'74' (出差ID)
       'owner' =>'王天虹' (申请人)
       'title' =>'去上海回访客户' (出差主题)
       'cu_ids' =>'4,8' (关联客户，多个用逗号分隔)
       'startdate' =>'2018-11-02' (开始日期)
       'enddate' =>'2018-11-07' (结束日期)
       'content' =>'协商项目事宜' (备注)
       'from_address' =>'毕竟' (出发地)
       'des_address' =>'上海' (目的地)
       'bmoney' =>'5000.00' (结款金额)
       'together' =>'刘晓明，张三' (同行人)
       'traffic' =>'1' (交通工具，请参考自定义设置进行处理)
       'prj_id' =>'0' (关联项目ID)
       'status' =>'2' (出差状态	0:未出差;1:出差中;2:出差完成)
       'confirm' =>'2' (审批状态	1:待申请|wait_0;2:同意|pass_1;3:否决|vote_1;4:待审|wait_1)
       'record_log' =>'，推进比较大这次出差感觉整体还是不错，是吧？什么什么的我继续说，上次没说完再说一下' (总结内容)
       'creatdate' =>'2018-11-01' (创建时间)
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条订单数据
            [{出差1},{出差2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 39. 项目读取接口

- 模块：售后与其他 · cmd：`api.output` · dt：`project`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 项目的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{  	"dt":"project",//读取数据的分类，project代表项目信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
param参数说明：
{ "dt":"project",//读取数据的分类，project代表项目信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

假定参数对应数值如下：
param:{"dt":"project","lastid":70}
stamp:1578274045
upr:{"sid":"aeb55a979642f2537db8f63a904580f6"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"project","lastid":70}1578274045{"sid":"aeb55a979642f2537db8f63a904580f6"}api.outputopen1slslslsdldlsdlds
md计算结果:034a0d89d3484b21cc2d963e248392d1

获取数据字段说明：
{
       'id' => '71' (项目ID)
       'subject' => '项目' (标题)
       'who' => 'M12,M18' (项目组成员)
       'date' => '2019-12-25' (立项日期)
       'content' => '' (概要)
       'status' => '-1' (状态)
       'cu_sn' => 'CU16912' (客户编码)
       'phase' => '3' (阶段)
       'type' => '0' (类型)
       'leader' => 'M60' (负责人)
       'expdate' => '2019-12-28' (预计签约日期)
       'exprev' => '600000.00' (预期金额)
       'probability' => '90' (可能性)
       'sal_type' => '4' (售前)
       'owner' => 'M60' (创建人)
       'slog' => '2019-12-25 14:18:40 云琅：
状态【】 阶段【】售前【】
2019-12-25 14:31:11 云琅：
状态【正常】 阶段【项目跟踪】售前【初期沟通】
2019-12-25 18:00:29 boss：
状态【失败】 阶段【项目跟踪】售前【初期沟通】
2019-12-25 18:18:48 boss：
状态【1】 阶段【项目跟踪】售前【初期沟通】
2019-12-25 18:21:54 boss：
状态【失败】 阶段【项目跟踪】售前【初期沟通】
2019-12-25 18:45:28 boss：
状态【失败】 阶段【结项验收】售前【方案制定】
' (推进日志)
       'creatdate' => '2019-12-25' (创建时间)
       'moddate' => '2019-12-25' (修改时间)
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 项目读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条项目数据
            [{项目1},{项目2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 40. 入库单写入接口

- 模块：订单与发货 · cmd：`api.input` · dt：`libin`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1628757241 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | json | 是 | 入库单写入参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 69be2d1efb953eabd93db80560eac9ec |

param 示例：

```
{ 	"dt":"libin",//写入数据的分类，libin代表入库单信息 	      "data":{"title":"open api 入库单导入","lib":1,"date":"2021-08-12","memo":"入库单备注","who":"M1","libitem":[{"prod":"35650","num":2,"memo":"明细备注1"},{"prod":"TS0034","num":2,"memo":"明细备注2"}]},//指定添加信息
```

### 详细说明

```
入库单写入参数说明：
{
	   "dt":"libin",//数据表libin代表入库单写入
       "data":{
			  'title':'open api 入库单导入',//主题 必须输入项目
				'lib':1,//仓库ID 必须输入项目
				'date':'2021-08-12',//填单日期
				'memo':"入库单备注",//入库单备注
				'who':'M1',//填单人，这个是CRM的用户内部part
				"libitem":[//入库明细信息保存的位置,以数组的形式保存
					{"prod":"35650",//产品编码
					"num":2,//入库数量
					"memo":"明细备注1"//明细备注
					},
					{"prod":"TS0034",//产品编码
					"num":2,//入库数量
					"memo":"明细备注2"//明细备注
					},
				]
			 }//数据
};

假定参数对应数值如下：
param:{"dt":"libin","data":{"title":"open api 入库单导入","lib":1,"date":"2021-08-12","memo":"入库单备注","who":"M1","libitem":[{"prod":"35650","num":2,"memo":"明细备注1"},{"prod":"TS0034","num":2,"memo":"明细备注2"}]}}
stamp:1628757241
upr:{"sid":"00927ebe4bc2e3fe0a8be8ba18560b74"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"libin","data":{"title":"open api 入库单导入","lib":1,"date":"2021-08-12","memo":"入库单备注","who":"M1","libitem":[{"prod":"35650","num":2,"memo":"明细备注1"},{"prod":"TS0034","num":2,"memo":"明细备注2"}]}}1628757241{"sid":"00927ebe4bc2e3fe0a8be8ba18560b74"}api.inputopen1slslslsdldlsdlds
md计算结果:69be2d1efb953eabd93db80560eac9ec
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 写入状态，1：写入成功，0：写入失败
        msg:’入库单添加成功！’,//文字说明字符串，写入成功提示，或者失败原因
        id:100//添加的数据ID
        }
}
                            
```

## 41. 入库单完成入库接口

- 模块：订单与发货 · cmd：`api.cmdact` · dt：`libin` · act：`libinok`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1628757241 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | json | 是 | 入库单完成入库参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 69be2d1efb953eabd93db80560eac9ec |

param 示例：

```
{ 	"dt":"libin",//操作数据的分类，libin代表入库单信息 	      "data":{"id":662,"act":"libinok"},//指定操作的入库ID和动作命令
```

### 详细说明

```
完成入库的接口参数说明
{
"dt":"libin",//操作数据的分类，libin代表入库单信息
"data":{//指定操作的入库ID和动作命令
 "id":662,//指定操作的入库单ID, 这个数据来源是：在入库单添加时，如果添加成功，返回接口里面提供的id就是新添加的入库单ID
 "act":"libinok"//操作动作名称，libinok 代表是完成入库的动作
 }
}

假定参数对应数值如下：
param:{"dt":"libin","data":{"id":662,"act":"libinok"}}
stamp:1628761827
upr:{"sid":"66041e26cad74e4e5538030180f2cb13"}
cmd:api.cmdact
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"libin","data":{"id":662,"act":"libinok"}}1628761827{"sid":"66041e26cad74e4e5538030180f2cb13"}api.cmdactopen1slslslsdldlsdlds
md计算结果:f383920e9dfaa1e807a32d91c6f447f9

备注：
完成入库单接口需要提供crm系统的入库单ID,这个id在入库单添加的时候，如果成功会在返回结果中提供。因此该功能应该在入库单添加成功后，进行调用。
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 动作操作状态，1：操作成功，0：操作失败
        msg:’完成入库成功！’,//文字说明字符串，操作成功提示，或者失败原因
        }
}
                            
```

## 42. 出库单读取接口

- 模块：订单与发货 · cmd：`api.output` · dt：`libout`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 出库单的读取参数 | {"dt":"libout","id":178} |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

### 详细说明

```
param参数说明：
{
"dt":"libout", //数据的分类, libout 代表出库单的读取
"id":10, //指定出库单ID，唯一值。有本参数，其他参数将无用
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"lasttime":"2019-12-31 12:01:15",//最后修改时间或者添加时间，本参数接受2种类型的数据，时间字符串或者时间戳 如：2019-12-31 12:01:15 = 1577764875
"mes_work_order_id":10 //生产工单ID，用于对接生产系统，其他功能本参数无用
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"libout","id":178}
stamp:1669796444
upr:{"sid":"547150c150fe7cdc39d3295829998404"}
cmd:api.output
appkey:xtools01f02875167924284317d
计算前字符串:{"dt":"libout","id":178}1669796444{"sid":"547150c150fe7cdc39d3295829998404"}api.outputxtools01f02875167924284317d
md计算结果:4e9032f64856f5349318e10fb0f2989b

返回出库单结果字段说明：
{
"id":"180", //出库单ID
"title":"open api 出库单导入", //出库单标题
"lib":"1", //出库单的出库仓库ID
 "libname":"全国仓库", //出库单的出库仓库名称
"cu_sn":0, //客户编码(字符串型)，如果没有编码，则提供客户ID(数值型)
"date":"2022-11-30", //出库日期
"who":"M1", //经手人，
"memo":"出库单备注", //备注
"co_sn":0, //订单编码(字符串型)，如果没有编码，则提供订单ID(数值型)
"mes_work_order_id":"10", //生产工单ID
"libitem":
[
{
"id":"1087",//出库明细ID
"prod":"862021031558090", //产品编码(字符串型)，如果产品无编码，则提供产品ID(数值型)
"num":"5.000", //出库数量
"cprice":"5.000", //成本价
"memo":"明细备注1",//明细备注
"pid":149, //产品ID
"pro_name":"视频会议",//产品名称
"model":"POLYCOM HDX 6000-720",//产品型号
"sku":"-",//产品sku或规格
"sn":"862021031558090",//产品编码
"batchnum":""//批次
},
{
"id":"1088",//出库明细ID
"prod":147, //产品编码(字符串型)，如果产品无编码，则提供产品ID(数值型)
"num":"2.000",//出库数量
"cprice":"5.000", //成本价
"memo":"明细备注2",//明细备注
"pid":147, //产品ID
"pro_name":"iPhone7s",//产品名称
"model":"128G",//产品型号
"sku":"-",//产品sku或规格
"sn":"",//产品编码
"batchnum":""//批次
}
]
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 出库单　读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条出库单数据
            [{出库单数据1},{出库单数据2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 43. 出库单写入接口

- 模块：订单与发货 · cmd：`api.input` · dt：`libout`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1628757241 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | json | 是 | 出库单写入参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 69be2d1efb953eabd93db80560eac9ec |

param 示例：

```
{ 	"dt":"libout",//写入数据的分类，libout代表出库单信息 	      "data":{"title":"open api 入库单导入","lib":1,"date":"2021-08-12","memo":"入库单备注","who":"M1","libitem":[{"prod":"35650","num":2,"memo":"明细备注1"},{"prod":"TS0034","num":2,"memo":"明细备注2"}]},//指定添加信息
```

### 详细说明

```
出库单写入参数说明：
{
"dt":"libout",//数据表分类 libout 代表出库单的写入
    "data"://添加信息对象
{
  'title':'open api 出库单导入',//主题 必须输入项目
'lib':1,//仓库ID 必须输入项目
'date':'2021-08-12',//填单日期
'cu_sn':'cs100802',//客户编码 无订单可不提供
'co_sn':'HED00274',//订单编码 无订单可不提供
'memo':"出库单备注",//出库单备注
'who':'M1',//经手人，这个是CRM的用户内部part
'mes_work_order_id':1,//生产工单ID,用于对接生产系统，可不提供
"libitem":[//出库明细数组
{
"prod":"TZ00101",//产品编码 字符串型代表产品编码，也可以提供产品id 数字型代表产品ID
"num":5,//出库数量
"memo":"明细备注1"//明细备注
},
{
"prod":114,//产品id 数字型代表产品ID，也可以提供产品编码 字符串型代表产品编码
"num":2,//出库数量
"memo":"明细备注2"//明细备注
},
]
}//数据data
}

假定参数对应数值如下：
param:{"dt":"libout","data":{"title":"open api 出库单导入","lib":1,"date":"2021-08-12","memo":"出库单备注","who":"M1","libitem":[{"prod":"TZ00101","num":5,"memo":"明细备注1"},{"prod":"TS0034","num":2,"memo":"明细备注2"}]}}
stamp:1628846502
upr:{"sid":"f822320516eb4a59fec748bc25111bf9"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"libout","data":{"title":"open api 出库单导入","lib":1,"date":"2021-08-12","memo":"出库单备注","who":"M1","libitem":[{"prod":"TZ00101","num":5,"memo":"明细备注1"},{"prod":"TS0034","num":2,"memo":"明细备注2"}]}}1628846502{"sid":"f822320516eb4a59fec748bc25111bf9"}api.inputopen1slslslsdldlsdlds
md计算结果:5d5e6cea383deba4ccd0e7c249514aa5
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 写入状态，1：写入成功，0：写入失败
        msg:’出库单添加成功！’,//文字说明字符串，写入成功提示，或者失败原因
        id:100//添加的数据ID
        }
}
                            
```

## 44. 出库单完成出库接口

- 模块：订单与发货 · cmd：`api.cmdact` · dt：`libout` · act：`liboutok`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1628757241 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | json | 是 | 出库单完成出库参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 69be2d1efb953eabd93db80560eac9ec |

param 示例：

```
{ 	"dt":"libout",//操作数据的分类，libout代表出库单信息 	      {"id":12572,"act":"liboutok"},//指定操作的出库ID和动作命令
```

### 详细说明

```
完成出库的接口参数说明：
{
"dt":"libout",////操作数据的分类，libout代表出库单信息
"data"://指定操作的出库ID和动作命令
{
"id":12572,//出库单ID,在添加出库单成后时，返回的ID即是出库单ID
"act":"liboutok"//动作命令，liboutok代表出库单完成动作
}
}

假定参数对应数值如下：
param:{"dt":"libout","data":{"id":12572,"act":"liboutok"}}
stamp:1628844430
upr:{"sid":"ca6f87bb527874746d10c85efee050d5"}
cmd:api.cmdact
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"libout","data":{"id":12572,"act":"liboutok"}}1628844430{"sid":"ca6f87bb527874746d10c85efee050d5"}api.cmdactopen1slslslsdldlsdlds
md计算结果:4a3dd4b3194fc8bf8dd69066d3357cde

备注：
由于完成出库的参数需要CRM系统中的出库单ID,而添加出库单可以返回出库单ID,因此，本功能可在出库单完成后进行调用。
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 动作操作状态，1：操作成功，0：操作失败
        msg:’完成出库成功！’,//文字说明字符串，操作成功提示，或者失败原因
        }
}
                            
```

## 45. 发货单读取接口

- 模块：订单与发货 · cmd：`api.output` · dt：`sendgoods`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | json | 是 | 发货单的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{  	"dt":"sendgoods",//读取数据的分类，sendgoods代表发货单  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
param参数说明：
{
"dt":"sendgoods",//读取数据的分类，sendgoods代表发货单
"id":10, //指定出库单ID，唯一值。有本参数，其他参数将无用
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"memo":'123' //通过备注读取信息，该功能可用于数据验证唯一性。
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"sendgoods","memo":"123"}
stamp:1764293596
upr:{"sid":"2f9b990eb5286674b5acc8b0fc501a66"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:
{"dt":"sendgoods","memo":"123"}1764293596{"sid":"2f9b990eb5286674b5acc8b0fc501a66"}api.outputopen1slslslsdldlsdlds
md计算结果:
b7a0acc80caf0bb5c1778a463c02cf28

返回发货单结果字段说明：
{
"id":"2451",//发货单ID
"co_id":"12361",//发货单所属订单
"cu_sn":"11111",//发货单客户 编码
"date":"2025-11-26",//发货日期
"status":"6",//发货状态：1:*已发货;2:已签收;3:其他;4:#待出库;5:#已出库;6:#审核通过;7:#审核否决;8:#已派单
"who":"刘琪峰",//发货人
"sn":"FH,20251126,0001",//发货单编号
"memo":"123",//备注
"sendcomp":"",//物流公司
"name":"",//收货人
"addr":"",//收货地址
"tel":"",//收货电话
"sendcode":"",//物流单号
"deli_note"://发货明细信息
[
{"pid":"1",//产品ID
"price":"11.0000",//产品单价
"num":"1.000",//发货数量
"tax":"1.65",//税金
"sum":"12.65",//金额
"memo":"A，D，F"//明细备注
},
...
]
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 数据读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条发货单数据
            [{发货单1},{发货单2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 46. 产品表读取接口

- 模块：产品与库存 · cmd：`api.output` · dt：`product`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 产品表的读取参数 | {"dt":"product","lasttime":"2022-01-01"} |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

### 详细说明

```
param参数说明：
{
  "dt":"product",  //读取数据的分类，product代表产品表信息
  "id":10,  //指定下载的一条数据的ID号,有这个参数，lastid就不起作用
  "lastid":10,  //指定上次下载的最后一个ID,和参数id二选一
  "lasttime":"2022-09-08", //最后修改时间，可精确到秒　可选参数
  "sn":"产品编号",  //通过产品编码，读取产品信息
    “mflag”:"1",//是否自产，0-否，1-是
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"product","lasttime":"2022-01-01"}
stamp:1663556498
upr:{"sid":"43f5d5137aeb8aed6d65b8de16efa864"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:
{"dt":"product","lasttime":"2022-01-01"}1663556498{"sid":"43f5d5137aeb8aed6d65b8de16efa864"}api.outputopen1slslslsdldlsdlds

md计算结果:07fd75ecd1a42ded85d6fd7385c83612

获取数据字段说明：
{
"id":"95", //产品ID
"name":"主机", //产品名称
"model":"NQ5700", //型号
"sku":"-", //SKU、规格
"sn":"6912581", //产品编码
"class":"安防监控设备", //产品分类
"price":"4899.0000", //成本
"unit":"台", //单位
"intro":"", //产品说明
"faq":"", //常见问题
"memo":"", //备注
"parameter":"四核\/64G\/2T\/6路", //技术参数
"costprice":"4099.0000", //成本价格
"lup":"50.000", //库存上限
"ldown":"10.000", //库存下限
"lnum":"2.000", //库存数量
 "ptype":"是", //是否计算库存， 0:否;1:是;2:外部库存
"pstat":"不需要", //是否需要 调成本价 0:不需要;1:需要
"status":"正常", //产品状态 0:正常;1:停售
"pup_id":"0", //上级产品
"batchnum":"", //批次
"mdate":"", //生产日期
"edate":"", //失效日期
"unit_num":"1.000", //单位换算
"sntype":"否", //是否序列号管理 0:否;1:是;
"pow_type":"", //权限分组
"weight":"7.80", //重量
"w_unit":"kg", //重量单位
"fnum":"0.000", //关注库存
"wxflag":"未展示", //微网展示否 0:未展示;1:展示
 "p_type":"手工", //成本算法 0:手工;1:加权;2:先进先出
	"manufacturer":"", //生产厂家
"approval_num":"", //批准文号
"list_remark":"", //明细概要
"tb_sn":"", //淘宝编号
"jd_sn":"", //京东编号
"tm_sn":"", //天猫编号
"ydh_sn":"", //易订货编号
"hm_shop":"不上架", //虎客好店 0:不上架;1:上架;2:精选
"pmode":"常规产品", //使用方式 0:常规产品;1:非标定制|fbdz;2:租赁专用|zlzy;3:套餐产品|tccp
"svcflag":"否", //三包 0:否;1:是
"mflag":"否", //自产  0:否;1:是
"j1":"2022-01-10", //自定义字段1
"j2":"2022-01-10", //自定义字段2
"j4":"2022-01-10", //自定义字段4
"j5":"" //自定义字段5
“flow_id":""//工艺id
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 产品表　读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条产品数据
            [{产品数据1},{产品数据2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 47. 产品写入接口

- 模块：产品与库存 · cmd：`api.input` · dt：`product`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549951800 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"5fd9f194d62533227df465568a024a3d",//登录接口返回的sid } |
| param | json | 是 | 写入产品的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | f106479a228a964469458bc2b2db8300 |

param 示例：

```
{"dt":"product","data":{"name":"tesla","model":"model 3","sku":"black","sn":"8468326748327648","price":170000}}
```

### 详细说明

```
产品写入参数说明：
{
"dt":"product",//数据表
       "data":{
  'name':'tesla',//产品名
'model':'model x',//型号
' sku':'black',//规格SKU
'sn':'xxxxxx',//产品编码
'price':2231232,//价格
'memo':"备注",//备注
'unit':1,//单位：数字字典“产品-单位”里取数字部分
'mflag':1,//自产  0:否;1:是
'manufacturer':'TESLA',//生产厂家
'intro':'特斯拉 SUV',//产品说明
'ptype':0,//是否计算库存，0：否；1：是；2：外部库存 当启用外部库存时：只能写入0和2，当未启用外部库存时：只能写入0和1
'class':8, //产品分类ID
'list_remark':'明细概要',//明细概要
'parameter':'技术参数',//技术参数
'unit':2,//单位
"pow_type":"1", //权限分组 注意，请使用数据字典中设置的数值
json自定义字段，//根据公司别设置，有所不同
 }//数据
};

假定参数对应数值如下：
param:{"dt":"product","data":{"name":"tesla","model":"model 3","sku":"black","sn":"8468326748327648","price":170000}}
stamp:1694424858
upr:{"sid":"8391e85898850b524391113582556a48"}
cmd:api.input
appkey:xtools01f02875167924284317d
计算前字符串:{"dt":"product","data":{"name":"tesla","model":"model 3","sku":"black","sn":"8468326748327648","price":170000}}1694424858{"sid":"8391e85898850b524391113582556a48"}api.inputxtools01f02875167924284317d
md计算结果:e361ac47d93e0d6d322861013d959208
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 写入状态，1：写入成功，0：写入失败
        msg:’产品信息添加成功！’//文字说明字符串，写入成功提示，或者失败原因
        id:40614
        }
}
                            
```

## 48. 产品修改接口

- 模块：产品与库存 · cmd：`api.update` · dt：`product`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.update |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528078285 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid } |
| param | json | 是 | 产品的修改信息 | {"dt":"product","data":{"sku":"yellow","id":40614}} |
| md | string | 是 | 参数合法性校验码 | 6913de14caa74767e360ce918497e085 |

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"product","data":{"sku":"yellow","id":40614}}
stamp:1694482339
upr:{"sid":"79f8d674d8693b3da754275bfe82aaa1"}
cmd:api.update
appkey:xtools01f02875167924284317d
计算前字符串:{"dt":"product","data":{"sku":"yellow","id":40614}}1694482339{"sid":"79f8d674d8693b3da754275bfe82aaa1"}api.updatextools01f02875167924284317d
md计算结果:818c19b69005d0f7b189a1c59c2cad44

参数说明：
{"dt":"product",
"data":
{
"id":553,//产品ID：需要修改的产品id
 'name':'tesla',//产品名
'model':'model x',//型号
'sku':'black',//规格SKU
'sn':'xxxxxx',//产品编码
'price':2231232,//价格
'memo':"备注",//备注
'unit':1,//单位：数字字典“产品-单位”里取数字部分
'mflag':1,//自产  0:否;1:是
'manufacturer':'TESLA',//生产厂家
'ptype':0,//是否计算库存，0：否；1：是；2：外部库存 当启用外部库存时：只能写入0和2，当未启用外部库存时：只能写入0和1
'class':8, //产品分类ID
'list_remark':'明细概要',//明细概要
'parameter':'技术参数',//技术参数
'unit':2,//单位
"pow_type":"1", //权限分组 注意，请使用数据字典中设置的数值
json自定义字段，//根据公司别设置，有所不同
}
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 修改状态，1：修改成功，0：修改失败
        msg:’产品信息[id:40614]修改成功！’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 49. 产品客制别名读取接口

- 模块：产品与库存 · cmd：`api.output` · dt：`prod_alias`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 产品客制别名的读取参数 | {"dt":"prod_alias","id":10} |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

### 详细说明

```
param参数说明：
{
  "dt":"prod_alias",  //读取数据的分类，prod_alias代表产品客制别名信息
  "id":10,  //指定下载的一条数据的ID号,有这个参数，lastid就不起作用
  "lastid":10,  //指定上次下载的最后一个ID,和参数id二选一
  "cu_id":10,  //指定所属客户
 "pid":10,  //指定所属产品
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"prod_alias","cu_id":1,"pid":15152}
stamp:1719450952
upr:{"sid":"52c8d0acd2aef86a434a12a834fb46f3"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"prod_alias","cu_id":1,"pid":15152}1719450952{"sid":"52c8d0acd2aef86a434a12a834fb46f3"}api.outputopen1slslslsdldlsdlds
md计算结果:8cf49a184cae5930f47ac960e1637a38

获取数据字段说明：
{
    "id":"6",                            //数据ID
    "cu_sn":"CJKH000769",    //客户编码
    "pid":"11870",                  //产品ID
    "name":"red\u7cd6\u76d2",  //产品客制别名
    "sn":"",                                    //产品客制编码
    "memo":"qwwq",                   //备注说明
    "cu_id":43774                        //客户ID 这个是追加的，方便其他地方使用
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条产品数据
            [{产品客制别名数据1},{产品客制别名数据2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 50. 产品客制别名写入接口

- 模块：产品与库存 · cmd：`api.input` · dt：`prod_alias`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549951800 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"5fd9f194d62533227df465568a024a3d",//登录接口返回的sid } |
| param | json | 是 | 写入产品客制别名信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | f106479a228a964469458bc2b2db8300 |

param 示例：

```
{"dt":"prod_alias","data":{"cu_sn":0,"pid":126,"name":"A139-4","sn":"NA129004"}}
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"prod_alias","data":{"cu_sn":0,"pid":127,"name":"A139-4","sn":"NA1129004","memo":"测试"}}
stamp:1717036971
upr:{"sid":"de9e2bb24447874ae4ae433b66eb4b97"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"prod_alias","data":{"cu_sn":0,"pid":127,"name":"A139-4","sn":"NA1129004","memo":"测试"}}1717036971{"sid":"de9e2bb24447874ae4ae433b66eb4b97"}api.inputopen1slslslsdldlsdlds
md计算结果:35df4a77dbb4a9844bd8317ca74be14e

产品客制别名、编号写入参数说明：
{
"dt":"prod_alias",//数据表 产品客制化别名、编号
       "data":{//数据写入内容
            "cu_sn":0, //字符串为客户编号，如果是数字为客户id, 指定使用客制化别名的客户
            "pid":126,//所属产品id 必填项
            "name":"红米手机",//客制别名  和 编号至少有一项不为空
            "sn":"NA129004",  //客制编号  和 别名至少有一项不为空
            "memo":"备注信息", //备注
       }//数据
};
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 写入状态，1：写入成功，0：写入失败
        msg:’产品客制别名/编号添加成功！’//文字说明字符串，写入成功提示，或者失败原因
        id:40614  //添加数据ID
        }
}
                            
```

## 51. 产品价格策略变更接口

- 模块：产品与库存 · cmd：`api.cmdact` · dt：`product` · act：`chg_str_ps`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 价格策略变更参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |
|  | string | 是 |  |  |

param 示例：

```
{"dt":"product","data":{"id":15198,"act":"chg_str_ps","data":{"4":"ceshi1","5":"ceshi2"}}}
```

### 详细说明

```
param参数说明：
{
 "dt":"product", //数据的分类，product代表产品信息
 "data": //动作描述的ｊｓｏｎ对象
{
"id":15198, //产品ＩＤ
"act":"chg_str_ps" //动作分类，chg_str_ps表示　变更价格策略的动作
data:{//价格策略内容
 4:"98",//key值4代表的价格策略的数据字典中的序号。value值98代表这个策略的价格
    5:"99",//key值5代表的价格策略的数据字典中的序号。value值99代表这个策略的价格
 }
}
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"product","data":{"id":15198,"act":"chg_str_ps","data":{"4":"ceshi1","5":"ceshi2"}}}
stamp:1723446782
upr:{"sid":"92140f318b6227fcba9e470271a31511"}
cmd:api.cmdact
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"product","data":{"id":15198,"act":"chg_str_ps","data":{"4":"ceshi1","5":"ceshi2"}}}1723446782{"sid":"92140f318b6227fcba9e470271a31511"}api.cmdactopen1slslslsdldlsdlds
md计算结果:c25272aa7016d0c4f36aeb5c01578825
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 返回状态，　　1：修改成功，0：修改失败
        msg:"变更价格策略成功"　　//返回变更数据状态的描述
        }
}
                            
```

## 52. 产品分类写入接口

- 模块：产品与库存 · cmd：`api.input` · dt：`csstree`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549956700 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"5c08e77b2100df75bc4ae3c45a65754c"} |
| param | string | 是 | 写入产品分类的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | b9655d6347a0a9075c011c1eef580282 |

param 示例：

```
{"dt":"csstree","data":{"id":0,"tid":1,"upid":11,"title":"测试分类"}}
```

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
|  |  | string |  |  |

### 详细说明

```
param中数据的说明：
{
"dt":"csstree",//数据分类，csstree代表产品分类
"data":{
"id":0, //产品分类ID,写入时，id=0
"tid":"1",//树编号，默认为1
"title":"测试分类",//标题 。
"upid":"上级节点id
}
}

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"csstree","data":{"id":0,"tid":1,"upid":11,"title":"测试分类"}}
stamp:1723711883
upr:{"sid":"58876e089c14f2fc7964db1915d7d972"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"csstree","data":{"id":0,"tid":1,"upid":11,"title":"测试分类"}}1723711883{"sid":"58876e089c14f2fc7964db1915d7d972"}api.inputopen1slslslsdldlsdlds
md计算结果:b9655d6347a0a9075c011c1eef580282
```

### 返回示例

```
                                {
    "ok":1,
    "ret":{
        "ok":1,
        "msg":"保存成功",
        "id":64
    }
    
}
                            
```

## 53. 产品分类读取接口

- 模块：产品与库存 · cmd：`api.output` · dt：`csstree`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | string | 是 | 产品分类的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{  	"dt":"csstree",//读取数据的分类，csstree代表分类信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
param中数据的说明：
{
"dt":"csstree",//数据分类，csstree代表产品分类
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10,//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
"title":"测试标题",//标题
"upid":3,//父级id
"status":0,//状态，0：表示无下级；1：表示有下级
}

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:param:{"dt":"csstree","id":11}
stamp:1723709908
upr:{"sid":"252a5568b0fa2cee24cf6c7ab53a389c"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"csstree","id":11}1723709908{"sid":"252a5568b0fa2cee24cf6c7ab53a389c"}api.outputopen1slslslsdldlsdlds
md计算结果:d416f2cfde6b80ba30e6326761694109
```

### 返回示例

```
                                {
    "ok": 1,
    "ret": {
        "ok": 1,
        "data": [
            {
                "id": "11",
                "tid": "1",
                "title": "颐",
                "upid": "2",
                "status": "1"
            }
        ]
    }
}
                            
```

## 54. 收发货通知单读取接口

- 模块：订单与发货 · cmd：`api.output` · dt：`sr_notice`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 收发货通知单的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{  	"dt":"sr_notice",//读取数据的分类，sr_notice代表收发货通知单信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
收发货通知单的外部系统调用过程建议
一、读取订单的发货通知
1）读取收发货通知单
2）发货通知单写入外部系统，如写入成功，则继续下面操作
3）回写已读状态到CRM的收发货通知单，如回写成功，则继续
4）如回写失败，则说明收发货通知单在这个微小的时间差发生了状态变化（变为关闭了），则找到外部系统刚写入的订单，状态也改为关闭
目的：避免在读写执行过程中，CRM操作收发货通知单为关闭，此时要保障两边系统严格同步：关闭 状态，避免关闭单据发货。

二、 外部执行出库发货并回写执行结果到超兔
1）先读取超兔CRM对应的收发货通知单，检查其状态是否=关闭，如果是则中止执行出库发货的操作。
2）收发货通知单状态为关闭的概率很低，但是两套系统读写处理都需要时间，时间差不可避免，依靠单方的数据校验无法做到严丝合缝，所以增加保护措施，避免关闭订单发货给客户带来损失。
3）如果状态正常，则可以正常出库发货，完成后向CRM系统回写执行结果。

param参数说明：
{
 "dt":"sr_notice", //读取数据的分类，sr_notice代表收发货通知单信息
 "id":10, //指定下载的一条数据的ID号,有这个参数，lastid就不起作用
 "lastid":10, //指定上次下载的最后一个ID,和参数id 二选一
 "lasttime":"2022-09-08", //最后修改时间，可精确到秒　可选参数
 "type":1, //收发货通知单类型　可选参数 0:订单-发货;1:采购-收货;2:订单退货-收货;3:采购退货-发货
 "status":1 //收发货通知单状态　可选参数 0:临时;1:*API未读;2:API已读;3:部分执行;4:全部执行;5:已关闭;6:部分执行API已读;7:API错误
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"sr_notice","id":10,"lastid":10,"lasttime":"2022-09-08","type":1,"status":1}
stamp:1663225528
upr:{"sid":"4aeae120971438153c40397a2d829f11"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:
{"dt":"sr_notice","id":10,"lastid":10,"lasttime":"2022-09-08","type":1,"status":1}1663225528{"sid":"4aeae120971438153c40397a2d829f11"}api.outputopen1slslslsdldlsdlds

md计算结果:bec43ba2510e8047449ec99bf0cd15d1

获取数据字段说明：
{
   "id":"1", //收发货通知单 ID
 "subject":"订单测试", //收发货通知单 标题
 "cu_sn":"C00001", //客户编码
"lib":"1",//仓库ID，出、入库仓库ID
"libname":"北京仓库",//仓库名称，出、入库仓库
 "erp_no":"N000001", //收发货通知单 编码,
 "type":"0", //0:订单-发货;1:采购-收货;2:订单退货-收货;3:采购退货-发货
 "mid":"289", //关联 主单，如 type=0时，这个mid就是订单id; type=1时，这个mid就是采购单id; type=2时，这个mid就是退货单id;
 "status":"4", //0:临时;1:*API未读;2:API已读;3:部分执行;4:全部执行;5:已关闭;6:部分执行API已读;7:API错误
 "who":"陈默", //负责人
 "memo":"", //收发货通知单　的备注
 "name":"", //收、发货人
 "mphone":"", //收、发货人电话
 "addr":"", //收、发货地址
 "date":"2022-09-06",//收发货日期
 "eta":"2022-12-06",//预计到货日期
"sendcomp":"韵达",//物流公司
 "sendcode":"", //快递单号
 "log":"2022-09-13 11:44:49 API第 1 次执行\n2022-09-13 11:38:58 API第 2 次执行\n2022-09-09 16:14:58 API第 1 次执行\n2022-09-09 16:07:05 API第 1 次执行\n",
 "sr_notice_item":
 [
 {
 "id":"1", //通知单明细ＩＤ
 "prod":"WB0001", //通知单明细产品编码
 "num":"1.000", //通知单明细产品数量
 "num_exc":"1.000", //通知单明细产品执行数量
 "memo":"", //通知单明细备注
 "prod_name":"测试库存产品", //产品名称
 "model":"", //产品型号
 "sku":"-", //ｓｋｕ、规格
 "batchnum":"", //批次
"price":200, //单价
"money_type":RMB, //币种
"money_rate":100 //汇率，以100元人民币兑换的外币数量
 }
 ]
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 收发货通知单　读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条收发货通知单数据
            [{收发货通知单1},{收发货通知单2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 55. 收发货通知单状态变更接口

- 模块：订单与发货 · cmd：`api.cmdact` · dt：`sr_notice` · act：`chgst`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 收发货通知单的状态变更参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{"dt":"sr_notice","data":{"id":1,"erp_no":"N000001","status":2,"act":"chgst"}}
```

### 详细说明

```
注意：本功能判断是否启用了外部库存功能。未启用的账号，无法调用此接口。
应用场景：
读取未读（1:*API未读）数据后，将本收发货通知单改变为已读（2:API已读），同时将外部系统对应的单据编码回填入CRM系统。
读取部分执行（3:部分执行）数据后，将本收发货通知单改变为已读（6:部分执行API已读）。
如果收发货通知单需要删除或撤销，无存在的必要时，可将本收发货通知单改变为已关闭（5:已关闭）。

param参数说明：
{
 "dt":"sr_notice", //数据的分类，sr_notice代表收发货通知单信息
 "data": //动作描述的ｊｓｏｎ对象
{
"id":1, //收发货通知单ＩＤ，用这个处理指定的收发货通知单数据
"erp_no":"N000001", //收发货通知单编码，将指定的通知单的编码进行变更。如果不改变，可不提供本参数。
"status":2, //收发货通知单状态，将指定的通知单的状态进行变更。0:临时;1:*API未读;2:API已读;3:部分执行;4:全部执行;5:已关闭;6:部分执行API已读;7:API错误
"log":"修改状态的说明内容",//本参数可选，用于在CRM的日志中展示，提醒客户的内容。
"act":"chgst" //动作分类，chgst表示　改变状态的动作，该参数是本接口的唯一区分
}
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"sr_notice","data":{"id":1,"erp_no":"N000001","status":2,"act":"chgst"}}
stamp:1663307556
upr:{"sid":"384d2aa96534a8a5300054c854070b33"}
cmd:api.cmdact
appkey:open1slslslsdldlsdlds
计算前字符串:
{"dt":"sr_notice","data":{"id":1,"erp_no":"N000001","status":2,"act":"chgst"}}1663307556{"sid":"384d2aa96534a8a5300054c854070b33"}api.cmdactopen1slslslsdldlsdlds

md计算结果:96f2e92a89075c683ccac0536e279d54

说明：
状态变更可修改的状态只能为：2:API已读;5:已关闭;6:部分执行API已读;7:API错误
当前通知单状态为：已关闭 的情况下，不可以进行状态变更，接口会返回错误。
外部系统操作需要严格校验收发货通知单的状态，关闭或错误的通知单应避免后续业务的继续运行。
 设置收发货通知单状态时，如果返回错误，说明改通知单状态已关闭，不能继续后续操作。
 执行收发货通知单时，如果返回错误，说明通知单状态可能已关闭，也不能继续后续操作。
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 返回状态，　　1：修改成功，0：修改失败
        msg:"修改状态成功"　　//返回修改数据状态的描述
        }
}
                            
```

## 56. 收发货通知单执行接口

- 模块：订单与发货 · cmd：`api.cmdact` · dt：`sr_notice` · act：`exc`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 收发货通知单的明细执行参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{"dt":"sr_notice","data":{"id":13,"who":"李能","date":"2022-09-13","sendcode":"98837737101","child":[{"prod":"WB0001","num":2,"costprice":100,"memo":"执行日志"}],"act":"exc"}}
```

### 详细说明

```
收发货通知单的外部系统调用过程
一、读取订单的发货通知
1）读取收发货通知单
2）发货通知单写入外部系统，如写入成功，则继续下面操作
3）回写已读状态到CRM的收发货通知单，如回写成功，则继续
4）如回写失败，则说明收发货通知单在这个微小的时间差发生了状态变化（变为关闭了），则找到外部系统刚写入的订单，状态也改为关闭
目的：避免在读写执行过程中，CRM操作收发货通知单为关闭，此时要保障两边系统严格同步：关闭 状态，避免关闭单据发货。

二、 外部执行出库发货并回写执行结果到超兔
1）先读取超兔CRM对应的收发货通知单，检查其状态是否=关闭，如果是则中止执行出库发货的操作。
2）收发货通知单状态为关闭的概率很低，但是两套系统读写处理都需要时间，时间差不可避免，依靠单方的数据校验无法做到严丝合缝，所以增加保护措施，避免关闭订单发货给客户带来损失。
3）如果状态正常，则可以正常出库发货，完成后向CRM系统回写执行结果。

注意：
本功能判断是否启用了外部库存功能。未启用的账号，无法调用此接口。
本接口判断了收发货通知单的状态，如果是关闭的收发货通知单，执行会有错误提示。如果外部系统的发货在执行接口调用之前，需要自行判断通知单状态再发货。
即：关闭的通知单不应该发货或执行。
本接口调用后，产品库存的变更，需要再调用 外部库存变更接口 来实现。
一次执行，一个产品可以输入多条执行明细。
如果是订单的发货通知单，自动生成发货单时，一个产品的产品数量会合计起来，生成一个产品一条的发货明细。

param参数说明：
{
  "dt":"sr_notice", //数据的分类，sr_notice代表收发货通知单信息
  "data": //动作描述的ｊｓｏｎ对象
{
"id":1, //收发货通知单ＩＤ，用这个处理指定的收发货通知单数据。和erp_no参数２选１
"erp_no":"N000001", //收发货通知单编码，用这个处理指定的收发货通知单数据。和id参数２选１
"who":"李能", //执行人
"date":"2022-09-13", //执行时间
"sendcode":"98837737101", //物流单号
"child": //执行明细的列表
[
{
"prod":"WB0001",　//执行产品编码
"num":2, //执行数量
"costprice":100, //单个成本价
"memo":"执行日志" //产品别执行日志、备注
}
],
"act":"exc" ,//动作分类，exc 表示　通知单执行的动作，该参数是本接口的唯一区分
"no_more":1 //可选参数，如果没本参数，缺省：0,对执行数量不进行控制；设置值为1：则控制执行数量之和不能大于通知数量。
}
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"sr_notice","data":{"id":13,"who":"李能","date":"2022-09-13","sendcode":"98837737101","child":[{"prod":"WB0001","num":2,"costprice":100,"memo":"执行日志"}],"act":"exc"}}
stamp:1663313492
upr:{"sid":"b66e305585dc4f9a5ef667782549c508"}
cmd:api.cmdact
appkey:open1slslslsdldlsdlds
计算前字符串:
{"dt":"sr_notice","data":{"id":13,"who":"李能","date":"2022-09-13","sendcode":"98837737101","child":[{"prod":"WB0001","num":2,"costprice":100,"memo":"执行日志"}],"act":"exc"}}1663313492{"sid":"b66e305585dc4f9a5ef667782549c508"}api.cmdactopen1slslslsdldlsdlds

md计算结果:3aa53eb432b8864ee05018855c4feb1f

执行结果后台处理：
将执行数量合计到收发货通知单对应的产品明细中，同时修改通知单的状态为：部分执行或全部执行。
如果主单是订单，则根据执行数据自动生成订单的发货单，计算订单明细已交付数量，修改订单发货状态，部分或全部发货。
如果主单是采购单，则根据执行数据自动计算采购明细入库量，修改采购单状态，变为3部分入库或4入库完成。
如果主单是订单退货，则根据执行数据自动计算退货明细入库量，修改退货入库状态，变为部分入库或全部入库。
如果主单是采购退货，则根据执行数据自动计算退货明细出库量，修改退货出库状态，变为部分出库或全部出库；修改退货单状态为：执行中或结束。

通知单执行业务说明：
业务场景1:(执行参数no_more=0或不提供）
接口调用的执行数量不进行控制，执行数量是多少，业务处理数量就是多少。
如果发现执行数量超出，可通过 提供执行数量为负值进行对冲。
业务场景2:(执行参数no_more=1）
接口调用的执行数量进行校验，如果已执行数量、当前执行数量之和 大于 收发货通知单中该产品数量，则提示错误，无法执行。
错误提示如：{ok:0,msg:"产品：GP036141 皇裕 盘子 执行数量超出，无法执行。(通知数量：15，已执行：15，本次执行：15)"}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 返回状态，　　1：执行结果成功，0：执行结果失败
        msg:"执行成功"　　//返回执行结果的描述
        }
}
                            
```

## 57. 外部库存变更接口

- 模块：产品与库存 · cmd：`api.cmdact` · dt：`libn` · act：`erp_libn`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 外部库存变更参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{"dt":"libn","data":{"lib":3,"prod":"WB0001","num":8,"memo":"测试外部库存","act":"erp_libn"}}
```

### 详细说明

```
注意：本功能判断是否启用了外部库存功能。未启用的账号，无法调用此接口。

param参数说明：
{
"dt":"libn", //数据的分类，libn代表库存管理信息
"data": //操作动作JSON对象
{
"lib":3, //库存仓库，可以是仓库ID（此时，参数数据类型是数字型），也可以是仓库名称（此时，参数数据类型是文本型），如果仓库的名称不存在，还可以自动追加一个新仓库
"prod":"WB0001", //库存产品编码
"num":8, //库存数量
"memo":"测试外部库存", //备注
"act":"erp_libn" //动作分类，erp_libn表示　外部库存变更的动作，该参数是本接口的唯一区分
}
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"libn","data":{"lib":3,"prod":"WB0001","num":8,"memo":"测试外部库存","act":"erp_libn"}}
stamp:1663554294
upr:{"sid":"7a30269bb89c68607884b04fa3aa0a4f"}
cmd:api.cmdact
appkey:open1slslslsdldlsdlds
计算前字符串:
{"dt":"libn","data":{"lib":3,"prod":"WB0001","num":8,"memo":"测试外部库存","act":"erp_libn"}}1663554294{"sid":"7a30269bb89c68607884b04fa3aa0a4f"}api.cmdactopen1slslslsdldlsdlds

md计算结果:a14823f751e2143ee77ba5f871ca853a
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 返回状态，　　1：修改成功，0：修改失败
        msg:"外部库存录入成功"　　//返回修改外部库存结果的描述
        }
}
                            
```

## 58. 合同读取接口

- 模块：订单与发货 · cmd：`api.output` · dt：`contract0`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 合同的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{  	"dt":"contract0",//读取数据的分类，contract0代表合同信息  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
参数说明：
{ "dt":"contract0",//读取数据的分类，contract0代表合同信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

md参数计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"contract0"}
stamp:1668998593
upr:{"sid":"a0c26f8615f1d6a573d65ba0e5b9a774"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"contract0"}1668998593{"sid":"a0c26f8615f1d6a573d65ba0e5b9a774"}api.outputopen1slslslsdldlsdlds
md计算结果:9dbbaf615687c75ad21d5875ff20330f

字段说明：
{
	"id":"9236",//合同ID
	"subject":"HT00007接口添加",//合同标题
	"cu_sn":"0067",//客户编号，需要转换为客户的ID进行 保存
	"No.":"HT000007",//合同编号
	"type":"1",//分类 参考数据字典 自定义内容
	"sum":"7025.36",//总金额
	"sum_memo":"外币备注",//外币备注
	"back_sum":"1000.00",//回款
	"who":"boss",//合同所有者
 "name":"zjb1111",//收货人姓名
 "tel":"18910785591",//收货人电话
 "addr":"中国北京海淀区中关村北大街151号428",//收货人地址
	"memo":"memo",//合同备注
	"date":"2022-11-21",//签约日期
	"begin_date":"2022-11-11",//开始时间
	"end_date":"2022-11-21",//结束时间
	"money_type":"USD",//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
	"money_rate":"629",//汇率，可不传递
	"status":"2",//状态 1:*执行中|suc_no;2:结束|stop;3:意外中止|cancel;-1:#预定;-2:#借出未还;-3:#关闭
	"state":"0",//省份
	"city":"",//城市
	"mphone":"",//手机
	"pst":"",//邮编
	"cu_user":"签约人",//签约人
	"pay_mode":"-1",//付款方式 参考 数据字典 自定义内容
	"payment":"7",//结款方式
	"deli_place":"",//交付地点
	"prj_id":"0",//对应项目ID
	"op_id":"0",//对应机会ID
	"j1":null,//自定义字段1
	"j2":null,//自定义字段2
	"j3":"2019-12-27",//自定义字段3
	"j4":"90公斤"//自定义字段4
	... 其他自定义字段
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 合同读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条订单数据
            [合同1},{合同2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 59. 合同写入接口

- 模块：订单与发货 · cmd：`api.input` · dt：`contract0`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528095120 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"e6cf1667f7811d36df0f483b01128132"} |
| param | json | 是 | 写入合同的数据信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | e9204980c6b87bb9d7f88257a17c6672 |

param 示例：

```
{"dt":"contract0","data":{"subject":"HT00007接口添加", "cu_sn":"0067","No.":"HT000007","sum":"7025.36","back_sum":1000, "type":"1","status":2,"who":"B1","date":"2022-11-21","begin_date":"2022-11-11", "end_date":"2022-11-21","money_type":"USD","money_rate":"629", "payment":7,"sum_memo":"外币备注", "cu_user":"签约人","deli_place":"交付地点", "prj_id":"1","op_id":"0"}}
```

### 详细说明

```
参数param的说明：
{"dt":"contract0",//写入数据的分类，contract0代表合同写入
"data":
 {
		"subject":"HT00007接口添加",//合同标题
		"cu_sn":"0067",//客户编号，需要转换为客户的ID进行 保存
		"No.":"HT000007",//合同编号
		"type":"1",//分类 参考数据字典 自定义内容
		"sum":"7025.36",//总金额
		"sum_memo":"外币备注",//外币备注
		"back_sum":"1000.00",//回款
		"who":"boss",//合同所有者
 "name":"zjb1111",//收货人姓名
 "tel":"18910785591",//收货人电话
 "addr":"中国北京海淀区中关村北大街151号428",//收货人地址
		"memo":"memo",//合同备注
		"date":"2022-11-21",//签约日期
		"begin_date":"2022-11-11",//开始时间
		"end_date":"2022-11-21",//结束时间
		"money_type":"USD",//币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
		"money_rate":"629",//汇率，可不传递
		"status":"2",//状态 1:*执行中|suc_no;2:结束|stop;3:意外中止|cancel;-1:#预定;-2:#借出未还;-3:#关闭
		"state":"0",//省份
		"city":"",//城市
		"mphone":"",//手机
		"pst":"",//邮编
		"cu_user":"签约人",//签约人
		"pay_mode":"-1",//付款方式 参考 数据字典 自定义内容
		"payment":"7",//结款方式
		"deli_place":"",//交付地点
		"prj_id":"0",//对应项目ID
		"op_id":"0",//对应机会ID
		"j1":null,//自定义字段1
		"j2":null,//自定义字段2
		"j3":"2019-12-27",//自定义字段3
		"j4":"90公斤"//自定义字段4
 }
}

md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
计算用例如下：
param:{"dt":"contract0","data":{"subject":"HT00007接口添加","cu_sn":"0067","No.":"HT000007","sum":"7025.36","back_sum":1000,"type":"1","status":2,"who":"B1","memo":"memo","name":"zjb1111","tel":"18910785591","addr":"中国北京海淀区中关村北大街151号428","date":"2022-11-21","begin_date":"2022-11-11","end_date":"2022-11-21","money_type":"USD","money_rate":"629","payment":7,"sum_memo":"外币备注","cu_user":"签约人","deli_place":"交付地点","prj_id":"1","op_id":"0","j3":"2019-12-27","j4":"90公斤","j6":"4","j7":"2019-12-27","j8":"2019-12-27","j10":"2019-12-27","j11":"2019-12-27","j13":"2019-12-27","j14":",1,2,","j15":"文本测试缺省","j16":"2"}}
stamp:1669016873
upr:{"sid":"c9cccba9208356ec089d2e2e392af976"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"contract0","data":{"subject":"HT00007接口添加","cu_sn":"0067","No.":"HT000007","sum":"7025.36","back_sum":1000,"type":"1","status":2,"who":"B1","memo":"memo","name":"zjb1111","tel":"18910785591","addr":"中国北京海淀区中关村北大街151号428","date":"2022-11-21","begin_date":"2022-11-11","end_date":"2022-11-21","money_type":"USD","money_rate":"629","payment":7,"sum_memo":"外币备注","cu_user":"签约人","deli_place":"交付地点","prj_id":"1","op_id":"0","j3":"2019-12-27","j4":"90公斤","j6":"4","j7":"2019-12-27","j8":"2019-12-27","j10":"2019-12-27","j11":"2019-12-27","j13":"2019-12-27","j14":",1,2,","j15":"文本测试缺省","j16":"2"}}1669016873{"sid":"c9cccba9208356ec089d2e2e392af976"}api.inputopen1slslslsdldlsdlds
md计算结果:16f8f14ac1744ac124764cfa93674e59
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 合同写入状态，1：写入成功，0：写入失败
        msg:’添加订单成功’//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 60. 字段信息（数据字典）读取接口

- 模块：基础 · cmd：`api.fieldinfo` · dt：`customer`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.fieldinfo |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1655972843 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | json | 是 | 字段信息（数据字典）读取接口参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 8b673832d84b1ab034b9668fc806a43a |

param 示例：

```
{ 	"dt":"customer",//数据表的分类，customer代表客户表 	      "field":"cu_status"//字段名称},
```

### 详细说明

```
字段信息（数据字典）读取接口参数param说明：
{
"dt":"customer",////数据表的分类，customer代表客户表
"field":"cu_status"//需获取信息的指定字段
}

假定参数对应数值如下：
param:{"dt":"customer","field":"cu_status"}
stamp:1655972843
upr:{"sid":"fc7c5ee14bcab84057f291e243b668dd"}
cmd:api.fieldinfo
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"customer","field":"cu_status"}1655972843{"sid":"fc7c5ee14bcab84057f291e243b668dd"}api.fieldinfoopen1slslslsdldlsdlds
md计算结果:8b673832d84b1ab034b9668fc806a43a
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 动作操作状态，1：操作成功，0：操作失败
        msg:’成功！’,//文字说明字符串，操作成功提示，或者失败原因
        data:[
            {
                "key":"1",//数据字典的键值key
                "value":"1.售前跟踪",//数据字典的键值key 对应的展示内容 value
                "flag":"USE"//本键值的数据状态：USE代表可用，Defualt代表可用且为缺省值，NO USE 代表当前已弃用（只可查看，不可作为编辑选择项）
            },{"key":"2","value":"2.合同执行","flag":"Default"},{"key":"3","value":"3.售后服务","flag":"USE"},{"key":"4","value":"4.合同期满","flag":"USE"}
            ]
        }
}
                            
```

## 61. 字段信息（字段名称）读取接口

- 模块：基础 · cmd：`api.fieldinfo` · dt：`customer` · act：`dbcn`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.fieldinfo |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1655972843 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | json | 是 | 字段信息（字段名称）读取接口参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 8b673832d84b1ab034b9668fc806a43a |

param 示例：

```
{ 	"dt":"customer",//数据表的分类，customer代表客户表 "act":"dbcn"//字段名称},
```

### 详细说明

```
字段信息（字段名称）读取接口参数param说明：
{
"dt":"customer",////数据表的分类，customer代表客户表
"act":"dbcn"// 动作分类: dbcn 代表 字段名称读取
}

假定参数对应数值如下：
param:{"dt":"customer","act":"dbcn"}
stamp:1754462878
upr:{"sid":"7bad012c6155df5197b7f602b3d1dc8a"}
cmd:api.fieldinfo
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"customer","act":"dbcn"}1754462878{"sid":"7bad012c6155df5197b7f602b3d1dc8a"}api.fieldinfoopen1slslslsdldlsdlds
md计算结果:1aef172553cc66aae8075bf641b73235
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 动作操作状态，1：操作成功，0：操作失败
        msg:’成功！’,//文字说明字符串，操作成功提示，或者失败原因
        data://字段信息
        {'id':'ID',
          'owner':'所有者',
          'rpower':'读权限',
          'lockflag':'封存标志',
            ...
         }
        }
}
                            
```

## 62. 字段信息（用户）读取接口

- 模块：基础 · cmd：`api.fieldinfo` · dt：`customer` · act：`pr2nm`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.fieldinfo |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1655972843 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"00927ebe4bc2e3fe0a8be8ba18560b74",//登录接口返回的sid } |
| param | json | 是 | 字段信息（字段名称）读取接口参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 8b673832d84b1ab034b9668fc806a43a |

param 示例：

```
{ 	"dt":"customer",//数据表的分类，customer代表客户表 "act":"pr2nm"//用户信息},
```

### 详细说明

```
字段信息（用户）读取接口参数param说明：
{
"dt":"customer",////数据表的分类，customer代表客户表 作用不大
"act":"pr2nm",// 动作分类: pr2nm代表 用户信息读取, 下面的part,nam参数不提供返回全部人员信息
"part":"B1",// 用户part,通过 part获取用户姓名，可选
"name":"陈默",// 用户name,通过姓名获取part，可选
}

假定参数对应数值如下：
param:{"act":"pr2nm","dt":"customer","part":"B1","name":"陈默"}
stamp:1764213019
upr:{"sid":"51496b945bd1efb61e6cacf0bed58f20"}
cmd:api.fieldinfo
appkey:open1slslslsdldlsdlds
计算前字符串:
{"act":"pr2nm","dt":"customer","part":"B1","name":"陈默"}1764213019{"sid":"51496b945bd1efb61e6cacf0bed58f20"}api.fieldinfoopen1slslslsdldlsdlds
md计算结果:
c353587e7c8ef5e967b9e64c0a061c58
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 动作操作状态，1：操作成功，0：操作失败
        msg:’成功！’,//文字说明字符串，操作成功提示，或者失败原因
        data://用户信息
        [
            {
                part:"B1",
                name:"张三"
            },
            {
                part:"B2",
                name:"李四"
            },
            ...
        ]
        }
}
                            
```

## 63. 领料单预生成接口

- 模块：售后与其他 · cmd：`api.cmdact` · dt：`mes_process` · act：`preview`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 领料单预生成参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{"dt":"mes_process","data":{"work_order_id":6,"goods_id":2,"process_no":"Test001","need_number":5,"act":"preview"}}
```

### 详细说明

```
param参数说明：
{
"dt":"mes_process", //数据的分类，mes_process代表工序管理信息
"data": //操作动作JSON对象
{
"work_order_id":6, //mes工单id
"goods_id":2, //crm订单明细id
"process_no":"Test001", //工序编号
"need_number":5, //领料数量
"act":"preview" //动作分类，preview表示　领料单预生成准备数据的动作，该参数是本接口的唯一标示
}
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"mes_process","data":{"work_order_id":6,"goods_id":2,"process_no":"Test001","need_number":5,"act":"preview"}}
stamp:1669778079
upr:{"sid":"c5b32349832991ea423653c309a41ce1"}
cmd:api.cmdact
appkey:xtools01f02875167924284317d
计算前字符串:{"dt":"mes_process","data":{"work_order_id":6,"goods_id":2,"process_no":"Test001","need_number":5,"act":"preview"}}1669778079{"sid":"c5b32349832991ea423653c309a41ce1"}api.cmdactxtools01f02875167924284317d
md计算结果:c4aafacafc0814a0b24db23f55360439

领料数据信息结果说明：
{
"id":"1", //工序ID
"name":"Test001", //工序名称
"process_no":"Test001", ////工序编号
"flow_id":"1", //所属工艺
"flow_name":"Test", //所属工艺名称
	"yield_rate":"95%", //达标良品率
"content":"", //工序说明
"memo":"", //质检要求
"sort_id":"1", //工序顺序
"lib":"3", //领料仓库ID
	"libname":"上海仓库", //领料仓库名称
    "who":"B1",//领料仓库库管Part，如果是多个库管，选第一个;  对应出库单的经手人字段who
	"info":[ //客制化信息列表
["身高", "168cm"], //第一条客制信息，标题，内容
 ["重量", "90KG"] //第二条客制信息，标题，内容
 ],
"prods": //领料产品明细
[
{
"pid":97, //产品ID
"pro_name":"摄像头-400万半球网络", //产品名称
"model":"DS-2CD2F45F(D)-I(W)(S)", //产品型号
"spec":"-", //产品 SKU、规格
"sn":"", //产品编码
"m_num":"1", //母料基数
"num":"1", //子料基数
"need_num":5, //领料数量
"memo":"" //说明
}
]
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 返回状态，　　1：成功，0：失败
        msg:"领料单预生成准备数据成功"　　//返回领料单预生成准备数据结果的描述
        data:{ //领料数据信息
            {"lib":"3","libname":"上海仓库","id":"1","name":"Test001","process_no":"Test001","flow_id":"1","yield_rate":"","content":"","memo":"","sort_id":"1","info":[],"flow_name":"Test","prods":[{"pid":"103","pro_name":"电源","model":"","spec":"-","sn":"","m_num":"1","num":"2","need_num":10,"memo":""}]}
            
            }
        }
}
                            
```

## 64. 生产工艺工序

- 模块：售后与其他 · cmd：`api.output` · dt：`mes_flow`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 工艺读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{  	"dt":"mes_flow",//读取数据的分类，	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
参数说明：
{ "dt":"mes_flow",//读取数据的分类
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  0//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
“flow_no”:''//工艺编号
}

md参数计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"mes_flow"}
stamp:1668998593
upr:{"sid":"a0c26f8615f1d6a573d65ba0e5b9a774"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"contract0"}1668998593{"sid":"a0c26f8615f1d6a573d65ba0e5b9a774"}api.outputopen1slslslsdldlsdlds
md计算结果:9dbbaf615687c75ad21d5875ff20330f

字段说明：
{
		'id' = 2  //工艺id
       'name' = '维C面包' //工艺名称
       'flow_no' ='8989' //工艺编号
       'version' = '1.0' //版本
       'yield_rate' = '97' //达标良品率
       'status' = '2' //状态：0-编辑中；2-已启用；3-停用
       'sdate' = '2022-12-19' //启用日期
       'edate' = '2022-12-19' //停用日期
       'memo' ='' //备注
       'who' => 'B1'//执行人
       'log' => '2022-12-19 11:29:20 刘琪峰 启用
2022-12-19 11:29:13 刘琪峰 可再编辑
2022-12-19 11:29:11 刘琪峰 停用
2022-12-19 11:27:52 刘琪峰 启用
2022-12-19 11:27:39 刘琪峰 可再编辑
2022-12-19 11:27:36 刘琪峰 停用
2022-12-19 11:15:12 刘琪峰 启用
2022-12-19 11:13:55 刘琪峰 创建
'  //执行日志
       'creatdate' =  '2022-12-19' //数据创建日期
       'moddate' = '2022-12-19' //数据修改日期
       'mes_process' = //工艺下工序数组
        {
         0 =>
           'id' => 1 //工序id
           'name' = '和面' //工序名称
           'process_no' = '112' //工序编号
           'yield_rate' = '90' //达标良品率
           'content' = '' //工序说明
           'memo' = '' //备注
           'sort_id' = '1' //工序顺序
           'info' ='[]' //客制化信息
           'creatdate' = '2022-12-19'  //数据创建日期
           'moddate' ='2022-12-19' //数据修改日期
         1 =>
          array (size=10)
           'id' => string '2' (length=1)
           'name' => string '发酵' (length=6)
           'process_no' => string '113' (length=3)
           'yield_rate' => string '95' (length=2)
           'content' => string '' (length=0)
           'memo' => string '' (length=0)
           'sort_id' => string '2' (length=1)
           'info' => string '[]' (length=2)
           'creatdate' => string '2022-12-19' (length=10)
           'moddate' => string '2022-12-19' (length=10)
	}
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 合同读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条订单数据
            [工艺1},{工艺2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 65. 获客线索读取接口

- 模块：客户与联系人 · cmd：`api.output` · dt：`jk_collect`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1676277157 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"f9c39ca0aaef1614c33274a3075db1de"} |
| param | json | 是 | 读取参数信息 | {"dt":"jk_collect","id":973} |
| md | string | 是 | 参数合法性校验码 | 932c91b645fdf6c3fe2b46cca97553b0 |

### 详细说明

```
参数说明：
{ "dt":"jk_collect",//读取数据的分类，contract0代表合同信息
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  973//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

md参数计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
假定参数对应数值如下：
param:{"dt":"jk_collect","id":973}
stamp:1676277157
upr:{"sid":"f9c39ca0aaef1614c33274a3075db1de"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"jk_collect","id":973}1676277157{"sid":"f9c39ca0aaef1614c33274a3075db1de"}api.outputopen1slslslsdldlsdlds
md计算结果:932c91b645fdf6c3fe2b46cca97553b0

字段说明：
{
"id":"973",//获客线索 ID
"form_id":"0",//表单 ID
"page_id":"0",//页面 ID
"content":"{\"key\":[\"姓名\",\"电话\",\"年龄\",\"您的公司\",\"广告计划ID\",\"广告计划名称\",\"推广链接\",\"最新修改时间\",\"创建时间\"],\"val\":[\"杨紫\",\"15261366585\",\"0\",\"装裱\",\"1732702771256323\",\"2022-05-13拒绝孤立系统，全业务一体化\",\"https:\\\/\\\/www.chengzijianzhan.com\\\/tetris\\\/page\\\/7097138386397921316\\\/\",\"2022-05-14 23:22:47\",\"2022-05-14 23:22:47\"]}",//采集内容
"status":"0",//状态： 0:未处理;1:已处理
"source":"5",//分类： 0:集客;1:销帮;2:网客;3:录入;4:导入;5:外部抓取
"come_from":"头条广告", //来源
"con_name":"杨紫", //联系人
"con_type":"15261366585", //联系方式
"com_name":"公司", //公司信息
"opport":"需求", //需求信息
"memo":"备注", //备注信息
"cu_id":"0", //客户ID
"cost":"50.00", //成本
"owner":"B100", //所有者 part
"cu_sn":"", //客户编码
"mark_subject":"中秋活动",//关联市场活动 标题
"mark_id":14,//关联市场活动 ID
"creatstm":"2022-09-14 09:29:10", // 提交时间，创建时间
"log":"加待办 ", //日志
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 获客线索读取状态，1：读取成功，0：读取失败
        data://返回读取数据的数组，如：多条获客线索数据
            [获客线索1},{获客线索2}]
        （注意：返回结果集最多100条，如果超过，可多次读取）
        }
}
                            
```

## 66. 获客线索写入接口

- 模块：客户与联系人 · cmd：`api.input` · dt：`jk_collect`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1676270180 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"a23d8cb2eb04680a87cfb792edd3f0bd"} |
| param | json | 是 | 写入参数信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 314398eb38ebb06db705b5de5cdff91b |

param 示例：

```
{"dt":"jk_collect","data":{"come_from":"来自电话回访","com_name":"宏大装修公司","con_name":"张总1","con_type":"19973607343","cost":"274","opport":"客户需求：120平米精装修","memo":"欧式风格","owner":"B100"}}
```

### 详细说明

```
接口说明：
本接口只接受参数data下所提供的字段内容，超出的字段无法保存。保存结果固定字段有 分类为：导入，状态为：未处理,
在接口调用时，所有者原则上无法更改；本功能通过添加数据后，自动追加转移功能实现所有者导入。

参数param的说明：
{
"dt":"jk_collect", //数据分类， jk_collect 代表获客线索
"data": //保存信息，json 对象
{
"come_from":"来自电话回访", //数据来源
"com_name":"宏大装修公司", //公司
"con_name":"张总", //联系人
"con_type":"19973607343", //联系方式
"cost":"274", //成本
"opport":"客户需求：120平米精装修", //需求
"memo":"欧式风格", //备注信息
"owner":"B100", //所有者，用part 或者 所有者姓名
"mark_id":14 //关联市场活动 ID
}
}
md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值
计算用例如下：
param:{"dt":"jk_collect","data":{"come_from":"来自电话回访","com_name":"宏大装修公司","con_name":"张总1","con_type":"19973607343","cost":"274","opport":"客户需求：120平米精装修","memo":"欧式风格","owner":"B100"}}
stamp:1676270180
upr:{"sid":"a23d8cb2eb04680a87cfb792edd3f0bd"}
cmd:api.input
appkey:xtools01f02875167924284317d
计算前字符串:{"dt":"jk_collect","data":{"come_from":"来自电话回访","com_name":"宏大装修公司","con_name":"张总1","con_type":"19973607343","cost":"274","opport":"客户需求：120平米精装修","memo":"欧式风格","owner":"B100"}}1676270180{"sid":"a23d8cb2eb04680a87cfb792edd3f0bd"}api.inputxtools01f02875167924284317d
md计算结果:314398eb38ebb06db705b5de5cdff91b
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 写入状态，1：写入成功，0：写入失败
        msg:’获客线索添加成功！’,//文字说明字符串，写入成功提示，或者失败原因
        id:898 //写入成功后，写入数据的获客线索ID
        }
}
                            
```

## 67. 开票申请的开票动作接口

- 模块：财务 · cmd：`api.cmdact` · dt：`bill_apply` · act：`kaipiao`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.cmdact |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528102067 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | {"sid":"61c0028e6b7dbe7f63df43340ce494a3"} |
| param | json | 是 | 外部库存变更参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | ced67ca166b6a27897ff868ff45bbb9f |

param 示例：

```
{"dt":"bill_apply","data":{"id":3,"billsn":"WB0001","act":"kaipiao"}}
```

### 详细说明

```
param参数说明：
{
"dt":"bill_apply", //数据的分类，bill_apply代表开票申请信息
"data": //操作动作JSON对象
{
"id":197, //开票申请的ID
"billsn":"M2840034", //开票票号
"act":"kaipiao" //动作分类，kaipiao表示　开票的动作，该参数是本接口的唯一区分
}
}

参数md计算方法为：param字符串+时间戳+upr字符串+cmd字符串+appkey字符串的结果的md5值

假定参数对应数值如下：
param:{"dt":"bill_apply","data":{"id":197,"billsn":"M2840034","act":"kaipiao"}}
stamp:1703471075
upr:{"sid":"7af1d4e130a9df0da931d8fd534be89b"}
cmd:api.cmdact
appkey:xtools01f02875167924284317d
计算前字符串:{"dt":"bill_apply","data":{"id":197,"billsn":"M2840034","act":"kaipiao"}}1703471075{"sid":"7af1d4e130a9df0da931d8fd534be89b"}api.cmdactxtools01f02875167924284317d

md计算结果:c6ca7df0ed77222b4ccb27b1f18ae8c5
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 返回状态，　　1：修改成功，0：修改失败
        msg:"开票成功"　　  //返回开票结果的描述
        }
}
                            
```

## 68. 发货单修改接口

- 模块：订单与发货 · cmd：`api.update` · dt：`sendgoods`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.update |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1528078285 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"f6a55a89a2b4ff13be9cd6c147bca9e8",//登录接口返回的sid } |
| param | json | 是 | 发货单的修改信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 6913de14caa74767e360ce918497e085 |

param 示例：

```
{"dt":"sendgoods","extend":1,"data":{"sntype":1,"num":2,"package_type":2,"weight":3,"volume":4,"cost":45,"costtype":2,"sendcomp":"韵达","sendcode":"dsdldl123","name":"张三","date":"2025-12-04","memo":"备注甩啦甩啦","id":2130,"one_select":2,"deli_note":[{"prod":"20241129001","deli_sum":2,"plan":"备注11","price":300,"sum":700,"un_price_tax":300},{"prod":"SN19873","deli_sum":2,"plan":"备注22","price":200,"sum":600,"un_price_tax":200}]}}
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"sendgoods","extend":1,"data":{"sntype":1,"num":2,"package_type":2,"weight":3,"volume":4,"cost":45,"costtype":2,"sendcomp":"韵达","sendcode":"dsdldl123","name":"张三","date":"2024-12-04","memo":"备注甩啦甩啦","id":2130,"one_select":2,"deli_note":[{"prod":"20241129001","deli_sum":2,"plan":"备注11"},{"prod":"SN19873","deli_sum":2,"plan":"备注22"}]}}
stamp:1716345028
upr:{"sid":"93b23f08fe4a69078723da86f1f5dd3e"}
cmd:api.update
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"sendgoods","extend":1,"data":{"sntype":1,"num":2,"package_type":2,"weight":3,"volume":4,"cost":45,"costtype":2,"sendcomp":"韵达","sendcode":"dsdldl123","name":"张三","memo":"备注甩啦甩啦","id":2130,"one_select":2,"deli_note":[{"prod":"20241129001","deli_sum":2,"plan":"备注11"},{"prod":"SN19873","deli_sum":2,"plan":"备注22"}]}}1733132528{"sid":"82b819793afc02030ee1f21895fe072e"}api.updateopen1slslslsdldlsdlds
md计算结果:7bf31787850a46e67bc319df60c018a7

参数说明：
{"dt":"sendgoods", //业务数据表区分，发货单
"extend"=>1,
"data":
{
'id':319, //发货单ID            修改数据的检索条件
'sn':'FHD0001', //发货单号  和id 提供一个即可
'sntype':2, //发货方式        根据数据字典设置，请输入数字内容，如 1:邮局;2:中通快递;3:航空;4:其他
'num':3, //打包件数           输入内容
'package_type':2, //包裹类型  根据数据字典设置，请输入数字内容，如 1:衣物;2:易碎品;3:食品;4:易漏品
'weight':2.3, //重量(Kg)        输入内容
'volume':0.23, //体积(m³)        输入内容
'cost':4.5, // 运费           输入内容
'costtype':1, //运费结算      根据数据字典设置，请输入数字内容，如 1:现付;2:到付;3:月结
'sendcomp':'韵达', // 物流公司     文本输入内容
'sendcode':'yd00023', // 物流单号     文本输入内容
'name':'张三', // 收货人姓名        文本输入内容
'addr':'北京市朝阳区', // 收货人地址        文本输入内容
'pst':'100001', // 收货人邮编        文本输入内容
'tel':'01087833***', // 收货人电话         文本输入内容
'mphone':'189107858***', // 收货人手机      文本输入内容
'insured':100, // 保价金额      输入内容
'date':'2025-12-04', // 发货日期      日期输入内容
'memo':'备注内容', //备注            文本输入内容
'one_select':2,//分类2
'deli_note':[
{
'prod':'20241129001',//产品编号
'deli_sum' :2,//交付数量（如果数量超过订单产品数量，按订单产品数量交付）
'plan': '备注',//备注
},
{
'prod':'20241129002',//产品编号
'deli_sum':2,//交付数量
'plan' : '备注',//备注
}
]
}
}
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 修改状态，1：修改成功，0：修改失败
        msg:"发货单修改成功！"//文字说明字符串，写入成功提示，或者失败原因
        }
}
                            
```

## 69. 下游询价记录写入接口

- 模块：客户与联系人 · cmd：`api.input` · dt：`ask_price_note`
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.input |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549951800 |
| upr | json | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"5fd9f194d62533227df465568a024a3d",//登录接口返回的sid } |
| param | json | 是 | 写入下游询价记录信息 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | f106479a228a964469458bc2b2db8300 |

param 示例：

```
{"dt":"ask_price_note","data":{"cu_sn":43784,"content":"询价内容","status":1,"date":"2024-06-04","subject":"标题内容","memo":"测试备注"}}
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"ask_price_note","data":{"cu_sn":43784,"content":"询价内容","status":1,"date":"2024-06-04","subject":"标题内容","memo":"测试备注","ask_price_note_item":[{"content":"test1 10","num":11},{"content":"test2 110","num":121}]}}
stamp:1717491112
upr:{"sid":"d002ba5f51f2d08048e6e95b2893a8e2"}
cmd:api.input
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"ask_price_note","data":{"cu_sn":43784,"content":"询价内容","status":1,"date":"2024-06-04","subject":"标题内容","memo":"测试备注","ask_price_note_item":[{"content":"test1 10","num":11},{"content":"test2 110","num":121}]}}1717491112{"sid":"d002ba5f51f2d08048e6e95b2893a8e2"}api.inputopen1slslslsdldlsdlds
md计算结果:d73b23db472ea298edf75bbd7e4dc64d

下游询价单写入参数说明：
{
"dt":"ask_price_note",//数据表 下游询价单
       "data":{//数据写入内容
 			"cu_sn":0, //字符串为客户编号，如果是数字为客户id, 指定使用客制化别名的客户
  "content":"询价内容",//询价内容
			"status":1,//状态 0:未提交;1:已提交;2:中心已确认
			"date":"2024-06-05",//日期
			"who":5,//询价人  客户的联系人ID
			"subject":"主题信息",//主题
			"memo":"备注信息", //备注
 		}//数据
};
```

### 返回示例

```
                                {
    ok:1,//接口调用状态标志， 1:接口调用正常，  0:接口调用异常
    ret: {
        ok:1,// 写入状态，1：写入成功，0：写入失败
        msg:’下游询价记录添加成功！’//文字说明字符串，写入成功提示，或者失败原因
        id:40614  //添加数据ID
        }
}
                            
```

## 70. 采购退货单读取接口

- 模块：财务 · cmd：`api.output` · dt：`purreturn` · 本版新增
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | string | 是 | 采购退货单的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{  	"dt":"purreturn",//读取数据的分类，purreturn代表采购退货单  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"purreturn","id":152}
stamp:1781593670
upr:{"sid":"ef177eb99ac8b0d2c11783b82e6255c7"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"purreturn","id":152}1781593670{"sid":"ef177eb99ac8b0d2c11783b82e6255c7"}api.outputopen1slslslsdldlsdlds
md计算结果:6407574abce5dc67958cbceb4b50de2c

param参数说明：
{
"dt":"purreturn",//读取数据的分类，purreturn代表采购退货单
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

返回字段说明：
{
        "id": "152", //采购退货ID
        "subject": "自动主题-采购单号:CGD20251106059-序列号001等1种产品-退货", //采购退货单标题
        "cu_sn": "11111", //客户编号
        "pu_id": "2095", //对应采购单ID
        "status": "2", //状态 0:待处理|dcl;2:执行中|zxz;3:结束|over;4:终止
        "ra_who": null, //退货审批人
        "ra_date": "", //退货审批日期
        "lib": "1", //退货仓库
        "memo": "", //备注
        "date": "2025-11-06", //退货日期
        "who": "B1", //经办人
       "who_name": "陈默", //经办人姓名
        "return_no": "", //退货单编号
        "st_libout": "3", //出库状态 0:待出库;1:生成出库单;2:部分出库;3:全部出库;4:退货完成(无出库)
        "st_hk": "0", //退款状态 0:未退款;1:部分退款;2:全部退款
        "hk_sum": "0.00", //已回款金额
        "money": "13.80", //应退货金额
        "money_type": "RMB", //币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
        "money_rate": "100", //汇率，可不传递，缺省 100
        "one_select": "0", //分类
        "org_id": "0", //组织ID
        "purrtnitem": [
          {
            "id": "319", //退货项ID
            "pid": "15491", //产品ID,对应 外部的产品编号
            "rnum": "1.000", //退货数量
            "rprice": "13.8000", //单价
            "rsum": "13.80", //退货金额
            "nout": "1.000", //已出库数量
            "reason": "", //退货原因
            "memo": "" //产品明细备注
          }
        ]
      }
```

### 返回示例

```
                                {
    "ok": 1,
    "ret": {
        "ok": 1,
        "data": [
            {采购退货单1},{采购退货单2},
    ...
    最多100条
        ]
    }
}
                            
```

## 71. 订单退货单读取接口

- 模块：订单与发货 · cmd：`api.output` · dt：`libreturn` · 本版新增
- 请求方式：POST · 请求地址：https://crm.xtcrm.com/open/index.xt（原文部分接口写为 http）

### 请求参数

| 参数 | 类型 | 必需 | 描述 | 示例 |
|---|---|---|---|---|
| cmd | string | 是 | 接口名称分类 | api.output |
| appid | string | 是 | 开发公司的应用ID,由XTools公司提供 | open00001_sajdjsjsj |
| stamp | string | 是 | 接口调用的当前时间戳 | 1549954821 |
| upr | string | 是 | 用户的登录信息。在上次登录接口返回中，有sid， 在登录成功后，返回的sid放入到upr即可登录。提高服务器性能。 | { "sid":"96c584001f27e93c443e8eb0ee77e9b4",//登录接口返回的sid } |
| param | string | 是 | 订单退货的读取参数 | 见下方示例 |
| md | string | 是 | 参数合法性校验码 | 79bdc07d245290beea7da0c9ec0fbb58 |

param 示例：

```
{  	"dt":"libreturn",//读取数据的分类，libreturn代表订单退货  	"lastid":0,//指定上次下载的最后一个ID,和参数id二选一  	"id":    10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用  }
```

### 详细说明

```
假定参数对应数值如下：
param:{"dt":"libreturn"}
stamp:1781590357
upr:{"sid":"2784e788c0972414ac9d8115e6ff3edf"}
cmd:api.output
appkey:open1slslslsdldlsdlds
计算前字符串:{"dt":"libreturn"}1781590357{"sid":"2784e788c0972414ac9d8115e6ff3edf"}api.outputopen1slslslsdldlsdlds
md计算结果:250e4f0d49cf7b342eb2faafe8a7f651

参数说明：
{
 "dt":"libreturn",//读取数据的分类，libreturn代表订单退货
"lastid":0,//指定上次下载的最后一个ID,和参数id二选一
"id":  10//指定下载的一条数据的ID号,有这个参数，lastid就不起作用
}

返回数据说明：
{
  "id": "196",        // 订单退货单ID
  "subject": "wtest1112th", // 退货标题
  "cu_sn": "[id:17209]",   // 客户编号，如果没客户编号，返回客户ID
  "co_id": "6776",      // 订单ID
  "status": "2",       // 退货单状态 0:待处理|dcl;2:执行中|zxz;3:结束|over;4:终止
  "ra_who": "",       // 退货审批人
  "ra_date": "",       // 退货审批日期
  "lib": "1",        // 退货仓库
  "memo": "",        // 备注
  "date": "2020-12-01",   // 退货日期
  "who": "B100",       // 经办人
  "who_name": "陈默", //经办人姓名
  "return_no": "",      // 退货单编号
  "st_libin": "3",      // 入库状态 0:待入库;1:生成入库单;2:部分入库;3:全部入库;4:退货完成(无入库)
  "st_hk": "0",       // 回款状态 0:未退款;1:部分退款;2:全部退款
  "hk_sum": "0.00",     // 已回款金额
  "money": "50.00",     // 应退货金额
  "money_type": "RMB",    // 币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
  "money_rate": "100",    // 汇率，可不传递，缺省 100
  "one_select": "0",     // 分类
  "sendcode": "",      // 物流单号
  "org_id": "0",       // 组织ID
  "rtnitem": [
    {
      "id": "324",    // 退货项ID
      "pid": "10912",  // 产品ID,对应 外部的产品编号
      "rnum": "1.000",  // 退货数量
      "rprice": "57.5000",// 单价
      "rsum": "57.50",  // 退货金额
      "nin": "1.000",  // 入库数量
      "reason": "",   // 退货原因
      "memo": ""     // 产品明细备注
    }
  ]
}
```

### 返回示例

```
                                {
    "ok": 1,
    "ret": {
        "ok": 1,
        "data": [
            {
    "id": "196",               // 订单退货单ID
    "subject": "wtest1112th",  // 退货标题
    "cu_sn": "[id:17209]",     // 客户编号，如果没客户编号，返回客户ID
    "co_id": "6776",           // 订单ID
    "status": "2",             // 退货单状态 0:待处理|dcl;2:执行中|zxz;3:结束|over;4:终止
    "ra_who": "",              // 退货审批人
    "ra_date": "",             // 退货审批日期
    "lib": "1",                // 退货仓库
    "memo": "",                // 备注
    "date": "2020-12-01",      // 退货日期
    "who": "B100",             // 经办人
    "return_no": "",           // 退货单编号
    "st_libin": "3",           // 入库状态 0:待入库;1:生成入库单;2:部分入库;3:全部入库;4:退货完成(无入库)
    "st_hk": "0",              // 回款状态 0:未退款;1:部分退款;2:全部退款
    "hk_sum": "0.00",          // 已回款金额
    "money": "50.00",          // 应退货金额
    "money_type": "RMB",       // 币种 可不传递，缺省 RMB, 请参考多币种设置里面的币种，如: JPY CAD RMB EUR USD
    "money_rate": "100",       // 汇率，可不传递，缺省 100
    "one_select": "0",         // 分类
    "sendcode": "",            // 物流单号
    "org_id": "0",             // 组织ID
    "rtnitem": [
        {
            "id": "324",       // 退货项ID
            "pid": "10912",    // 产品ID,对应 外部的产品编号
            "rnum": "1.000",   // 退货数量
            "rprice": "57.5000",// 单价
            "rsum": "57.50",   // 退货金额
            "nin": "1.000",    // 入库数量
            "reason": "",      // 退货原因
            "memo": ""         // 产品明细备注
        }
    ]
}
    ...
    最多100条
        ]
    }
}
                            
```
