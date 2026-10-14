"""Physical text bounds from the native vector scene, using Qt font metrics.

This checks presentation only. All feature measurements/references are verified
against the original BRep and native projected geometry in separate modules.
"""
import re
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from .dimensions import displayed_text,overlaps

# Trailing-zero suppression changes the native label width and therefore
# TechDraw's automatic arrow direction. Keep a visible paper gap after that
# width changes instead of relying on the older fixed-decimal label behavior.
ARROW_TEXT_GAP_MM=2.0


class ArrowTextCollision(RuntimeError):
    def __init__(self,key):
        self.minimum_gap_mm=ARROW_TEXT_GAP_MM
        super().__init__(key+': diameter text collides with an arrowhead or its required clearance')


def arrow_bounds(svg):
    """Bounds of actual filled native arrow triangles, including their stroke.

    These are presentation polygons in paper coordinates, not CAD features.
    Ignore transparent faces and unrecognized paths rather than guessing.
    """
    root=ET.parse(svg).getroot()
    box=[float(v) for v in root.attrib['viewBox'].split()]
    rx=box[2]/float(root.attrib['width'].replace('mm',''))
    ry=box[3]/float(root.attrib['height'].replace('mm',''))
    number=r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'
    triangle=re.compile(r'^\s*M\s*('+number+r')[,\s]+('+number+r')'
                        +3*(r'\s*L\s*('+number+r')[,\s]+('+number+r')')+r'\s*[zZ]?\s*$')
    result=[]
    def visit(node,parent,style):
        matrix=multiply(parent,transform_matrix(node.attrib.get('transform','')))
        style={**style,**node.attrib}
        match=triangle.fullmatch(node.attrib.get('d','')) if node.tag.rsplit('}',1)[-1]=='path' else None
        if (match and style.get('fill','none')!='none' and float(style.get('fill-opacity',1))>0
                and float(style.get('opacity',1))>0):
            values=list(map(float,match.groups()))
            points=list(zip(values[::2],values[1::2]))
            if points[0]==points[-1] and len(set(points[:-1]))==3:
                points=[((matrix[0]*x+matrix[2]*y+matrix[4]-box[0])/rx,
                         (matrix[1]*x+matrix[3]*y+matrix[5]-box[1])/ry) for x,y in points[:-1]]
                # Affine scale of the native stroke, converted to paper mm.
                stroke=float(style.get('stroke-width',0))/2 if style.get('stroke','none')!='none' else 0
                px=stroke*math.hypot(matrix[0],matrix[2])/rx
                py=stroke*math.hypot(matrix[1],matrix[3])/ry
                result.append({'left':min(p[0] for p in points)-px,'right':max(p[0] for p in points)+px,
                               'top':min(p[1] for p in points)-py,'bottom':max(p[1] for p in points)+py})
        for child in node:visit(child,matrix,style)
    visit(root,(1,0,0,1,0,0),{})
    return result


def diameter_arrow_checks(doc,reports,svg,texts=None):
    """Require diameter labels to clear every rendered arrow on the page."""
    texts=text_bounds(svg) if texts is None else texts
    arrows=arrow_bounds(svg);checks={}
    page_height=doc.DrawingPage.Template.Height.Value
    for key,record in reports.items():
        if record['status']!='created' or '⌀' not in record['format_spec']:continue
        dim=doc.getObject(record['object_name']);value=displayed_text(dim,record)
        matches=[t for t in texts if t['text']==value]
        if not matches:raise RuntimeError(key+': actual native rendered dimension text was not found')
        if not arrows:raise RuntimeError(key+': native filled-arrow geometry was not found for clearance validation')
        view=dim.References2D[0][0]
        ax,ay=view.X.Value+dim.X.Value,page_height-view.Y.Value-dim.Y.Value
        found=min(matches,key=lambda t:abs((t['bounds_mm']['left']+t['bounds_mm']['right'])/2-ax)
                  +abs((t['bounds_mm']['top']+t['bounds_mm']['bottom'])/2-ay))
        if any(overlaps(found['bounds_mm'],arrow,ARROW_TEXT_GAP_MM) for arrow in arrows):
            raise ArrowTextCollision(key)
        checks[key]={'arrow_text_clearance_verified':True,'minimum_arrow_text_gap_mm':ARROW_TEXT_GAP_MM,
                     'native_arrow_polygons_checked':len(arrows),
                     'basis':'Rendered native text and filled-arrow triangle bounds, including arrow stroke, in paper millimeters'}
    return checks

def multiply(a,b):
    return (a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],
            a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5])


def transform_matrix(value):
    result=(1,0,0,1,0,0)
    for kind,args in re.findall(r'(\w+)\(([^)]+)\)',value):
        v=[float(n) for n in re.split(r'[,\s]+',args.strip())]
        if kind=='matrix':matrix=tuple(v)
        elif kind=='scale':matrix=(v[0],0,0,v[-1],0,0)
        elif kind=='translate':matrix=(1,0,0,1,v[0],v[1] if len(v)>1 else 0)
        elif kind=='rotate':
            angle=math.radians(v[0]);c,s=math.cos(angle),math.sin(angle);matrix=(c,s,-s,c,0,0)
            if len(v)==3:matrix=multiply(multiply((1,0,0,1,v[1],v[2]),matrix),(1,0,0,1,-v[1],-v[2]))
        else:raise RuntimeError('Unsupported native SVG transform '+kind)
        result=multiply(result,matrix)
    return result


def text_bounds(svg):
    from PySide import QtGui
    root=ET.parse(svg).getroot()
    box=[float(v) for v in root.attrib['viewBox'].split()]
    width=float(root.attrib['width'].replace('mm',''))
    height=float(root.attrib['height'].replace('mm',''))
    rx,ry=box[2]/width,box[3]/height
    result=[]
    def visit(node,parent,style):
        transform=node.attrib.get('transform','')
        matrix=transform_matrix(transform)
        matrix=multiply(parent,matrix)
        style={**style,**{k:v for k,v in node.attrib.items() if k.startswith('font-')}}
        texts=[child for child in node if child.tag.rsplit('}',1)[-1]=='text']
        if texts:
            bounds=[];content=[]
            for child in texts:
                value=''.join(child.itertext());content.append(value)
                font_style={**style,**child.attrib}
                font=QtGui.QFont(font_style.get('font-family','Arial'))
                font.setPixelSize(round(float(font_style.get('font-size','48'))))
                weight=font_style.get('font-weight','400')
                font.setBold(weight=='bold' or (weight.isdigit() and int(weight)>=600))
                font.setItalic(font_style.get('font-style')=='italic')
                rect=QtGui.QFontMetricsF(font).boundingRect(value)
                x,y=float(child.attrib.get('x',0)),float(child.attrib.get('y',0))
                for px,py in ((rect.left()+x,rect.top()+y),(rect.right()+x,rect.top()+y),(rect.right()+x,rect.bottom()+y),(rect.left()+x,rect.bottom()+y)):
                    bounds.append(((matrix[0]*px+matrix[2]*py+matrix[4]-box[0])/rx,(matrix[1]*px+matrix[3]*py+matrix[5]-box[1])/ry))
            result.append({'text':''.join(content).strip(),'bounds_mm':{'left':min(p[0] for p in bounds),'right':max(p[0] for p in bounds),
                          'top':min(p[1] for p in bounds),'bottom':max(p[1] for p in bounds)}})
        for child in node:
            if child.tag.rsplit('}',1)[-1]!='text':visit(child,matrix,style)
    visit(root,(1,0,0,1,0,0),{})
    return result


def check(doc,reports,layout,paper_boxes,svg):
    texts=text_bounds(svg)
    arrow_checks=diameter_arrow_checks(doc,reports,svg,texts)
    captions=[t['bounds_mm'] for t in texts if t['text'].startswith('DETAIL ') or t['text'] in ('LONGITUDINAL','LEFT END','RIGHT END','ISOMETRIC REFERENCE','SECTION A-A','AXIAL CUT A-A (UNHATCHED)','A')]
    occupied=[];checks={};area=layout['content_area_top_origin_mm']
    for key,r in reports.items():
        if r['status']!='created':continue
        dim=doc.getObject(r['object_name']);value=displayed_text(dim,r)
        matches=[t for t in texts if t['text']==value]
        if not matches:raise RuntimeError(key+': actual native rendered dimension text was not found')
        view=dim.References2D[0][0]
        ax,ay=view.X.Value+dim.X.Value,layout['height_mm']-view.Y.Value-dim.Y.Value
        found=min(matches,key=lambda t:abs((t['bounds_mm']['left']+t['bounds_mm']['right'])/2-ax)+abs((t['bounds_mm']['top']+t['bounds_mm']['bottom'])/2-ay))
        bounds=found['bounds_mm']
        if any(bounds[s]<area[s] for s in ('left','top')) or any(bounds[s]>area[s] for s in ('right','bottom')):
            raise RuntimeError(key+': dimension text is outside the reserved content area')
        own_profile=r.get('candidate',{}).get('kind')=='plane_angle' and r['view_role']=='opening_detail'
        boxes=[box for role,box in paper_boxes.items() if not (own_profile and role==r['view_role'])]
        if any(overlaps(bounds,other) for other in occupied+captions+boxes):
            raise RuntimeError(key+': dimension text collides with another dimension, view or caption')
        if own_profile:
            from fastener_analysis.geometry import App,Part
            x0,x1=bounds['left']-view.X.Value,bounds['right']-view.X.Value
            y0,y1=layout['height_mm']-view.Y.Value-bounds['bottom'],layout['height_mm']-view.Y.Value-bounds['top']
            rect=Part.Face(Part.makePolygon([App.Vector(x,y,0) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0))]))
            if Part.makeCompound(view.getVisibleEdges(True)).common(rect).Length>1e-5:
                raise RuntimeError(key+': localized angular text intersects the actual profile outline')
        occupied.append(bounds)
        checks[key]={**arrow_checks.get(key,{}),'actual_rendered_text':value,'native_text_bounds_top_origin_mm':bounds,'text_no_collision_or_clipping':True,
                     'minimum_checked_gap_mm':1.0,'basis':'Native vector scene text/transforms with installed Qt font metrics; physical paper millimeters',
                     'line_and_arrow_review':'Diameter text checked against native arrow polygons; leaders and hatching still require rendered PDF inspection'}
    return checks
