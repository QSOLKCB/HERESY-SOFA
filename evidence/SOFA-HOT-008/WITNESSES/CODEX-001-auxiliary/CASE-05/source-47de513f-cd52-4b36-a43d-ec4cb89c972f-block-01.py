import re, zipfile
from openpyxl import Workbook
from openpyxl.formatting.rule import Rule
from openpyxl.styles import Font
from openpyxl.styles.differential import DifferentialStyle

wb = Workbook()
ws = wb.active
ws["A1"] = '=1'
ws.conditional_formatting.add(
    "A1:A2",
    Rule(type="expression", formula=["A1=1"], stopIfTrue=False, priority=7,
         dxf=DifferentialStyle(font=Font(italic=True, color="FFD9D9DB"))),
)
wb.save("cf.xlsx")

z = zipfile.ZipFile("cf.xlsx")
styles = z.read("xl/styles.xml").decode()
print(re.search(r"<dxfs.*?</dxfs>", styles, re.S).group(0))
print(z.read("xl/worksheets/sheet1.xml").decode().split("<conditionalFormatting")[1][:200])
