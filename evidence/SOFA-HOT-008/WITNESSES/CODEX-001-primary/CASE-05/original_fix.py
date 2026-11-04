"""Preserved proposed fix; not imported when openpyxl is unavailable."""

from openpyxl.styles import Font

base = Font(name="Calibri", size=11, color="FF000000", italic=True)
for row in ws["A1:A2"]:  # noqa: F821 - context comes from the post's earlier block
    for cell in row:
        cell.font = base
ws.conditional_formatting.add(  # noqa: F821
    "A1:A2",
    Rule(  # noqa: F821
        type="expression",
        formula=["A1=1"],
        stopIfTrue=False,
        priority=7,
        dxf=DifferentialStyle(font=Font(italic=True, color="FFD9D9DB")),  # noqa: F821
    ),
)
wb.save("cf_fixed.xlsx")  # noqa: F821
