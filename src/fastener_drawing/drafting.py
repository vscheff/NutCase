"""Native cosmetic centerlines at verified geometric axes, with saved styles."""
from fastener_analysis.geometry import App
from .references import projected_point
from .views import wait_for_views


def centerlines(doc,views,frames,origin):
    records=[]
    for role,view in views.items():
        if role not in ('left_end','right_end','longitudinal','section'):continue
        point=projected_point(view,App.Vector(*origin))
        edges=view.getVisibleEdges(True)
        import Part
        box=Part.makeCompound(edges).BoundBox
        # Cosmetic lines use model-space view coordinates. Keep endpoints
        # within source extents so automated extent dimensions stay geometric.
        halfx=box.XLength/(2*view.Scale)*.95
        halfy=box.YLength/(2*view.Scale)*.95
        lines=[((-halfx,point.y),(halfx,point.y))]
        if role in ('left_end','right_end'):
            lines.append(((point.x,-halfy),(point.x,halfy)))
        for start,end in lines:
            tag=view.makeCosmeticLine(App.Vector(*start,0),App.Vector(*end,0))
            edge=view.getCosmeticEdge(tag)
            edge.Format={'style':3,'weight':.18,'color':(0.,0.,0.,1.),'visible':True}
            records.append({'view':view.Name,'tag':tag,'start_mm':list(start),'end_mm':list(end),'format':edge.Format,
                'basis':'Recovered source axis projected into this native view; endpoints clipped within source envelope'})
        view.CosmeticEdges=list(view.CosmeticEdges)
    wait_for_views(doc,list(views.values()))
    return records


def verify_centerlines(doc,records):
    for row in records:
        view=doc.getObject(row['view'])
        # Native cosmetic UUIDs can be regenerated on restore. Verify actual
        # endpoints/style rather than using a transient tag as identity.
        def matches(edge):
            return all(max(abs(a-b) for a,b in zip(point,expected+[0]))<1e-8 for point,expected in ((edge.Start,row['start_mm']),(edge.End,row['end_mm'])))
        found=[edge for edge in view.CosmeticEdges if matches(edge)]
        if len(found)!=1:raise RuntimeError('Persisted drafting centerline has no unique matching geometry')
        edge=found[0]
        actual,expected=edge.Format,row['format']
        if (actual['style']!=expected['style'] or actual['visible']!=expected['visible']
            or abs(actual['weight']-expected['weight'])>1e-8
            or max(abs(a-b) for a,b in zip(actual['color'],expected['color']))>1e-8):
            raise RuntimeError('Persisted drafting centerline style changed')
        for point,expected in ((edge.Start,row['start_mm']),(edge.End,row['end_mm'])):
            if max(abs(a-b) for a,b in zip(point,expected+[0]))>1e-8:
                raise RuntimeError('Persisted drafting centerline geometry changed')
    return len(records)
