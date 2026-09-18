"""纯标准库生成 .xlsx（Office Open XML），供本地前台“导出 Excel”使用，不依赖 openpyxl。

* 一个文件可含多个工作表；表头加粗、冻结首行、自动筛选；列宽按内容估算。
* 单元格：None → 空；int / float → 数值（千分位两位小数样式）；date / datetime → 文本（ISO）；其余 → 文本（inlineStr，不用共享字符串表）。
* XML 1.0 不允许的控制字符会被剔除；工作表名去掉非法字符并截到 31 字。
"""

from __future__ import annotations

import datetime as dt
import io
import math
import re
import zipfile
from typing import Any, Iterable, List, Sequence, Tuple
from xml.sax.saxutils import escape

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
_BAD_SHEET = re.compile(r"[\[\]:*?/\\]")

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
{sheets}</Types>"""
_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>{sheets}</sheets></workbook>"""
_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
{sheets}</Relationships>"""
# 样式：0 普通文本；1 表头（加粗、浅灰底）；2 数值（千分位两位小数）；3 整数
_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF2F2F2"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
<xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def col_letter(index: int) -> str:
    """0 → A，25 → Z，26 → AA。"""
    out = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def _text(value: Any) -> str:
    return escape(_CONTROL.sub("", str(value)))


def _cell(ref: str, value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return f'<c r="{ref}" t="inlineStr"><is><t>{"是" if value else "否"}</t></is></c>'
    if isinstance(value, int):
        return f'<c r="{ref}" s="3"><v>{value}</v></c>'
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return f'<c r="{ref}" s="2"><v>{repr(value)}</v></c>'
    if isinstance(value, (dt.date, dt.datetime)):
        value = value.isoformat(sep=" ") if isinstance(value, dt.datetime) else value.isoformat()
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{_text(value)}</t></is></c>'


def _width(value: Any) -> float:
    """按字符数估算列宽：中文按 2 个宽度单位。"""
    s = "" if value is None else str(value)
    w = 0.0
    for ch in s[:80]:
        w += 2.0 if ord(ch) > 0x2E7F else 1.1
    return w


def sheet_xml(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    widths = [max(4.0, _width(h) + 2) for h in headers]
    body: List[str] = []
    n_rows = 1
    body.append("<row r=\"1\">" + "".join(f'<c r="{col_letter(i)}1" s="1" t="inlineStr"><is><t>{_text(h)}</t></is></c>' for i, h in enumerate(headers)) + "</row>")
    for row in rows:
        n_rows += 1
        cells = []
        for i, value in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], min(60.0, _width(value) + 2))
            cells.append(_cell(f"{col_letter(i)}{n_rows}", value))
        body.append(f'<row r="{n_rows}">' + "".join(cells) + "</row>")
    last = f"{col_letter(max(len(headers) - 1, 0))}{n_rows}"
    cols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w:.1f}" customWidth="1"/>' for i, w in enumerate(widths))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last}"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f"<cols>{cols}</cols><sheetData>{''.join(body)}</sheetData>"
        + (f'<autoFilter ref="A1:{last}"/>' if headers and n_rows > 1 else "")
        + "</worksheet>"
    )


def write_xlsx(sheets: Sequence[Tuple[str, Sequence[str], Iterable[Sequence[Any]]]]) -> bytes:
    """sheets: [(工作表名, 表头列表, 行迭代器), ...] → .xlsx 字节。"""
    if not sheets:
        sheets = [("Sheet1", [], [])]
    names: List[str] = []
    for i, (name, _, _) in enumerate(sheets):
        clean = (_BAD_SHEET.sub(" ", str(name)).strip() or f"Sheet{i + 1}")[:31]
        while clean in names:
            clean = clean[:28] + f"({len(names)})"
        names.append(clean)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES.format(sheets="".join(
            f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(len(sheets)))))
        z.writestr("_rels/.rels", _RELS)
        z.writestr("xl/workbook.xml", _WORKBOOK.format(sheets="".join(
            f'<sheet name="{escape(names[i])}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i in range(len(sheets)))))
        z.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS.format(sheets="".join(
            f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
            for i in range(len(sheets)))))
        z.writestr("xl/styles.xml", _STYLES)
        for i, (_, headers, rows) in enumerate(sheets):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", sheet_xml(list(headers), rows))
    return buf.getvalue()
