"""New regression controls adapted from the retained native diameter probe.

Proves physical clearance and actual native glyph output at different scales.
"""
import json
import os
import unittest
from pathlib import Path
import FreeCAD as App
import Part
from fastener_drawing.views import initialize_gui, wait_for_views
from fastener_drawing.dimensions import set_presentation, presentation_record
from fastener_drawing.references import inventory
from fastener_drawing.svg_placement import arrow_bounds, diameter_arrow_checks, ArrowTextCollision
from fastener_drawing.comprehensive import settle_placement
from fastener_drawing.template import make_template
from fastener_drawing.export import shape_signature, compare_signatures


class NativePresentationTests(unittest.TestCase):
    def test_diameter_text_arrow_clearance_rounding_and_native_reopen(self):
        Gui, TD = initialize_gui()
        directory=Path(os.environ['NUTCASE_TEST_RESULTS']); directory.mkdir(parents=True,exist_ok=True)
        template=directory/'native-control-template.svg'
        layout={'width_mm':431.8,'height_mm':279.4,'sheet':'ANSI-B','scale_label':'Fixture',
                'content_area_top_origin_mm':{'left':15,'right':415,'top':25,'bottom':190},
                'positions':{'right_end':{'x_mm':200,'y_mm':140}}}
        make_template(template,layout,'Independent native cylinder','2026-10-13',False)
        evidence=[]
        for diameter,scale in [(4,2),(9.5,1),(9.5,2),(9.6,2),(20,2),(9.5,5),(9.56789,2)]:
            with self.subTest(diameter=diameter,scale=scale):
                doc=App.newDocument('ArrowFixture')
                try:
                    source=doc.addObject('PartDesign::Feature','Cylinder');source.Shape=Part.makeCylinder(diameter/2,8)
                    original=shape_signature(source.Shape)
                    page=doc.addObject('TechDraw::DrawPage','DrawingPage');page.Scale=scale
                    svg=doc.addObject('TechDraw::DrawSVGTemplate','Template');svg.Template=str(template);page.Template=svg
                    view=doc.addObject('TechDraw::DrawViewPart','RightEnd');view.Source=[source]
                    view.Direction=App.Vector(0,0,1);view.X=200;view.Y=140;page.addView(view);page.ViewObject.show()
                    wait_for_views(doc,[view])
                    circles=[e for e in inventory(view) if isinstance(e['edge'].Curve,Part.Circle)
                             and abs(e['edge'].Curve.Radius-diameter/2)<1e-8]
                    self.assertTrue(circles)
                    dim=doc.addObject('TechDraw::DrawViewDimension','Diameter');dim.Type='Diameter'
                    dim.MeasureType='Projected';dim.References2D=[(view,[circles[0]['name']])];page.addView(dim)
                    set_presentation(dim,'flange_diameter');dim.X=0;dim.Y=diameter*scale/2+16
                    wait_for_views(doc,[view])
                    record={'status':'created','object_name':dim.Name,'format_spec':dim.FormatSpec,'view_role':'right_end',
                            'candidate':{'kind':'diameter','units':'mm'},'presentation':presentation_record(dim),
                            'position_relative_to_view_mm':[dim.X.Value,dim.Y.Value]}
                    reports={'fixture':record}; native_svg=directory/'native-control.svg'
                    TD.exportPageAsSvg(page,str(native_svg))
                    self.assertEqual(len(arrow_bounds(native_svg)),2)
                    baseline_collision=False
                    try:diameter_arrow_checks(doc,reports,native_svg)
                    except ArrowTextCollision:baseline_collision=True
                    checked=settle_placement(doc,reports,layout,{}, {'right_end':view})
                    self.assertTrue(checked['fixture']['arrow_text_clearance_verified'])
                    self.assertAlmostEqual(dim.getRawValue(),diameter,places=8)
                    self.assertTrue(compare_signatures(original,shape_signature(source.Shape))['geometry_equivalent'])
                    project=directory/f'arrow-{diameter}-{scale}.FCStd'; doc.saveAs(str(project))
                    App.closeDocument(doc.Name); doc=None
                    reopened=App.openDocument(str(project))
                    try:
                        reopened.DrawingPage.ViewObject.show();wait_for_views(reopened,[reopened.RightEnd])
                        TD.exportPageAsSvg(reopened.DrawingPage,str(native_svg))
                        proof=diameter_arrow_checks(reopened,reports,native_svg)
                        self.assertTrue(proof['fixture']['arrow_text_clearance_verified'])
                        self.assertAlmostEqual(reopened.Diameter.getRawValue(),diameter,places=8)
                        if diameter==9.5 and scale==2:
                            annotation=reopened.addObject('TechDraw::DrawViewAnnotation','OrdinaryText')
                            annotation.Text=['ORDINARY TEXT'];annotation.X=200;annotation.Y=230
                            annotation.TextSize=3.5;reopened.DrawingPage.addView(annotation)
                            wait_for_views(reopened,[reopened.RightEnd])
                            reopened.save()
                            TD.exportPageAsPdf(reopened.DrawingPage,str(directory/'native-control.pdf'))
                            # Actual native Unicode control is consumed by external PDF tests.
                            (directory/'native-control.report.json').write_text(json.dumps({'layout':layout,
                                'native_render_checks':{'actual_dimension_labels':['⌀ 9.5','ORDINARY TEXT']}}),encoding='utf-8')
                    finally:App.closeDocument(reopened.Name)
                    evidence.append({'diameter_mm':diameter,'scale':scale,'baseline_collision':baseline_collision,
                                     'actual_native_clearance':proof,'format_spec':record['format_spec']})
                finally:
                    if doc is not None:App.closeDocument(doc.Name)
        self.assertTrue(any(row['baseline_collision'] for row in evidence))
        (directory/'diameter-clearance.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
