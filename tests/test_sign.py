"""离线签名测试：全部用例取自《XToolsCRM OPEN API》文档中给出的“计算前字符串 / md 计算结果”。

运行：python -m pytest tests -q
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xtools import XToolsClient, XToolsConfig, compact_json  # noqa: E402

APPKEY = "open1slslslsdldlsdlds"
APPKEY2 = "xtools01f02875167924284317d"

CASES = [
    # (说明, param, stamp, upr, cmd, appkey, 期望 md)
    ("登录", "[]", "1527746854",
     '{"comkeyid":"xtoolsplusd002","com":"d002","part":"","md":"d79d4e33a7771d8f0473f1bc0bd12f8e"}',
     "user.login", APPKEY, "d9a145ef66734897f0f38dd42a471873"),
    ("用户读取", '{"dt":"user","lastid":0}', "1552028002", '{"sid":"b56561c28a6bec6257e5a5916000837e"}',
     "api.output", APPKEY, "8a4c78a92d67f09a0eaee3334aa8feb6"),
    ("客户读取", '{"dt":"customer","id":10}', "1549876028", '{"sid":"4abda94f27512666f079e288ab44a287"}',
     "api.output", APPKEY, "79bdc07d245290beea7da0c9ec0fbb58"),
    ("客户扩展读取", '{"dt":"customerext","id":10}', "1549936788", '{"sid":"6a44d9130891288eae6bdd5ecd975d59"}',
     "api.output", APPKEY, "b914bb54ea40aa9e27bfc696410402d4"),
    ("企业客户写入（含中文）",
     '{"dt":"customer","data":{"id":0,"cu_name":"中国海上救援大队","sn":"0067","address":"中国上海","cu_remark":"这是一段客户备注：这个客户情况不错，不知道是否支持换行？如果不支持，需要在参数说明中写清楚","cu_from":"1","contact":[{"id":0,"name":"刘大庆","mphone":"15891023600","qq":"999999991000234","weixin":"wx_91884dx","email":"wq@sohu.com"},{"id":0,"name":"留明海","mphone":"15920066999 ","qq":" ","weixin":" ","email":" "}]}}',
     "1528078285", '{"sid":"f6a55a89a2b4ff13be9cd6c147bca9e8"}', "api.input", APPKEY, "6913de14caa74767e360ce918497e085"),
    ("客户扩展字段写入", '{"dt":"customerext","data":{"sn":"00003","ext_item5":"测试","ext_item7":"12345"}}', "1549937464",
     '{"sid":"1f92796c29c7346c832947414ffa1216"}', "api.input", APPKEY, "9d7041b7b4ea935cdc9d04032fcf43f4"),
    ("行动记录写入", '{"dt":"action","data":{"id":0,"cale":"3","subject":"测试标题","content":"行动历史记录的内容描述","cu_sn":"00003","date":"2019-01-31"}}',
     "1549951800", '{"sid":"5fd9f194d62533227df465568a024a3d"}', "api.input", APPKEY, "f106479a228a964469458bc2b2db8300"),
    ("行动记录读取", '{"dt":"action","lastid":10}', "1549954821", '{"sid":"96c584001f27e93c443e8eb0ee77e9b4"}',
     "api.output", APPKEY, "14772c52c44faeaf973c0778f66c4fc8"),
    ("计划回款修改", '{"dt":"gathering","data":{"id":553,"date":"2019-12-27","serial":"1","money":"1195.74","status":"2","who":"B1","principal":"","co_sn":"DD2016080124","prj_id":"0","memo":"备注信息"}}',
     "1577436357", '{"sid":"19b41e79e92ce567852832a943df2e8b"}', "api.update", APPKEY, "b276c0e35aa0af1a9a09487b8ba4dad2"),
    ("回款记录写入", '{"dt":"gathering_note","data":{"cu_sn":"5642324","co_id":"74","date":"2021-08-12","invoice":"1","serial":2,"money":"100","type":1,"ctype":2,"who":"M1"}}',
     "1628737838", '{"sid":"729d74edf717c634aeb611c0bb927ca3"}', "api.input", APPKEY, "44c5577e091e82c3853bb95b88f85cd0"),
    ("开票记录写入", '{"dt":"bill","data":{"id":0,"cu_sn":"11111","billsn":"fp444","date":"2024-11-20","money":444,"type":5,"who":"M2","money_type":"RMB","money_rate":444,"content":"内容444","serial":2}}',
     "1732168886", '{"sid":"aa9dd4bda646ea60c48518688320574b"}', "api.input", APPKEY, "0d2a57b0f17d8d66885278f7cb219bad"),
    ("入库单写入", '{"dt":"libin","data":{"title":"open api 入库单导入","lib":1,"date":"2021-08-12","memo":"入库单备注","who":"M1","libitem":[{"prod":"35650","num":2,"memo":"明细备注1"},{"prod":"TS0034","num":2,"memo":"明细备注2"}]}}',
     "1628757241", '{"sid":"00927ebe4bc2e3fe0a8be8ba18560b74"}', "api.input", APPKEY, "69be2d1efb953eabd93db80560eac9ec"),
    ("入库单完成", '{"dt":"libin","data":{"id":662,"act":"libinok"}}', "1628761827", '{"sid":"66041e26cad74e4e5538030180f2cb13"}',
     "api.cmdact", APPKEY, "f383920e9dfaa1e807a32d91c6f447f9"),
    ("出库单完成", '{"dt":"libout","data":{"id":12572,"act":"liboutok"}}', "1628844430", '{"sid":"ca6f87bb527874746d10c85efee050d5"}',
     "api.cmdact", APPKEY, "4a3dd4b3194fc8bf8dd69066d3357cde"),
    ("产品读取", '{"dt":"product","lasttime":"2022-01-01"}', "1663556498", '{"sid":"43f5d5137aeb8aed6d65b8de16efa864"}',
     "api.output", APPKEY, "07fd75ecd1a42ded85d6fd7385c83612"),
    ("产品写入（另一 appkey）", '{"dt":"product","data":{"name":"tesla","model":"model 3","sku":"black","sn":"8468326748327648","price":170000}}',
     "1694424858", '{"sid":"8391e85898850b524391113582556a48"}', "api.input", APPKEY2, "e361ac47d93e0d6d322861013d959208"),
    ("产品修改", '{"dt":"product","data":{"sku":"yellow","id":40614}}', "1694482339", '{"sid":"79f8d674d8693b3da754275bfe82aaa1"}',
     "api.update", APPKEY2, "818c19b69005d0f7b189a1c59c2cad44"),
    ("价格策略变更", '{"dt":"product","data":{"id":15198,"act":"chg_str_ps","data":{"4":"ceshi1","5":"ceshi2"}}}', "1723446782",
     '{"sid":"92140f318b6227fcba9e470271a31511"}', "api.cmdact", APPKEY, "c25272aa7016d0c4f36aeb5c01578825"),
    ("产品分类写入", '{"dt":"csstree","data":{"id":0,"tid":1,"upid":11,"title":"测试分类"}}', "1723711883",
     '{"sid":"58876e089c14f2fc7964db1915d7d972"}', "api.input", APPKEY, "b9655d6347a0a9075c011c1eef580282"),
    ("收发货通知单读取", '{"dt":"sr_notice","id":10,"lastid":10,"lasttime":"2022-09-08","type":1,"status":1}', "1663225528",
     '{"sid":"4aeae120971438153c40397a2d829f11"}', "api.output", APPKEY, "bec43ba2510e8047449ec99bf0cd15d1"),
    ("收发货通知单状态变更", '{"dt":"sr_notice","data":{"id":1,"erp_no":"N000001","status":2,"act":"chgst"}}', "1663307556",
     '{"sid":"384d2aa96534a8a5300054c854070b33"}', "api.cmdact", APPKEY, "96f2e92a89075c683ccac0536e279d54"),
    ("收发货通知单执行", '{"dt":"sr_notice","data":{"id":13,"who":"李能","date":"2022-09-13","sendcode":"98837737101","child":[{"prod":"WB0001","num":2,"costprice":100,"memo":"执行日志"}],"act":"exc"}}',
     "1663313492", '{"sid":"b66e305585dc4f9a5ef667782549c508"}', "api.cmdact", APPKEY, "3aa53eb432b8864ee05018855c4feb1f"),
    ("外部库存变更", '{"dt":"libn","data":{"lib":3,"prod":"WB0001","num":8,"memo":"测试外部库存","act":"erp_libn"}}', "1663554294",
     '{"sid":"7a30269bb89c68607884b04fa3aa0a4f"}', "api.cmdact", APPKEY, "a14823f751e2143ee77ba5f871ca853a"),
    ("数据字典", '{"dt":"customer","field":"cu_status"}', "1655972843", '{"sid":"fc7c5ee14bcab84057f291e243b668dd"}',
     "api.fieldinfo", APPKEY, "8b673832d84b1ab034b9668fc806a43a"),
    ("字段名称", '{"dt":"customer","act":"dbcn"}', "1754462878", '{"sid":"7bad012c6155df5197b7f602b3d1dc8a"}',
     "api.fieldinfo", APPKEY, "1aef172553cc66aae8075bf641b73235"),
    ("用户对照", '{"act":"pr2nm","dt":"customer","part":"B1","name":"陈默"}', "1764213019", '{"sid":"51496b945bd1efb61e6cacf0bed58f20"}',
     "api.fieldinfo", APPKEY, "c353587e7c8ef5e967b9e64c0a061c58"),
    ("附件读取", '{"dt":"costdetail","id":"285"}', "1581315848", '{"sid":"476562f58e591ae7d6afabe2987f3a10"}',
     "api.downfile", APPKEY, "a9ca053b884df6c2b38577780a74f916"),
    ("开票动作", '{"dt":"bill_apply","data":{"id":197,"billsn":"M2840034","act":"kaipiao"}}', "1703471075",
     '{"sid":"7af1d4e130a9df0da931d8fd534be89b"}', "api.cmdact", APPKEY2, "c6ca7df0ed77222b4ccb27b1f18ae8c5"),
    ("获客线索写入", '{"dt":"jk_collect","data":{"come_from":"来自电话回访","com_name":"宏大装修公司","con_name":"张总1","con_type":"19973607343","cost":"274","opport":"客户需求：120平米精装修","memo":"欧式风格","owner":"B100"}}',
     "1676270180", '{"sid":"a23d8cb2eb04680a87cfb792edd3f0bd"}', "api.input", APPKEY2, "314398eb38ebb06db705b5de5cdff91b"),
]


@pytest.mark.parametrize("title,param,stamp,upr,cmd,appkey,expected", CASES, ids=[c[0] for c in CASES])
def test_sign_matches_document(title, param, stamp, upr, cmd, appkey, expected):
    assert XToolsClient.sign(param, stamp, upr, cmd, appkey) == expected


def test_login_code_matches_document():
    # 文档：time 1527746854，comkey xtoolsplusd002sjsjsj，com d002，part 空
    assert XToolsClient.login_code("1527746854", "xtoolsplusd002sjsjsj", "d002", "") == "d79d4e33a7771d8f0473f1bc0bd12f8e"


def test_compact_json_keeps_chinese_and_no_spaces():
    obj = {"dt": "customer", "data": {"cu_name": "中国海上救援大队", "contact": [{"id": 0, "name": "刘大庆"}]}}
    text = compact_json(obj)
    assert text == '{"dt":"customer","data":{"cu_name":"中国海上救援大队","contact":[{"id":0,"name":"刘大庆"}]}}'


def test_build_request_reproduces_document_login_example(tmp_path):
    config = XToolsConfig(
        appid="open00001_sajdjsjsj",
        appkey=APPKEY,
        comkeyid="xtoolsplusd002",
        comkey="xtoolsplusd002sjsjsj",
        com="d002",
        part="",
        sid_cache=tmp_path / "sid.json",
    )
    client = XToolsClient(config, clock=lambda: 1527746854.0, sleep=lambda s: None)
    fields = client.build_login_request(stamp="1527746854")
    assert fields["cmd"] == "user.login"
    assert fields["param"] == "[]"
    assert fields["upr"] == '{"comkeyid":"xtoolsplusd002","com":"d002","part":"","md":"d79d4e33a7771d8f0473f1bc0bd12f8e"}'
    assert fields["md"] == "d9a145ef66734897f0f38dd42a471873"


def test_build_request_reproduces_document_output_example(tmp_path):
    config = XToolsConfig(appid="open00001_sajdjsjsj", appkey=APPKEY, comkeyid="x", comkey="y", com="d002", sid_cache=tmp_path / "sid.json")
    client = XToolsClient(config, clock=lambda: 1549876028.0, sleep=lambda s: None)
    fields = client.build_request("api.output", {"dt": "customer", "id": 10}, {"sid": "4abda94f27512666f079e288ab44a287"})
    assert fields["stamp"] == "1549876028"
    assert fields["md"] == "79bdc07d245290beea7da0c9ec0fbb58"
