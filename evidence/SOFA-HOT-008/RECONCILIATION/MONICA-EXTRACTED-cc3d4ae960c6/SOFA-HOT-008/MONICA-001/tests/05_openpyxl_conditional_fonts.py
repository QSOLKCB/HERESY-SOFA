#!/usr/bin/env python3
"""openpyxl package/XML audit; intentionally does not claim Excel UI rendering."""
from __future__ import annotations
import json, re, tempfile, zipfile
from pathlib import Path
from openpyxl import Workbook
from openpyxl.formatting.rule import Rule
from openpyxl.styles import Font
from openpyxl.styles.differential import DifferentialStyle

def make(path: Path, explicit: bool) -> tuple[str,str]:
    wb=Workbook(); ws=wb.active; ws['A1']='=1'
    if explicit:
        ws['A1'].font=Font(name='Calibri',size=11,color='FF000000',italic=True)
    ws.conditional_formatting.add('A1:A1', Rule(type='expression',formula=['A1=1'],dxf=DifferentialStyle(font=Font(italic=True,color='FFD9D9DB'))))
    wb.save(path)
    with zipfile.ZipFile(path) as z:
        return z.read('xl/styles.xml').decode(),z.read('xl/worksheets/sheet1.xml').decode()

def main() -> None:
  with tempfile.TemporaryDirectory() as d:
    s0,w0=make(Path(d)/'implicit.xlsx',False); s1,w1=make(Path(d)/'explicit.xlsx',True)
  for styles,sheet in [(s0,w0),(s1,w1)]:
    assert re.search(r'<dxf>.*?<font>.*?<i val="1"/>.*?</font>.*?</dxf>',styles,re.S)
    assert re.search(r'<cfRule[^>]*dxfId="0"',sheet)
  # Explicit base font affects cell style table, not the conditional dxf's italic declaration.
  assert s0.count('<xf ') < s1.count('<xf ')
  assert re.search(r'<i val="1"/>',s0) and re.search(r'<i val="1"/>',s1)
  print(json.dumps({'case_id':'47de513f-cd52-4b36-a43d-ec4cb89c972f','execution':'openpyxl 3.1.5 XML serialization only','assertions':7,'negative_control':{'name':'claim_xml_proves_excel_ui_recalc','detected':True,'result':'XML equivalence/difference cannot prove Excel visual rendering or a click-OK repair mechanism'},'verified':'Both implicit and explicit variants serialize a differential italic font and cfRule dxfId. Explicit base font changes base cell style XML.','not_tested':'Excel-side visible conditional formatting behaviour; Excel was not available and LibreOffice was not used as a substitute.','recommendation':'VERIFY: retain only the serialization claim; require a controlled Excel-version reproduction before asserting causation or correction.'},indent=2))
if __name__=='__main__': main()
