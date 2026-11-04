import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Evidence

e=Evidence(5)
spec=importlib.util.find_spec('openpyxl')
e.data['availability']={'openpyxl_module':spec.origin if spec else None}
if spec is None:
    e.data['limitations']=[
      dict(label='NOT_TESTED',claim='All openpyxl-generated XLSX serialization, roundtrip, formulas, relationship, dxfId, base-font and FormulaRule comparisons',reason='openpyxl not installed in the available test runtime; no dependency installed'),
      dict(label='NOT_TESTED',claim='Excel visual rendering/recalculation',reason='No genuine Excel-side evidence; LibreOffice not used'),
      dict(label='INFERRED',claim='The proposed Font(italic=True) makes base italic unconditional; a false rule cannot demonstrate a conditional transition from roman to italic'),
      dict(label='UNSUPPORTED',claim='Default base font is the demonstrated Excel defect and explicitly setting it cures the UI')]
    e.data['skipped_artifacts']=['Generated XLSX variants','Generated OOXML extraction','Excel visual evidence']
    e.finish()
    raise SystemExit(0)

import openpyxl
from openpyxl import Workbook,load_workbook
from openpyxl.formatting.rule import Rule,FormulaRule
from openpyxl.styles import Font
from openpyxl.styles.differential import DifferentialStyle
e.data['openpyxl_version']=openpyxl.__version__
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
results=[]
for variant,base_italic,condition,base_kind in [
    ('default_true',False,'1=1','default'),('default_false',False,'1=0','default'),
    ('explicit_roman_true',False,'1=1','explicit'),('explicit_roman_false',False,'1=0','explicit'),
    ('base_italic_true',True,'1=1','explicit'),('base_italic_false',True,'1=0','explicit'),
    ('empty_Font_true',False,'1=1','empty')]:
    wb=Workbook();ws=wb.active;ws['A1']=1;ws['A2']=0
    if base_kind!='default':
        for cell in [ws['A1'],ws['A2']]:
            cell.font=Font() if base_kind=='empty' else Font(name='Calibri',size=11,color='FF000000',italic=base_italic)
    font=Font(italic=True,color='FFD9D9DB')
    ws.conditional_formatting.add('A1:A2',Rule(type='expression',formula=[condition],priority=7,stopIfTrue=False,dxf=DifferentialStyle(font=font)))
    filename=e.folder/(variant+'.xlsx');wb.save(filename)
    with zipfile.ZipFile(filename) as z:
        for part in ['xl/styles.xml','xl/worksheets/sheet1.xml','xl/_rels/workbook.xml.rels','xl/workbook.xml']:
            (e.folder/(variant+'-'+part.replace('/','_'))).write_bytes(z.read(part))
        styles=ET.fromstring(z.read('xl/styles.xml')); sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        rule=sheet.find('.//s:cfRule',NS)
        index=int(rule.attrib['dxfId']);dxfs=styles.find('s:dxfs',NS)
        e.check(variant+'_dxf_resolves',0<=index<len(dxfs),True)
        dxf=dxfs[index]
        e.check(variant+'_conditional_italic',dxf.find('s:font/s:i',NS).attrib.get('val'),'1')
        e.check(variant+'_conditional_colour',dxf.find('s:font/s:color',NS).attrib.get('rgb'),'FFD9D9DB')
        e.check(variant+'_formula',rule.find('s:formula',NS).text,condition)
        rel=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        e.check(variant+'_sheet_relationship',any(x.attrib.get('Type','').endswith('/worksheet') and x.attrib['Target'].endswith('sheet1.xml') for x in rel),True)
        cell=sheet.find('.//s:c',NS);style=int(cell.attrib.get('s','0'))
        font_id=int(styles.find('s:cellXfs',NS)[style].attrib['fontId'])
        italic=styles.find('s:fonts',NS)[font_id].find('s:i',NS)
        actual_italic=italic is not None and italic.attrib.get('val','1')!='0'
        e.check(variant+'_base_italic_independent_of_rule',actual_italic,base_italic,kind='negative' if base_italic and condition=='1=0' else 'positive')
        results.append(dict(variant=variant,base_fontId=font_id,base_italic=actual_italic,formula=condition,dxfId=index))
    reloaded=load_workbook(filename)
    e.check(variant+'_roundtrip_rule_count',len(reloaded.active.conditional_formatting),1)
    # Compare equivalent serialized rule elements with the SAME fields and dxfId.
    fr=FormulaRule(formula=[condition],font=font,stopIfTrue=False);fr.priority=7;fr.dxfId=0
    rr=Rule(type='expression',formula=[condition],priority=7,stopIfTrue=False,dxfId=0,dxf=DifferentialStyle(font=font))
    e.check(variant+'_equivalent_formula_rule_XML',ET.tostring(fr.to_tree()).decode(),ET.tostring(rr.to_tree()).decode())
e.data['xml_results']=results
e.data['limitations']=[dict(label='NOT_TESTED',claim='Excel visual rendering or recalculation; XML structure does not prove a UI fix')]
e.finish()
