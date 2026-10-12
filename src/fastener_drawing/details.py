"""Localized, associative source-edge views for crowded opening dimensions."""
from fastener_analysis.geometry import App, Part
from .orientation import native_projected_envelope


def opening_detail_plan(shape, discovery, frames):
    angles = [c for c in discovery['dimension_candidates'] if c['kind'] == 'plane_angle']
    openings = [c for c in discovery['dimension_candidates'] if c['kind'] == 'opening_extent']
    if not angles or not openings:
        return None
    boundaries={tuple(sorted(c['source_edges'])) for c in openings}
    if len(boundaries)!=1:
        return None  # Several openings need explicit view association/review.
    edge_ids = openings[0]['source_edges']
    wire = Part.Wire([shape.Edges[i - 1] for i in edge_ids])
    if not wire.isClosed() or not wire.isValid():
        return None
    # This is a view of the actual terminal boundary, not a sharp polygon
    # reconstructed from its support planes. A native binder keeps association.
    frame = frames['frames']['right_end']
    envelope = native_projected_envelope(wire, frame)
    from .layout import PREFERRED_SCALES
    size=max(envelope['width_mm'],envelope['height_mm'])
    scale=next(s for s in PREFERRED_SCALES if size*s<=70)
    return {'source_edges': edge_ids, 'frame': dict(frame), 'envelope': envelope,
            'scale':scale,'basis': 'Actual terminal opening wire, isolated from geometry visible behind it'}


def make_opening_detail(doc, page, source, plan, position):
    binder = doc.addObject('PartDesign::SubShapeBinder', 'OpeningBoundary')
    binder.Support = [(source, ['Edge' + str(i) for i in plan['source_edges']])]
    binder.Label = 'Associative original opening boundary'
    doc.recompute()
    binder.ViewObject.Visibility = False
    view = doc.addObject('TechDraw::DrawViewPart', 'OpeningDetail')
    view.Source = [binder]
    view.Direction = App.Vector(*plan['frame']['direction'])
    view.XDirection = App.Vector(*plan['frame']['x_direction'])
    view.ScaleType, view.Scale = 'Custom', position['scale']
    view.CoarseView, view.ScrubCount, view.HardHidden = False, 0, False
    view.SmoothVisible, view.SeamVisible = False, False
    view.ViewObject.LineWidth, view.ViewObject.FaceTransparency = .35, 100
    page.addView(view)
    view.X, view.Y = position['x_mm'], position['y_mm']
    return view


def preferred_views(candidate, discovery, views):
    result = list(candidate['preferred_views'])
    if 'opening_detail' not in views:
        return result
    kind = candidate['kind']
    feature = next(f for f in discovery['features'] if f['id'] == candidate['feature_id'])
    if kind in ('plane_angle', 'plane_gap', 'opening_extent') or (kind == 'radius' and feature.get('boundary_side') == 'internal'):
        result.insert(0, 'opening_detail')
    return result
