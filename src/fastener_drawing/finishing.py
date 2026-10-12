"""Finish a persisted drawing in a fresh GUI host, avoiding stale Qt page groups."""
import json
from pathlib import Path

from fastener_analysis.geometry import App
from fastener_analysis.export import write_json
from fastener_analysis.importer import sha256
from .views import initialize_gui,wait_for_views
from .dimensions import verify_dimensions
from .comprehensive import settle_placement
from .selection import Selection,coverage,write_summary
from .export import export_native,verify_reopen


def finish(plan_path):
    plan_path=Path(plan_path)
    report=json.loads(plan_path.read_text(encoding="utf-8"))
    Gui,TechDrawGui=initialize_gui()
    doc=App.openDocument(report.pop("staging_project"))
    destination=Path(report.pop("destination"))
    layout,frames=report["layout"],report["orientation"]
    reports=report["dimensions"]
    discovery=report["phase1_analysis"]["components"][0]["feature_discovery"]
    page=doc.DrawingPage;page.ViewObject.show()
    views={r:doc.getObject(r.title().replace("_","")) for r in layout["positions"]}
    wait_for_views(doc,list(views.values()))
    Gui.updateGui()
    TechDrawGui.exportPageAsSvg(page,str(destination)+".placement-scene.svg")
    if "section" in views:
        from .sections import rendered_hatching
        section_render_parameters={"x_mm":views["section"].X.Value,"y_mm":views["section"].Y.Value,
                                   "weight_mm":float(views["section"].ViewObject.WeightPattern)}
        hatching=rendered_hatching(str(destination)+".placement-scene.svg",views["section"])
        if hatching['status']=='native_hatch_strokes_rendered':
            from .section_material import native_hatch_material
            material=native_hatch_material(str(destination)+'.placement-scene.svg',views['section'])
            hatching['material_validation']=material
            if not material['solid_material_verified']:
                views['section'].ViewObject.HatchCutSurface=False
                hatching.update(status='requires_manual_completion',reason='Native hatch did not pass original-solid material validation')
        if hatching['status']=='requires_manual_completion':
            from .section_material import add_verified_overlay
            try:
                overlay,verified=add_verified_overlay(doc,page,views['section'],frames,report['section_diagnostics']['origin_mm'])
                verified['native_section_failure']=hatching
                report['section_diagnostics']['native_hatching']=hatching
                hatching=verified
                section_render_parameters={'x_mm':overlay.X.Value,'y_mm':overlay.Y.Value,'weight_mm':.18}
            except (RuntimeError,ValueError) as exc:
                hatching['fallback_refused_reason']=str(exc)
        report["section_diagnostics"]["hatching"]=hatching
        doc.SectionLabel.Text=["AXIAL CUT A-A (UNHATCHED)" if hatching["status"]=="requires_manual_completion" else "SECTION A-A"]
    # Retain failed references only until the live scene has been measured.
    # Removing a datum can invalidate initial Qt parent groups in this FreeCAD.
    removals=[]
    for key,r in reports.items():
        if r["status"]!="created":continue
        try:verify_dimensions(doc,{key:r},check_count=False)
        except (RuntimeError,ValueError) as exc:
            r.update(status="unresolved",reason="Native save/reopen associativity check failed: "+str(exc))
            removals.append(r["object_name"])
    boxes={r:c["paper_bounding_box_top_origin_mm"] for r,c in report["projection_checks"].items()}
    Gui.updateGui()
    TechDrawGui.exportPageAsSvg(page,str(destination)+".placement-scene.svg")
    report["dimension_placement_checks"]=settle_placement(doc,reports,layout,boxes,views)
    for name in removals:
        if doc.getObject(name):doc.removeObject(name)
    retained=Selection(discovery)
    for r in reports.values():
        if r["status"]=="created":retained.accept(r["candidate"])
    for r in reports.values():
        if r["status"]=="omitted_redundant" and not retained.reason(r["candidate"]):
            r.update(status="unresolved",reason="A dimension needed to justify redundancy did not survive validation/placement")
    report["dimensional_coverage"]=coverage(discovery,reports)
    report["dimensions_included"]=any(r["status"]=="created" for r in reports.values())
    report["unresolved_dimensions"]=[k for k,r in reports.items() if r["status"]=="unresolved"]
    page.addProperty("App::PropertyString","DimensionVerificationJSON","Provenance").DimensionVerificationJSON=json.dumps(reports)
    page.addProperty("App::PropertyString","DimensionalCoverageJSON","Provenance").DimensionalCoverageJSON=json.dumps(report["dimensional_coverage"])
    page.addProperty("App::PropertyString","DrawingLayoutJSON","Provenance").DrawingLayoutJSON=json.dumps(layout)
    if report.get('opening_detail'):
        report.setdefault('section_diagnostics',{})['opening_detail_source_edges']=report['opening_detail']['source_edges']
    page.addProperty("App::PropertyString","DrawingSectionJSON","Provenance").DrawingSectionJSON=json.dumps(report.get("section_diagnostics",{}))
    report["exports"]=export_native(doc,page,destination,TechDrawGui)
    report["native_render_checks"]=report["exports"]["native_render_checks"]
    if "section" in views:
        final_hatching=rendered_hatching(report["exports"]["rendered_svg"],section_render_parameters)
        previous=report['section_diagnostics']['hatching']
        expected_render='native_hatch_strokes_rendered' if previous['status']=='verified_geometry_hatch_rendered' else previous['status']
        if final_hatching["status"]!=expected_render:
            raise RuntimeError("Native hatch rendering changed during save/reopen; no stable final section claimed")
        previous['final_native_diagonal_stroke_count']=final_hatching['native_diagonal_stroke_count']
        if previous['status']=='native_hatch_strokes_rendered':
            saved=App.openDocument(report['exports']['project'])
            try:
                wait_for_views(saved,[saved.Section])
                previous['final_material_validation']=native_hatch_material(report['exports']['rendered_svg'],saved.Section)
                if not previous['final_material_validation']['solid_material_verified']:
                    raise RuntimeError('Final native hatch material validation failed')
            finally:App.closeDocument(saved.Name)
    report["reopen_checks"]=verify_reopen(report["exports"]["project"],report["imported_brep_signature"],layout["scale"],len(views),layout,frames,reports)
    if sha256(report["source"])!=report["phase1_analysis"]["source"]["sha256_before"]:
        raise RuntimeError("Original STEP source changed during drawing generation")
    report.update(source_sha256_verified_unchanged=True,drawing_status="generated_pending_visual_review",
                  geometry_requires_review=report["phase1_analysis"]["validation"]["status"]!="passed",
                  execution_host="Native FreeCAD bundled Python; separate fresh GUI host for persisted layout validation")
    write_summary(Path(str(destination)+".coverage.md"),report)
    write_json(report["phase1_analysis"],Path(str(destination)+".analysis.json"))
    write_json(report,Path(str(destination)+".drawing.json"))
