"""Minimal intended style delta. Excel-side effectiveness still requires Excel evidence."""

# With openpyxl installed, the intended distinction is:
# base = Font(name="Calibri", size=11, color="FF000000", italic=False)
# dxf = DifferentialStyle(font=Font(italic=True, color="FFD9D9DB"))


def effective_italic(base_italic, conditional_italic, condition):
    """OOXML-style property overlay model, not an Excel renderer."""
    return conditional_italic if condition and conditional_italic is not None else base_italic
