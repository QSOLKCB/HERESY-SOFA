from openpyxl.styles import Font

base = Font(name="Calibri", size=11, color="FF000000", italic=True)
for row in ws["A1:A2"]:
    for cell in row:
        cell.font = base
ws.conditional_formatting.add(
    "A1:A2",
    Rule(type="expression", formula=["A1=1"], stopIfTrue=False, priority=7,
         dxf=DifferentialStyle(font=Font(italic=True, color="FFD9D9DB"))),
)
wb.save("cf_fixed.xlsx")
