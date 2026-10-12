"""Minimal ANSI-style border and editable title block for native SVG templates."""
import textwrap
from xml.sax.saxutils import escape


def make_template(path, layout, filename, date_text, needs_geometry_review, dimensions=False, metadata=None):
    width, height = layout["width_mm"], layout["height_mm"]
    # Keep a conventional lower-right title block and lower-left drawing notes.
    block_width, block_height = 190.0, 44.0
    x, y = width - 10 - block_width, height - 10 - block_height
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:freecad="http://www.freecad.org/wiki/index.php?title=Svg_Namespace" width="{width}mm" height="{height}mm" viewBox="0 0 {width} {height}" version="1.1">',
             f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" stroke="none"/>',
             '<g fill="none" stroke="#000000" stroke-width="0.5">',
             f'<rect x="10" y="10" width="{width - 20}" height="{height - 20}"/>',
             f'<rect x="{x}" y="{y}" width="{block_width}" height="{block_height}"/>',
             f'<path d="M {x} {y + 11} H {width - 10} M {x} {y + 25} H {width - 10} M {x} {y + 35} H {width - 10}"/>',
             f'<path d="M {x + 50} {y + 25} V {y + 35} M {x + 86} {y + 25} V {y + 35} M {x + 119} {y + 25} V {y + 35}"/>',
             '</g>']

    def text(tx, ty, value, size=3.0, bold=False, field=None):
        attribute = f' freecad:editable="{field}"' if field else ''
        content = f'<tspan x="{tx}" y="{ty}">{escape(value)}</tspan>'
        lines.append(f'<text x="{tx}" y="{ty}" font-family="Arial" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="#000000"{attribute}>{content}</text>')

    text(14, 19, "PRELIMINARY TECHNICAL DRAWING", 3.0, True)
    text(width - 60, 19, f"{layout['sheet']} / LANDSCAPE", 2.5)
    text(x + 3, y + 3.6, "TITLE", 1.9)
    metadata = metadata or {}
    title = metadata.get('title', 'IMPORTED STEP GEOMETRY')
    # Keep metadata inside its physical field at readable size; refuse overflow.
    if len(title) > 65:raise ValueError('Title exceeds supported title-block length')
    def field_text(value, maximum_mm, sizes, bold=False):
        # The GUI host has initialized actual fonts. Pure geometry/unit-test
        # callers can use a conservative one-em-per-character bound instead.
        factor=float(len(value))
        try:
            from PySide6.QtGui import QFont,QFontMetricsF,QGuiApplication
            if QGuiApplication.instance():
                font=QFont('Arial');font.setPixelSize(100);font.setBold(bold)
                factor=QFontMetricsF(font).horizontalAdvance(value)/100
        except ImportError:pass
        for size in sizes:
            if factor*size<=maximum_mm:return size
        raise ValueError('Metadata text exceeds its physical title-block field at readable size: '+value)
    text(x + 3, y + 8.5, title, field_text(title,block_width-6,(3.5,3.0),True), True, "Title")
    number, revision = metadata.get('drawing_number', ''), metadata.get('revision', '')
    if number or revision:
        identifier=f"DRAWING: {number}    REV: {revision}"
        text(x+3, y-3, identifier, field_text(identifier,block_width-6,(2.7,)), field='DrawingNumberRevision')
    text(x + 3, y + 14.5, "SOURCE FILE", 1.9)
    wrapped = textwrap.wrap(filename, width=105, break_long_words=True, break_on_hyphens=False)
    if len(wrapped) > 2:
        raise ValueError("Source filename is too long for the supported title block; rename the input or choose a larger title layout")
    for index, value in enumerate(wrapped):
        text(x + 3, y + 19.0 + index * 3.7, value, 2.5, field=f"Source{index + 1}")
    text(x + 3, y + 28, "GENERATED", 1.9)
    text(x + 3, y + 32.8, date_text, 3.0, field="Date")
    text(x + 53, y + 28, "SCALE", 1.9)
    text(x + 53, y + 32.8, layout["scale_label"], 3.0, field="Scale")
    text(x + 89, y + 28, "UNITS", 1.9)
    text(x + 89, y + 32.8, "mm", 3.0)
    text(x + 122, y + 28, "PROJECTION / SHEET", 1.9)
    text(x + 122, y + 32.8, "THIRD ANGLE / 1 OF 1", 2.7)
    text(x + 3, y + 40.7, "PRELIMINARY - ENGINEERING VERIFICATION REQUIRED", 2.8, True)
    # Standard third-angle symbol: frustum on the left, circular end view on the right.
    sx, sy = width - 45, height - 62
    lines.extend(['<g fill="none" stroke="#000000" stroke-width="0.25">',
                  f'<path d="M {sx} {sy - 2.5} L {sx + 8} {sy - 4} L {sx + 8} {sy + 4} L {sx} {sy + 2.5} Z"/>',
                  f'<path d="M {sx - 1} {sy} H {sx + 28} M {sx + 21} {sy - 5} V {sy + 5}"/>',
                  f'<circle cx="{sx + 21}" cy="{sy}" r="4"/><circle cx="{sx + 21}" cy="{sy}" r="2.5"/>', '</g>'])
    # Compact notes adapt to smaller sheets without entering the title block.
    note_width = x - 18
    if note_width >= 125:
        text(14, y + 5, "DRAWING NOTES", 2.6, True)
        notes = ["1. Preliminary; engineering verification required.",
                 "2. Dimensions measure STEP geometry only." if dimensions else "2. Original STEP BRep; no dimensions assigned.",
                 "3. Extended Boolean check failed; review geometry." if needs_geometry_review else "3. Native geometry checks retained in project/report."]
        if dimensions:
            notes.append("4. Not approved manufacturing specifications.")
        if "section" in layout["positions"]:
            notes.extend(["5. Section hatching requires visual verification.","6. Geometric baseline supports are listed in report."])
        for index, note in enumerate(notes):
            text(14, y + 11 + index * 5, note, 2.7)
    else:
        text(14, y - 8, "MEASURED STEP GEOMETRY - PRELIMINARY" if dimensions else "PRELIMINARY - NO DIMENSIONS", 2.6)
        if needs_geometry_review:
            text(14, y - 3, "SOURCE GEOMETRY REQUIRES REVIEW", 2.5)
    lines.append('</svg>')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
