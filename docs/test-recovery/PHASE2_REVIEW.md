# Phase 2 Stage A review - October 9, 2026

> Historical review: the requested directory cleanup removed archived development outputs, regression suites, synthetic fixtures and investigation scripts. Artifact paths and test commands below record earlier work; they are not all present in this runtime-focused directory. Current usage is in README.md; preservation and post-cleanup checks are in [docs/CLEANUP.md](docs/CLEANUP.md).

**Stage A is implemented and was executed against both supplied STEP files.** Each produced an editable native FreeCAD project and a one-page vector PDF, with four undimensioned views. Both final PDFs were rendered and visually inspected with Poppler and independently with PDFium. Both saved projects were reopened through the installed FreeCAD API and checked. Stage B dimensioning has not been implemented; it awaits review of these sheets.

These are preliminary drawing-generation results, not engineering approval of the parts or their source BReps. The original extended Boolean failures remain unresolved. The earlier [Phase 1 review](PHASE1_REVIEW.md) remains a historical record; its statement that Phase 2 was not yet implemented describes that earlier stage.

## Delivered sheets

| Result | FC00AAB09748 sample | FC00AAB13125 sample |
| --- | --- | --- |
| Source file | `FC00AAB09748_003-NUT_RIVET HEX.DRIVE; refset Entire Part.stp` | `FC00AAB13125_002.0006-NUT_SPRG._U_1THD - _U_ SHAPED; refset Entire Part.stp` |
| Sheet | ANSI B landscape, 431.8 x 279.4 mm | ANSI B landscape, 431.8 x 279.4 mm |
| Projection / scale | Third angle / 3:1 for every view | Third angle / 3:1 for every view |
| Native drawing views | Longitudinal, right end, left end, isometric | Longitudinal, right end, left end, isometric |
| Native dimensions | **0** | **0** |
| Editable project reopen | Passed | Passed |
| Source STEP hash unchanged | Confirmed | Confirmed |
| Basic validity / detailed BRep check | Passed / passed | Passed / passed |
| Extended Boolean diagnostic entries | **55; failed** | **72; failed** |
| Final PDF visual review | Passed for Stage A layout/readability | Passed for Stage A layout/readability |

Output files under `output/` retain each complete source stem, with `.FCStd`, `.pdf`, `.template.svg`, `.drawing.json` and `.drawing.log` suffixes. The two preview pairs are `preview_09748.png` / `preview_09748_pdfium.png` and `preview_13125.png` / `preview_13125_pdfium.png`. Reports record the inspected artifact hashes, so a later generation cannot silently inherit this visual review.

Each sheet contains a conventional border, lower-right editable title block, source filename, generated date, scale, millimeter units, third-angle symbol and an explicit preliminary engineering-verification designation. No revision, material, finish, tolerance, GD&T, thread specification or fabricated part description was assigned. The generic title is “IMPORTED STEP GEOMETRY.”

## Native geometry and orientation

Phase 1's code was preserved. The new drawing modules call its importer and analyzer and retain the complete results. Drawing generation requires one basically valid closed solid and an identified or explicitly reviewed axis. It does not require successful head/shank/thread recognition and does not reject a solid solely because its extended Boolean check fails.

The original imported BRep is assigned to `OriginalSTEP` at its original placement. No healing, refinement, rescaling or feature replacement is applied. That feature is the direct `Source` of every native `TechDraw::DrawViewPart`. The project embeds its SVG template and source BRep, along with validation diagnostics, orientation and source-signature provenance. The original STEP and external SVG are not required to reopen the saved sheet.

Both recovered axes are oblique to global XYZ. The drawing points the positive axis toward the supported terminal circular enlargement and uses an actual external hex supporting-plane normal to establish roll. This selects a useful viewing orientation without assigning a head function. The longitudinal axis is horizontal on paper. Right and left end views have explicit right-handed frames and retain the same vertical direction; their positions follow third-angle convention. The isometric direction is equally inclined to the three orthogonal model-frame directions, with no perspective.

For rotationally symmetric or unresolved radial geometry, roll is deterministic rather than a claimed engineering orientation. The chosen basis is recorded in JSON. Axis ambiguity produces a failure report unless an explicit reviewed `--axis X Y Z` is supplied. The tool never substitutes global Z because axis recognition failed.

Native BRep extrema, measured in rigidly transformed copies, determine projected envelopes for scale/layout only. Those copies do not replace the drawing source. TechDraw performs the actual hidden-line projection. `CoarseView=False`, `Perspective=False` and `ScrubCount=0` avoid a coarse mesh projection or automatic edge scrubbing. Orthographic views enable hidden hard edges to show the bore and occluded exterior details. Hidden lines are omitted in the isometric reference view.

## Projection checks and source defects

Each view's native visible-edge envelope was compared with independently measured BRep extrema in its viewing frame, at the selected scale. Actual page positions were checked after view creation, and page-space boxes were checked for overlap and clipping. These catch gross projection/layout errors; they do not prove every internal curve correct.

| Native HLR result: visible / hidden edges | FC00AAB09748 | FC00AAB13125 |
| --- | ---: | ---: |
| Longitudinal | 33 / 33 | 48 / 85 |
| Right end | 3 / 31 | 20 / 94 |
| Left end | 32 / 20 | 72 / 69 |
| Isometric | 32 / 0 | 54 / 0 |

These are projected edge counts, not counts of original faces or distinct defects. Seam and smooth edges are suppressed deliberately for readable linework; no dimensions depend on projected edge naming in Stage A.

The longitudinal paper envelopes are approximately **48.72 x 60.00 mm** and **56.70 x 66.00 mm**, corresponding to the original **16.24 / 18.90 mm** axial extents and **20 / 22 mm** circular enlargement diameters at 3:1. The largest observed projected-width/height differences from the native source envelopes were about **2.0e-7 mm** and **6.9e-6 mm on paper**, respectively. The check threshold is a numerical QA setting, not a manufacturing tolerance or a source-accuracy guarantee.

Both TechDraw HLR operations completed with nonempty, up-to-date native edge sets. No fallback or approximation was required. Visual inspection showed the circular enlargement, exterior hex region, bore and shaped body details; the denser second model retained its additional projected curves. End views differ in visible/hidden linework as expected when looking from opposite sides. Longitudinal and end views align, and the isometric references explain the body shape. No clipped views, overlapping views/captions, missing title block, unreadable source filename or mirrored viewing frame was found in the final sheets.

The **55** and **72** original Boolean diagnostics are preserved verbatim and summarized in the drawing JSON and native project. The sheets explicitly say that the extended Boolean check failed and geometry needs review. The first source has 13 `GeomAbs_C0` entries and 21 edge / 21 face `InvalidCurveOnSurface` entries; the second has 16 and 28 / 28. These entries do not identify stable defective edge/face indices through the installed API, so this run cannot attribute a particular projection curve to a particular diagnostic. The maximum imported BRep tolerances remain approximately **0.001184396 mm** and **0.020144728 mm**. Those are kernel metadata, not assigned engineering tolerances.

**Observed conclusion:** the source defects did not prevent these native projections or cause an identified visible layout/completeness failure. They remain a reason for engineering review. This does not establish that every curve-on-surface inconsistency is harmless, that the solids are suitable for Boolean modeling, or that downstream dimension references will be reliable.

## Export and roundtrip verification

Native PDF export uses `TechDrawGui.exportPageAsPdf`. The installed FreeCAD 1.1.4 / Python 3.11.14 / OCC 7.8.1 runtime required an actual GUI-backed page even for batch export. `setupWithoutGUI()` alone projected geometry but did not produce a PDF. The implemented entry point creates an offscreen Qt application, initializes a hidden FreeCAD GUI, shows the drawing page internally and processes events until HLR finishes. The batch process uses project-local preferences/cache, leaving existing user sessions alone.

The FCStd archive was checked for its embedded template, then closed and reopened in FreeCAD. Reopen verification checks:

- Source topology/types/counts, BRep extrema, area/volume, native UV bounds, nine native surface probes per face and five curve probes per edge.
- Four native source-linked views, their direction and horizontal vectors, positions and caption positions.
- Shared page scale, third-angle convention, millimeter units, retained diagnostics and zero dimension objects.
- Original STEP SHA-256 before and after generation.

Assigning the imported source to the native document preserved its serialized BRep signature exactly in memory. Saving/reopening changed serialization details, including added identity locations and last-place floating-point representations. The BRep serialization hashes therefore differ after persistence; they are not falsely reported as byte-identical. Native geometry comparisons passed with maximum numeric deviations of **1.1369e-12** and **9.0949e-13** across the compared quantities. The comparison threshold is **1e-8 in native numeric values**, not an engineering tolerance. Sampled native probes supplement topology/aggregate checks; they are not a formal proof of equality for every point on a freeform surface.

Both PDFs pass a strict pypdf read, contain one page with a **1224 x 792 point MediaBox** (17 x 11 inches), and have zero image XObjects. They retain native vector drawing content. `output/pdf_validation.json` records these checks and final PDF hashes.

Poppler renders both pages but emits **15 “No current point in closepath” syntax warnings per PDF** on this FreeCAD/Qt export. Independent PDFium rendering succeeded, and both sets of renders were inspected without missing linework, text or title-block content. The native PDFs were not rewritten to suppress warnings. Compatibility with every viewer/printer is not established. Native template text is partly exported as vector outlines, so text extraction alone does not verify title-block content or provide fully searchable title text.

Offscreen Qt reports unsupported OpenGL-widget/keyboard messages in the run logs. A 3D OpenGL thumbnail is unnecessary for native vector drawing export and is disabled during save. A normal visible desktop session and physical printer were not exercised; the actual native project reopen and rendered PDF review are the validation performed here.

## Regression tests actually executed

```powershell
& 'C:\Program Files\FreeCAD 1.1\bin\python.exe' -m unittest discover -s tests -v
```

**37 tests passed in 28.064 seconds**, recorded in `output/test_results_phase2.txt`. This includes all 22 unchanged Phase 1 tests and 15 new Stage A tests. Native drawing integration tests launch real FreeCAD Python subprocesses, generate both sample projects/PDFs, reopen the projects, verify original hashes, preserve failed extended diagnostics, and check view frames/placement/shared scale/zero dimensions. A constructed arbitrarily rotated pin also generated successfully on A4 with the isometric and opposite-end views disabled. A cube failed correctly with unresolved-axis diagnostic JSON and no PDF. Layout tests cover all four exposed sheet sizes; only the two sample ANSI B pages received the full final visual review.

Independent known-geometry tests exercise pin projection extents, rotation-invariant hex roll, third-angle handedness, isometric inclination, optional-view scale selection and caption spacing. Geometry signatures detect changed internal geometry even when the exterior envelope is unchanged, while distinguishing tiny persistence noise from deliberate geometry changes. XML title fields preserve special filename characters. The dimensions flag is explicitly rejected.

Both final sample drawings were then regenerated through the discovering PowerShell launcher and reopened again with the final code. Both runs returned review exit code **2**, not execution failure. `output/drawing_run_09748.txt` and `output/drawing_run_13125.txt` retain the native runtime messages.

A final portability audit copied each FCStd into a separate directory, made its external SVG temporarily unavailable, and reopened the relocated project. The native `PageResult` loaded the embedded SVG from FreeCAD's document cache; its bytes matched the archive. Editing a title field in the relocated document was verified in a native SVG export while the external template remained unavailable. The external SVGs were restored and the delivered projects/PDFs were not modified by this audit. `output/stage_a_verification.json` records these results, exact retained validation diagnostics, source hashes matching the original Phase 1 reports, and final artifact hashes matching the visually inspected files. `Template` retains the original source filename as metadata; it should not be confused with the cached included `PageResult` that supplies the restored template.

## Review boundary

Stage A is ready for user review. Current limits include one valid closed solid, a resolved/reviewed longitudinal axis, supported page/scale choices and two source-filename lines in the title block. Complex assemblies, very long filenames and fundamentally invalid/open geometry produce explicit limitations rather than silent selection or replacement. Automatic roll selection for unusual asymmetric bodies may need a later user-orientation control; this run used supported hex geometry for both supplied models.

No Stage B dimensions have been added. Overall axial extent, circular enlargement diameter, bore diameter and external hex spacing remain the candidate geometric measurements from Phase 1. They must be attached to reliable native geometry and reviewed before any dimensioned drawing is produced. No thread or manufacturing specification follows from these measurements.
