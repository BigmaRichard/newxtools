"""web/xlsx.py：纯标准库 .xlsx 写入器。"""

import datetime as dt
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from web.xlsx import col_letter, write_xlsx  # noqa: E402


def test_col_letter():
    assert [col_letter(i) for i in (0, 25, 26, 27, 51, 52, 701, 702)] == ["A", "Z", "AA", "AB", "AZ", "BA", "ZZ", "AAA"]


def test_write_xlsx_structure_types_and_escaping():
    data = write_xlsx([("订单/列表:测试", ["日期", "客户", "金额", "单数", "备注"],
                        [["2026-09-18", "研创<生物> & 公司", 1234.5, 3, "换行\n控制\x01字符"], [dt.date(2026, 1, 1), None, float("nan"), 0, True]]),
                       ("订单/列表:测试", ["a"], [])])
    z = zipfile.ZipFile(io.BytesIO(data))
    assert z.testzip() is None
    assert set(z.namelist()) >= {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "xl/styles.xml", "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"}
    wb = z.read("xl/workbook.xml").decode()
    assert 'name="订单 列表 测试"' in wb and 'name="订单 列表 测试(1)"' in wb  # 非法字符替换、重名去重
    sheet = z.read("xl/worksheets/sheet1.xml").decode()
    assert '<c r="A1" s="1" t="inlineStr"><is><t>日期</t></is></c>' in sheet
    assert "研创&lt;生物&gt; &amp; 公司" in sheet and "换行\n控制字符" in sheet  # XML 转义、剔除控制字符
    assert '<c r="C2" s="2"><v>1234.5</v></c>' in sheet and '<c r="D2" s="3"><v>3</v></c>' in sheet
    assert '<c r="A3" t="inlineStr"><is><t xml:space="preserve">2026-01-01</t></is></c>' in sheet
    assert 'r="C3"' not in sheet and 'r="B3"' not in sheet  # NaN 与 None 为空单元格
    assert "<t>是</t>" in sheet
    assert 'state="frozen"' in sheet and '<autoFilter ref="A1:E3"/>' in sheet
    empty = z.read("xl/worksheets/sheet2.xml").decode()
    assert "autoFilter" not in empty and '<dimension ref="A1:A1"/>' in empty
