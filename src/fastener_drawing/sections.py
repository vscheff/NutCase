"""Native axial section and an independent original-BRep intersection diagnostic."""
from pathlib import Path
from fastener_analysis.geometry import App, Part
from .orientation import native_projected_envelope
from .views import wait_for_views


def rendered_hatching(svg_path,section):
    """Observe native diagonal hatch strokes; never construct replacement ink.

    With hidden edges disabled, the section's hatch-weight 45-degree line
    groups distinguish the native Diagonal4 pattern from outlines/dimensions.
    This is a render diagnostic; correctness still requires PDF inspection.
    """
    import re
    import xml.etree.ElementTree as ET
    from .svg_placement import multiply,transform_matrix
    root=ET.parse(svg_path).getroot()
    box=[float(v) for v in root.attrib["viewBox"].split()]
    ratio=box[2]/float(root.attrib["width"].replace("mm",""))
    height=float(root.attrib["height"].replace("mm",""))
    parameters=section if isinstance(section,dict) else {"x_mm":section.X.Value,"y_mm":section.Y.Value,"weight_mm":float(section.ViewObject.WeightPattern)}
    center=[parameters["x_mm"]*ratio,(height-parameters["y_mm"])*ratio]
    count=0
    def visit(node,parent,style):
        nonlocal count
        matrix=multiply(parent,transform_matrix(node.attrib.get("transform","")))
        style={**style,**node.attrib}
        if (node.tag.rsplit("}",1)[-1]=="path" and style.get("stroke-opacity","1")=="1"
            and abs(float(style.get("stroke-width","0"))-parameters["weight_mm"]*ratio)<.001
            and max(abs(matrix[i+4]-center[i]) for i in (0,1))<.01):
            match=re.fullmatch(r"M([-+\d.eE]+),([-+\d.eE]+) L([-+\d.eE]+),([-+\d.eE]+)",node.attrib.get("d",""))
            if match:
                x,y,p,q=map(float,match.groups())
                if abs(abs(p-x)-abs(q-y))<.01 and abs(p-x)>.1:count+=1
        for child in node:visit(child,matrix,style)
    visit(root,(1,0,0,1,0,0),{})
    return {"status":"native_hatch_strokes_rendered" if count>=4 else "requires_manual_completion",
            "native_diagonal_stroke_count":count,"visual_verification_required":True,
            "reason":"Native vector hatch strokes observed on the section; material coverage must be visually verified" if count>=4 else
                "Native cut outlines exist but section-face conversion produced no reliable visible hatch pattern; manual completion required",
            "original_geometry_unchanged":True}


def section_geometry(shape, frames, origin):
    axis, up = App.Vector(*frames["axis"]), App.Vector(*frames["up"])
    origin=App.Vector(*origin)
    size=shape.BoundBox.DiagonalLength*2+10
    corners=[origin+axis*x+up*y for x,y in [(-size,-size),(size,-size),(size,size),(-size,size),(-size,-size)]]
    cut=shape.section(Part.Face(Part.makePolygon(corners)))
    if cut.isNull() or not cut.isValid() or not cut.Edges:
        raise ValueError("Original BRep plane intersection failed or is empty/invalid")
    wires=[Part.Wire(edges) for edges in Part.sortEdges(cut.Edges)]
    diagnostic={"status":"source_intersection_computed","source_edge_count":len(cut.Edges),
                "closed_loop_count":sum(w.isClosed() for w in wires),"open_trace_count":sum(not w.isClosed() for w in wires),
                "source_healed":False,"basis":"Independent native Part section of original STEP with plane through recovered axis",
                "limitation":"Open intersection traces retained as a source-quality warning; no solid reconstruction or healing performed" if any(not w.isClosed() for w in wires) else None}
    return cut,diagnostic


def make_section(doc,page,source,base,frames,origin,position):
    sec=doc.addObject("TechDraw::DrawViewSection","Section")
    sec.Label="Axial section A-A"
    sec.BaseView=base;sec.Source=[source]
    sec.SectionDirection="Aligned"
    sec.SectionNormal=App.Vector(*frames["front_normal"])
    sec.SectionOrigin=App.Vector(*origin)
    sec.XDirection=App.Vector(*frames["axis"])
    sec.SectionSymbol="A"
    sec.SectionLineStretch=1.15
    sec.CutSurfaceDisplay="PatHatch"
    sec.FileGeomPattern=str(Path(App.getResourceDir())/"Mod/TechDraw/PAT/FCPAT.pat")
    sec.NameGeomPattern="Diagonal4"  # Generic 45-degree hatch, no material assertion.
    sec.HatchScale=.6
    sec.HardHidden=False;sec.CoarseView=False;sec.ScrubCount=0;sec.ScaleType="Page"
    sec.SeamVisible=False;sec.SmoothVisible=False
    sec.ViewObject.LineWidth=.35;sec.ViewObject.HiddenWidth=.18
    sec.ViewObject.HatchCutSurface=True
    sec.ViewObject.CutSurfaceColor=(1.0,1.0,1.0,1.0)
    sec.ViewObject.HatchColor=(0.0,0.0,0.0,1.0)
    sec.ViewObject.GeomHatchColor=(0.0,0.0,0.0,1.0)
    sec.ViewObject.WeightPattern=.18
    page.addView(sec);sec.X,sec.Y=position["x_mm"],position["y_mm"]
    wait_for_views(doc,[sec])
    return sec
