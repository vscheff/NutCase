"""Native TechDraw objects and bounded asynchronous HLR completion."""
import time
import os
from pathlib import Path

from fastener_analysis.geometry import App, Part

_qt_app = None


def initialize_gui():
    global _qt_app
    import FreeCADGui as Gui
    from PySide import QtWidgets, QtGui
    _qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # The Qt offscreen Windows platform may not enumerate system fonts. Load
    # the installed Arial faces into this process, avoiding fallback outline fonts.
    font_dir = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
    for filename in ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"):
        font_file = font_dir / filename
        if font_file.is_file():
            QtGui.QFontDatabase.addApplicationFontFromData(font_file.read_bytes())
    if not App.GuiUp:
        Gui.showMainWindow()
        Gui.getMainWindow().hide()
    import TechDraw
    import TechDrawGui
    return Gui, TechDrawGui


def wait_for_views(doc, views, timeout=30.0):
    doc.recompute()
    deadline, stable = time.monotonic() + timeout, 0
    while time.monotonic() < deadline:
        _qt_app.processEvents()
        ready = all("Up-to-date" in view.State and len(view.getVisibleEdges()) > 0 for view in views)
        pending_dimensions = [obj for obj in doc.Objects if obj.isDerivedFrom("TechDraw::DrawViewDimension") and "Touched" in obj.State]
        if ready and pending_dimensions:
            doc.recompute()
            ready = False
        stable = stable + 1 if ready else 0
        if stable >= 5:
            return
        time.sleep(0.04)
    raise RuntimeError("TechDraw did not complete reliable native projections within the timeout")


def flush_gui_deletions():
    from PySide import QtCore
    # The batch host pumps events rather than running Qt's normal exec loop.
    # Deferred widget deletion must complete before reopening the same page.
    QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.DeferredDelete)
    _qt_app.processEvents()


def make_view(doc, page, source, role, frame, position):
    view = doc.addObject("TechDraw::DrawViewPart", role.title().replace("_", ""))
    view.Label = {"longitudinal": "Longitudinal", "left_end": "Left end (-axis)",
                  "right_end": "Right end (+axis)", "isometric": "Isometric reference"}[role]
    view.Source = [source]
    view.Direction = App.Vector(*frame["direction"])
    view.XDirection = App.Vector(*frame["x_direction"])
    view.Perspective = False
    view.CoarseView = False
    view.ScrubCount = 0
    view.ScaleType = "Page"
    view.HardHidden = role != "isometric"
    view.SeamVisible = False
    view.SeamHidden = False
    view.SmoothVisible = False
    view.SmoothHidden = False
    view.ViewObject.LineWidth = 0.35
    view.ViewObject.HiddenWidth = 0.18
    view.ViewObject.FaceTransparency = 100
    view.ViewObject.ArcCenterMarks = False
    page.addView(view)
    view.X, view.Y = position["x_mm"], position["y_mm"]
    return view


def make_label(doc, page, role, position):
    label = doc.addObject("TechDraw::DrawViewAnnotation", role.title().replace("_", "") + "Label")
    label.Text = [{"longitudinal": "LONGITUDINAL", "left_end": "LEFT END", "right_end": "RIGHT END", "isometric": "ISOMETRIC REFERENCE", "section":"SECTION A-A","opening_detail":f"DETAIL B - OPENING PROFILE ({position.get('scale',1):g}:1)"}[role]]
    label.Font = "Arial"
    label.TextSize = 3.2
    label.TextColor = (0.0, 0.0, 0.0)
    page.addView(label)
    label.X, label.Y = position["label_x_mm"], position["label_y_mm"]
    return label


def projected_bounds(view):
    visible, hidden = view.getVisibleEdges(True), view.getHiddenEdges(True)
    if not visible:
        raise RuntimeError(f"View {view.Name} has no visible BRep projection")
    bound = Part.makeCompound(visible).optimalBoundingBox(False, False)
    return {"width_mm": bound.XLength, "height_mm": bound.YLength,
            "minimum_mm": [bound.XMin, bound.YMin], "maximum_mm": [bound.XMax, bound.YMax],
            "visible_edge_count": len(visible), "hidden_edge_count": len(hidden),
            "state": list(view.State), "scale_type": view.ScaleType}
