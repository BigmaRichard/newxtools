"""离线测试：行动记录正文里的人名抽取（规则法；不依赖 jieba）。

运行：python -m pytest tests -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web.names import extract_names  # noqa: E402


def names(text, **kw):
    return [(m.name, m.surname_only) for m in extract_names(text, **kw)]


def test_name_followed_by_title():
    assert names("电话拜访QC王艳萍老师，要做氨甲环酸") == [("王艳萍", False)]
    assert names("上门开发客户，拜访董荣贵老师，用安捷伦") == [("董荣贵", False)]
    assert names("拜访了张三老师和王工，见到了刘博士") == [("张三", False), ("王工", True), ("刘博士", True)]


def test_title_followed_by_name():
    assert names("电话拜访采购史德均老师，咨询了益母草颗粒专用柱") == [("史德均", False)]
    assert names("上门拜访纯化组长金舫，金老师这边现在主要做cdmo项目") == [("金舫", False)]  # 金老师并入金舫
    assert names("上门拜访深圳百川泓沛生物科技有限公司总经理姚林，先是沟通了") == [("姚林", False)]
    assert names("他让我和做纯化的张晨阳进行了项目沟通，张老师告知他") == [("张晨阳", False)]


def test_name_surname_title_form():
    assert names("拜访付玉清付总，付总这边比较忙，简单聊了两句") == [("付玉清", False)]


def test_surname_only_and_false_positives():
    assert names("电话拜访QC彭老师，要买一支氨基柱") == [("彭老师", True)]
    assert names("和对方老师沟通，公司李总不在，施工中，高工说下周，技术方案还没定") == [("李总", True)]
    assert names("大连依利特销售以及上海汉尧销售都过来咨询过价格") == []
    assert names("提报到慕春雨科长那面，审批以后就可以采购") == []
    assert names("现阶段他主要是筛选大曹填料，目前用月旭的氨基柱，做司美和替尔") == []


def test_registered_names_and_exclusions():
    text = "上门拜访纯化组长屈文杰，询问项目；拜访付玉清付总；李文邦陪同"
    got = extract_names(text, known=["屈文杰", "付玉清", "邓伟梅"], exclude=["李文邦"])
    assert [(m.name, m.source) for m in got] == [("屈文杰", "registered"), ("付玉清", "registered")]


def test_org_fragments_are_not_names():
    assert names("拜访了云南中医药大学药学院9504陈兴农组陈老师，实验室有4台液相") == [("陈老师", True)]
    assert names("现场拜访药宜立康詹老师，这边最近正好要开奥", orgs=["成都药宜立康医药科技有限公司"]) == [("詹老师", True)]
    assert names("蓝博思的杨总说可以，姚博这边同意", orgs=["宁夏蓝博思化学技术有限公司"]) == [("杨总", True), ("姚博", True)]
