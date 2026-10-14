"""STEP to native TechDraw views and optional verified measured dimensions."""
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastener_analysis.cli import build_report
from fastener_analysis.export import write_json
from fastener_analysis.geometry import App
from fastener_analysis.importer import import_step, sha256
from fastener_paths import ENTRYPOINTS
from .export import export_native, shape_signature, verify_reopen
from .dimensions import create_dimensions, check_text_placement
from .layout import SHEETS, select_layout, comprehensive_layout
from .orientation import native_projected_envelope, view_frame
from .template import make_template
from .views import initialize_gui, make_label, make_view, projected_bounds, wait_for_views

LOG = logging.getLogger("fastener_drawing")


def generate_drawing(path, output_dir, sheet="ANSI-B", isometric=True, opposite_end=True, axis=None, date_text=None, dimensions=False, dimension_scope="comprehensive", configuration=None):
    from .configuration import normalize_metadata_date
    if date_text:
        date_text=normalize_metadata_date(date_text)
    path, output_dir = Path(path).resolve(), Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / path.stem
    report_path = output_dir / (path.stem + ".drawing.json")
    report = {"schema_version": 2, "operation": "native_drawing", "stage": "Measured dimensions" if dimensions else "Undimensioned views", "preliminary": True, "requires_engineering_verification": True,
              "dimensions_requested": dimensions, "dimensions_included": False, "drawing_status": "started", "source": str(path),
              "visual_review": {"status": "pending", "note": "Automated exports do not establish visual correctness; inspect rendered PDF previews."}}
    doc = None
    comprehensive=dimensions and dimension_scope=="comprehensive"
    decisions = None
    if configuration is not None:
        dimensions = comprehensive = True
        report['dimensions_requested'] = True
        sheet = sheet if configuration['sheet']['size']=='auto' else configuration['sheet']['size']
        isometric, opposite_end = configuration['views']['isometric'], configuration['views']['opposite_end']
        axis = configuration['orientation']['axis']
        date_text = normalize_metadata_date(configuration['metadata']['date']) or date_text
    if comprehensive:report.update(operation='comprehensive_dimensioning',stage="Comprehensive feature dimensioning")
    if configuration is not None:
        report.update(operation='configured_dimensioning',stage='Configured '+configuration['dimensioning']['mode']+' feature dimensioning')
    try:
        Gui, TechDrawGui = initialize_gui()
        analysis = build_report(path)
        report["source_analysis"] = analysis
        write_json(report, report_path)
        original, source_metadata = import_step(path)
        if source_metadata["sha256_before"] != analysis["source"]["sha256_before"]:
            raise RuntimeError("Source changed between analysis and drawing import")
        if len(analysis["components"]) != 1:
            raise ValueError("Stage A currently requires one solid; it does not select an arbitrary assembly component")
        if not original.isValid() or not original.isClosed():
            raise ValueError("Imported BRep is open or basically invalid; no reliable native projection is claimed")
        geometry = analysis["components"][0]["geometry"]
        frames = view_frame(geometry, axis, configuration['orientation']['up'] if configuration else None)
        discovery=analysis["components"][0]["feature_discovery"]
        if configuration is not None:
            from .configuration import make_catalog, bind_config, selection_decisions
            catalog=make_catalog(discovery,shape_signature(original),source_metadata['sha256_before'])
            write_json(catalog,output_dir/(path.stem+'.catalog.json'))
            configuration=bind_config(configuration,catalog)
            decisions=selection_decisions(configuration,discovery)
            report.update(configuration=configuration,source_candidate_catalog=catalog,dimension_selection=decisions)
            write_json(configuration,output_dir/(path.stem+'.config.json'))
        roles = ["longitudinal", "right_end"]
        if opposite_end:
            roles.append("left_end")
        if isometric:
            roles.append("isometric")
        envelopes = {role: native_projected_envelope(original, frames["frames"][role]) for role in roles}
        if comprehensive and (configuration is None or configuration['views']['section']):
            from .sections import section_geometry,make_section
            try:
                if not discovery.get('axis'):raise ValueError('Automatic section omitted: feature-analysis axis unresolved; view override does not classify features')
                cut,report["section_diagnostics"]=section_geometry(original,frames,discovery["axis"]["origin_mm"])
                report["section_diagnostics"].update(origin_mm=discovery["axis"]["origin_mm"],normal=frames["front_normal"],
                    direction="Aligned",symbol="A",hatch_name="Diagonal4",hatch_scale=.6)
                report["section_diagnostics"]["hatching"]={"status":"pending_native_render_check",
                    "reason":"Native section-face conversion may fail; final exported hatch strokes and rendered PDF require verification",
                    "original_geometry_unchanged":True}
                frames["frames"]["section"]=dict(frames["frames"]["longitudinal"])
                envelopes["section"]=native_projected_envelope(cut,frames["frames"]["section"])
            except (RuntimeError,ValueError) as exc:
                report["section_diagnostics"]={"status":"unresolved","reason":str(exc),"external_views_preserved":True}
        if comprehensive and (configuration is None or configuration['views']['opening_detail']):
            from .details import opening_detail_plan
            detail=opening_detail_plan(original,discovery,frames)
            if detail:
                frames['frames']['opening_detail']=detail['frame']
                envelopes['opening_detail']={**detail['envelope'],'detail_scale':detail['scale']}
                report['opening_detail']=detail
        layout = comprehensive_layout(envelopes,discovery,sheet,
            requested_scale=None if configuration is None or configuration['scale']=='auto' else configuration['scale'],
            automatic_sheet=configuration is None or configuration['sheet']['size']=='auto', decisions=decisions) if comprehensive else select_layout(envelopes, sheet, dimensions)
        date_text = date_text or datetime.now(ZoneInfo("America/New_York")).date().isoformat()
        report.update(orientation=frames, native_source_envelopes=envelopes, layout=layout,
                      generated_date=date_text, generated_date_timezone="America/New_York")
        template_path = output_dir / (path.stem + ".template.svg")
        make_template(template_path, layout, path.name, date_text, analysis["validation"]["boolean_check"]["status"] != "passed", dimensions,
                      configuration['metadata'] if configuration else None)
        doc = App.newDocument("FastenerDrawing")
        doc.Label = path.stem + " - Preliminary Drawing"
        source = doc.addObject("Part::Feature", "OriginalSTEP")
        source.Label = "Original STEP (unmodified BRep)"
        source.Shape = original
        source.ViewObject.Visibility = False
        source.addProperty("App::PropertyString", "InputFile", "Provenance").InputFile = str(path)
        source.addProperty("App::PropertyString", "SourceSHA256", "Provenance").SourceSHA256 = source_metadata["sha256_before"]
        source.setEditorMode("InputFile", 1)
        source.setEditorMode("SourceSHA256", 1)
        signature = shape_signature(original)
        if shape_signature(source.Shape) != signature:
            raise RuntimeError("Native document assignment altered the imported BRep")
        page = doc.addObject("TechDraw::DrawPage", "DrawingPage")
        page.Label = "Preliminary - Third Angle"
        page.ProjectionType = "Third angle"
        page.Scale = layout["scale"]
        page.KeepUpdated = True
        page.ViewObject.ShowFrames = False
        template = doc.addObject("TechDraw::DrawSVGTemplate", "DrawingTemplate")
        template.Template = str(template_path)
        page.Template = template
        page.addProperty("App::PropertyString", "ValidationDiagnosticsJSON", "Provenance").ValidationDiagnosticsJSON = json.dumps(analysis["validation"])
        page.addProperty("App::PropertyString", "DrawingOrientationJSON", "Provenance").DrawingOrientationJSON = json.dumps(frames)
        page.addProperty("App::PropertyString", "SourceBRepSignatureJSON", "Provenance").SourceBRepSignatureJSON = json.dumps(signature)
        stage_text = "Comprehensive measured STEP dimensions" if comprehensive else "Measured STEP dimensions" if dimensions else "Undimensioned STEP views"
        if configuration is not None:stage_text=configuration['dimensioning']['mode'].title()+' measured STEP dimensions'
        page.addProperty("App::PropertyString", "DrawingStage", "Provenance").DrawingStage = stage_text + "; requires engineering verification"
        page.addProperty("App::PropertyString", "DrawingUnits", "Provenance").DrawingUnits = "mm"
        if configuration is not None:
            page.addProperty('App::PropertyString','DrawingConfigurationJSON','Provenance').DrawingConfigurationJSON=json.dumps(configuration)
        views = {role: make_view(doc, page, source, role, frames["frames"][role], layout["positions"][role]) for role in roles}
        if comprehensive and "section" in envelopes:
            try:
                views["section"]=make_section(doc,page,source,views["right_end"],frames,discovery["axis"]["origin_mm"],layout["positions"]["section"])
                roles.append("section")
            except (RuntimeError,ValueError) as exc:
                if doc.getObject("Section"):doc.removeObject("Section")
                layout["positions"].pop("section")
                report["section_diagnostics"].update(status="unresolved",reason=str(exc),external_views_preserved=True)
        if comprehensive and report.get('opening_detail'):
            from .details import make_opening_detail
            views['opening_detail']=make_opening_detail(doc,page,source,detail,layout['positions']['opening_detail'])
            roles.append('opening_detail')
        for role in roles:
            label=make_label(doc, page, role, layout["positions"][role])
            if role=="section":label.Text=["AXIAL CUT A-A (UNHATCHED)"]
        page.ViewObject.show()
        wait_for_views(doc, list(views.values()))
        checks = {}
        paper_boxes = {}
        for role, view in views.items():
            bounds = projected_bounds(view)
            expected = layout["positions"][role]
            if abs(view.X.Value - expected["x_mm"]) > 1e-8 or abs(view.Y.Value - expected["y_mm"]) > 1e-8:
                raise RuntimeError(f"{role}: native page placement differs from the planned layout")
            # Numerical projection consistency threshold, never a manufacturing tolerance.
            epsilon = max(1e-4, max(envelopes[role]["width_mm"], envelopes[role]["height_mm"]) * 1e-5) * view.Scale
            differences = {dimension: abs(bounds[dimension] - expected["expected_" + dimension]) for dimension in ("width_mm", "height_mm")}
            if max(differences.values()) > epsilon:
                raise RuntimeError(f"{role}: native projection envelope differs from the source BRep: {differences}; numerical threshold {epsilon} mm")
            paper_box = {"left": view.X.Value + bounds["minimum_mm"][0], "right": view.X.Value + bounds["maximum_mm"][0],
                         "top": layout["height_mm"] - view.Y.Value - bounds["maximum_mm"][1],
                         "bottom": layout["height_mm"] - view.Y.Value - bounds["minimum_mm"][1]}
            area = layout["content_area_top_origin_mm"]
            if any(paper_box[side] < area[side] - epsilon for side in ("left", "top")) or any(paper_box[side] > area[side] + epsilon for side in ("right", "bottom")):
                raise RuntimeError(f"{role}: projection lies outside the drawing content region")
            for other_role, other in paper_boxes.items():
                if min(paper_box["right"], other["right"]) > max(paper_box["left"], other["left"]) and min(paper_box["bottom"], other["bottom"]) > max(paper_box["top"], other["top"]):
                    raise RuntimeError(f"{role} overlaps {other_role} on the native sheet")
            paper_boxes[role] = paper_box
            checks[role] = {**bounds, "extent_difference_mm": differences, "numerical_check_threshold_mm": epsilon,
                           "page_position_verified_mm": [view.X.Value, view.Y.Value],
                           "paper_bounding_box_top_origin_mm": paper_box, "no_overlap_or_clipping": True,
                           "projection_matches_source_extents": True, "coarse_view": view.CoarseView,
                           "hlr_scrub_count": view.ScrubCount, "hidden_lines_enabled": view.HardHidden}
            LOG.info("%s: %d visible / %d hidden native edges; %.3f x %.3f mm on paper", role, bounds["visible_edge_count"], bounds["hidden_edge_count"], bounds["width_mm"], bounds["height_mm"])
        report["projection_checks"] = checks
        if comprehensive and discovery.get('axis'):
            from .drafting import centerlines
            report['drafting_centerlines']=centerlines(doc,views,frames,discovery['axis']['origin_mm'])
            page.addProperty('App::PropertyString','DraftingCenterlinesJSON','Provenance').DraftingCenterlinesJSON=json.dumps(report['drafting_centerlines'])
            report['drafting_conventions']={'native_centerlines':'Black native cosmetic centerlines at the recovered geometric axis',
                'detail_profile':'Actual source opening boundary; support-plane angles are geometric, not manufacturing specifications',
                'dimension_text_size_mm':3.5,'main_arrow_size_mm':2.5,'angular_arrow_size_mm':2.0}
        dimension_reports = {}
        if dimensions:
            if comprehensive:
                from .comprehensive import create
                dimension_reports=create(doc,page,source,views,discovery,layout,decisions)
                report["dimensions"]=dimension_reports
                write_json(report,report_path)
                # Persist geometry/references before invoking a fresh native GUI
                # host. This installation retains stale Qt page groups when a
                # large dimensioned page is closed/reopened in its creator host.
                import subprocess,sys
                staging=output_dir/(path.stem+'.layout-staging.FCStd')
                preferences=App.ParamGet('User parameter:BaseApp/Preferences/Document')
                thumbnail=preferences.GetBool('SaveThumbnail',True)
                preferences.SetBool('SaveThumbnail',False)
                try:doc.saveAs(str(staging))
                finally:preferences.SetBool('SaveThumbnail',thumbnail)
                App.closeDocument(doc.Name);doc=None
                report.update(staging_project=str(staging),destination=str(destination),imported_brep_signature=signature)
                plan=output_dir/(path.stem+'.finishing-plan.json')
                write_json(report,plan)
                worker=ENTRYPOINTS/'finish_drawing.py'
                completed=subprocess.run([sys.executable,str(worker),str(plan)],capture_output=True,text=True,
                    timeout=240,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (output_dir/(path.stem+'.finishing.log')).write_text(completed.stdout+completed.stderr,encoding='utf-8')
                if completed.returncode!=0:
                    failure=completed.stderr[-3000:]
                    if 'Layout requires a larger sheet or additional view' in failure and layout['sheet'] in ('ANSI-B','ANSI-C') and (configuration is None or configuration['sheet']['size']=='auto'):
                        larger='ANSI-C' if layout['sheet']=='ANSI-B' else 'ANSI-D'
                        LOG.warning('Retaining dimensions and retrying presentation on %s',larger)
                        result=generate_drawing(path,output_dir,larger,isometric,opposite_end,axis,date_text,dimensions,dimension_scope,configuration)
                        result['layout'].update(requested_sheet=sheet,automatic_sheet_enlargement=True,
                            presentation_retry_reason=failure,dimension_removal_for_layout=False)
                        write_json(result,report_path)
                        return result
                    raise RuntimeError('Native finishing host failed: '+failure)
                return json.loads(report_path.read_text(encoding='utf-8'))
            else:
                dimension_reports = create_dimensions(doc, page, source, views, geometry,
                    analysis["components"][0]["recognition"], frames, layout)
            report["dimensions"] = dimension_reports
            report["dimensions_included"] = any(d["status"] == "created" for d in dimension_reports.values())
            report["unresolved_dimensions"] = [k for k, d in dimension_reports.items() if d["status"] == "unresolved"]
            page.addProperty("App::PropertyString", "DimensionVerificationJSON", "Provenance").DimensionVerificationJSON = json.dumps(dimension_reports)
        report["imported_brep_signature"] = signature
        export_doc = doc
        doc = None
        report["exports"] = export_native(export_doc, page, destination, TechDrawGui)
        if dimensions and not comprehensive:
            reopened = App.openDocument(report["exports"]["project"])
            try:
                wait_for_views(reopened,[v for v in reopened.DrawingPage.Views if v.isDerivedFrom("TechDraw::DrawViewPart")])
                from .dimensions import verify_dimensions
                verify_dimensions(reopened,dimension_reports)
                report["dimension_placement_checks"] = check_text_placement(reopened, dimension_reports, layout, paper_boxes, report["exports"]["rendered_svg"])
            finally:
                App.closeDocument(reopened.Name)
        report["native_render_checks"] = report["exports"]["native_render_checks"]
        report["reopen_checks"] = verify_reopen(report["exports"]["project"], signature, layout["scale"], len(views), layout, frames, dimension_reports)
        if sha256(path) != source_metadata["sha256_before"]:
            raise RuntimeError("Source STEP hash changed during drawing generation")
        report["source_sha256_verified_unchanged"] = True
        report["drawing_status"] = "generated_pending_visual_review"
        report["geometry_requires_review"] = analysis["validation"]["status"] != "passed"
        write_json(report, report_path)
        LOG.info("Saved editable project and PDF; scale %s; visual inspection still required", layout["scale_label"])
        return report
    except Exception as exc:
        report["drawing_status"] = "failed"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        write_json(report, report_path)
        raise
    finally:
        if doc is not None:
            App.closeDocument(doc.Name)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Original STEP BRep to native TechDraw sheet, optional measured dimensions, FCStd and PDF")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--sheet-size", choices=SHEETS, default="ANSI-B")
    parser.add_argument("--isometric", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--opposite-end", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dimensions", action="store_true", help="Add independently verified native geometric dimensions")
    parser.add_argument("--dimension-scope",choices=("basic","comprehensive"),default="comprehensive",help="General feature dimensions by default; basic preserves the reviewed four-dimension Stage B output")
    parser.add_argument("--axis", type=float, nargs=3, metavar=("X", "Y", "Z"), help="Explicit reviewed axis override")
    parser.add_argument("--date", help="Generated date override, YYYY-MM-DD or MM/dd/yyyy")
    parser.add_argument('--config',type=Path,help='Drawing JSON policy; source selection remains independently verified')
    args = parser.parse_args(argv)
    if args.axis and sum(value * value for value in args.axis) <= 1e-20:
        parser.error("--axis must be a nonzero direction vector")
    if args.date:
        try:
            from .configuration import normalize_metadata_date
            args.date=normalize_metadata_date(args.date)
        except ValueError as error:
            parser.error(str(error))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    handler = logging.FileHandler(args.output_dir / (args.input.stem + ".drawing.log"), mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    try:
        from .configuration import read_config
        config=read_config(args.config) if args.config else None
        report = generate_drawing(args.input, args.output_dir, args.sheet_size, args.isometric, args.opposite_end, args.axis, args.date, args.dimensions,args.dimension_scope,config)
        manual_section=report.get("section_diagnostics",{}).get("hatching",{}).get("status")=="requires_manual_completion"
        return 2 if report["geometry_requires_review"] or report.get("unresolved_dimensions") or manual_section else 0
    except Exception as exc:
        LOG.exception("Drawing failed: %s", exc)
        return 1
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
