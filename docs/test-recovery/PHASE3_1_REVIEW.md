# Phase 3.1 review — drawing quality, section repair and generalization

> Historical review: the requested directory cleanup removed archived development outputs, regression suites, synthetic fixtures and investigation scripts. Artifact paths and test commands below record earlier work; they are not all present in this runtime-focused directory. Current usage is in README.md; preservation and post-cleanup checks are in [docs/CLEANUP.md](docs/CLEANUP.md).

Date: 2026-10-12. All drawings remain preliminary and require engineering verification. Measurements describe imported geometry; they are not nominal manufacturing specifications. No tolerances, material, finish, thread designations or GD&T were added. Original STEP files were not modified or healed.

## Presentation and coverage

Both drawings use ANSI B landscape (431.8 × 279.4 mm / 17 × 11 inches), with main views at 2:1. The full input stems are preserved. Final PDF, editable FCStd, analysis JSON, drawing JSON and coverage Markdown are directly in `output/`. The previous Phase 3 artifacts are preserved in `output/phase3/`.

| Model | Placed dimensions | Unresolved candidates | Redundant candidates | Section depiction |
| --- | ---: | ---: | ---: | --- |
| FC00AAB09748 | 11 | 2 | 11 | Native associative TechDraw section hatching |
| FC00AAB13125 | 23 | 14 | 16 | Native section plus independently verified cached hatch geometry |

No meaningful dimension was removed to improve appearance. Coverage has the same placed counts as Phase 3. Every unresolved candidate and omission reason remains in the reports; recognition and dimensional completeness are explicitly not claimed.

The 115.09° and 129.81° dimensions now describe actual measured wall-plane traces in a 5:1 opening profile detail. A native `PartDesign::SubShapeBinder` refers to the original terminal-wire edges; a native TechDraw view displays that exact boundary. This is a source-edge profile detail, rather than a cropped full-model `DrawViewDetail`: it excludes unrelated rear bore and flange projections without reconstructing a theoretical sharp polygon. The angle-location calculation uses the two actual straight carriers to position the arc; their intersection is not assigned a manufactured sharp corner or dimensioned vertex. Compact angular arc radii are 18–22 mm on paper, with 2 mm arrows.

Main views remain aligned. Axial dimensions occupy physical 7 mm lanes; end-view diameter lanes are included in scale/page selection. The profile detail and end caption have a separate 8 mm layout reservation. Radius leaders select a source-proved trace near the intended callout area rather than an arbitrary longest arc. Text is 3.5 mm high on paper; ordinary arrows are 2.5 mm. Border/title-block text retains its template sizes. These physical sizes do not shrink when the geometry scale changes.

Native scene text bounds, installed font metrics, captions, source view envelopes and paper limits are checked. A placement failure retries a larger sheet, then reports failure if supported sheets cannot accommodate it; it does not silently delete a dimension. Multiple drawing sheets were considered, but these two parts fit on one ANSI B sheet. General multi-sheet allocation is not implemented. Dense unfamiliar parts can still need manual presentation work.

Six black 0.18 mm dash-dot cosmetic centerline segments are saved in each native project: one longitudinal, two at each end, and one on the section. They follow the recovered model axis, and their saved positions and formats are verified after reopen. They stop within the source envelope so they cannot expand an automatic extent dimension. Extending centerlines conventionally beyond a view while keeping them excluded from extent calculations remains a drafting improvement. Automatic red/green centerlines observed on this installation were replaced with explicitly formatted native cosmetics. Cosmetic UUIDs change on restore; validation checks their geometry and format instead of relying on those transient IDs.

Section cutting arrows and A-A labels remain native. The opening detail has its own scale caption. Repeated radii retain verified multiplicities. Terms such as opening, supporting plane and transition radius describe geometry; they do not assert drive function, tool choice, process, thread form or intended fit. The detailed coverage reports identify the actual geometric baseline supports rather than assuming every part has a bearing shoulder.

## Why the spring-nut native hatch fails

The problem is in native section-face conversion, not merely a missing pattern setting. Debug BReps from the installed FreeCAD version show this sequence:

1. Native cut intersections contain four topologically closed faces, including duplicate pairs. Aggregate area is 112.895284 mm²; this is not accepted as physical material area.
2. Two boundary families have evaluated curve-end gaps of approximately 0.000750089 and 0.003488271 mm, despite topological closure. Their cut-face tolerances reach approximately 0.020144728 and 0.126192579 mm.
3. Projection into the drawing plane splits those boundaries into open chains. At the archived 3:1 scale, the largest projected gaps are approximately 0.002250266 and 0.010464812 mm.
4. Native `DrawViewSection::mapToPage()` projects the boundary, attempts wire assembly and rejects nonclosed results. The debug `DVSTopoSectionFaces.brep` contains zero faces, so there is no native hatchable face.

The [matching installed-commit section implementation](https://raw.githubusercontent.com/FreeCAD/FreeCAD/4fd3bf320d9566a27e60069fc8387448aaa3a094/src/Mod/TechDraw/App/DrawViewSection.cpp) corroborates that conversion path. Actual debug geometry, not a source-code assumption alone, establishes the observed failure.

The original spring-nut BRep itself has a maximum evaluated wire curve-end gap of 0.010525798 mm and maximum topological tolerance of approximately 0.020144728 mm. The hex-drive source's corresponding gap is only approximately 4.39e-8 mm, although its maximum tolerance is approximately 0.001184396 mm. Thus source curve/topology inconsistencies contribute to fragile section conversion. The precise original edge responsible for each failing cut cap has not been isolated. The retained C0, curve-on-surface and other Boolean diagnostics must not be collapsed into an unsupported claim about one particular defect.

`TrimAfterCut=True` and `Shape.fix(1e-7, 1e-7, .001)` on a disposable in-memory copy were actually tested. Neither restored native spring-nut hatch faces or removed its 72 Boolean diagnostics. The original project hashes before and after those probes match. Repair copies are not used in production, and no gap bridging or projected-boundary approximation was introduced.

Detailed native BReps, exported scenes and checks are retained under `output/section_diagnostics_phase3_1/`, including `section_forensics.json` for each part.

## Verified material fallback

Independent `Part.section` on the original spring-nut solid produces 26 exact edges forming two closed wires. Native Bullseye face construction handles boundary nesting and cavities. The accepted regions have areas approximately 28.222390 and 28.233756 mm², totaling 56.456146 mm². Each complete region is intersected with, and subtracted from, the original solid: intersection area matches the region area and outside-solid area is zero within numerical consistency checks.

The exact planar regions are rigidly transformed into a local plane. Native `TechDraw.makeGeomHatch` generates 35 segments at a 2 mm physical pitch, which are transformed back. Every complete segment is intersected with the original solid, and its entire length must match; testing only a segment midpoint would be insufficient. Native `DrawViewPart` displays the checked edges, with direction, scale and geometric centering explicitly aligned to the native section. All segment/material and view-alignment checks repeat against the saved original BRep after reopening the final FCStd.

**This fallback is cached derived geometry, linked to the original source, and requires rerunning the generator after source edits. It does not have the automatic regeneration behavior of native section hatching.** This limitation is recorded in the project object label, drawing JSON and coverage summary. No projected silhouette is promoted into an assumed material boundary.

The hex-drive part retains successful native associative hatching. Its exported 56 diagonal strokes are also checked against the original solid; the maximum outside-length discrepancy is approximately 3.91e-5 mm from SVG coordinate rounding, below the separate 1e-4 mm SVG diagnostic threshold. This threshold is not a manufacturing tolerance. Independent `Part.section` for that source contains an open trace, so the fallback deliberately refuses it instead of forcing it into a material face. Native success on that part and independent fallback success on the other part are separate verified paths.

Fallback construction requires valid closed exact section boundaries, valid material-area Boolean results and complete-segment agreement. If any condition fails, the cut remains explicitly unhatched and requires manual completion. These checks strengthen evidence but do not certify a defective kernel solid for manufacturing.

## Geometry and dimension diagnostics

Both imported solids pass basic validity and closure checks, but extended Boolean validation still reports 55 diagnostics for FC00AAB09748 and 72 for FC00AAB13125. Those warnings remain visible in logs, JSON and drawing notes. Both successful generation commands return 2 for required review.

Dimension creation uses independent original source measurements, measured native projections and computed native values. Native saved references and source-support fingerprints are rechecked after restore. A reference changing to a geometrically equivalent circle/carrier is accepted only after repeated proof, not because its numerical value happens to look plausible. Native cut measurements are verified separately from material depiction; successful hatching does not cleanse a bad dimension reference.

Input SHA-256 values remain:

| Model | SHA-256 |
| --- | --- |
| FC00AAB09748 | `f3d97d4cab35e9a0443a20ff4c61d68d488860eaa27936d7200dc907d4264264` |
| FC00AAB13125 | `546fafd4f1317079f929c56af69d96cc51c4450bc8e66e8782b79e7ac5860093` |

## Native PDF export diagnostics

Each final vector PDF has one ANSI B page and all 11/23 computed dimension labels; no image XObjects are present. Native PDFs are retained exactly as exported, with no content-stream patching.

Poppler reports 21 syntax warnings on each: 18 `No current point in closepath` messages and three invalid RGB `SCN` argument messages. Read-only operator inspection finds empty `h` operations after path-ending fill operations and empty `SCN` commands in `/DeviceRGB`, which requires three components.

Actual native export isolation probes distinguish their origins:

| Probe | Empty closepaths | Empty RGB commands |
| --- | ---: | ---: |
| Normal border/template and cutting line | 18 | 3 |
| Native cutting line disabled | 18 | 0 |
| Blank template, cutting line retained | 0 | 3 |

This isolates the closepath defect to template rendering and the RGB defect to native section cutting-line graphics. It does not establish the exact Qt implementation bug or an upstream fix. Removing the border or section indication to hide warnings would reduce drawing quality, so both remain. Probe results are in `output/pdf_sectionline_diagnostics_phase3_1.json`.

Poppler and PDFium independently render the final native PDFs. At a common 2000-pixel width their dark-pixel counts differ because of font rasterization and antialiasing. The ink-location comparison finds zero unmatched pixels for the spring nut and three PDFium pixels beyond a two-pixel neighborhood for the hex-drive drawing (0.00367% of its dark pixels). Final images from both renderers were inspected; no missing material regions, dimensions or visible drawing elements were found. This is a useful renderer disagreement check, not proof of pixel equality or geometric correctness. PDF syntax warnings remain a known export limitation.

## Focused generalization review

Production code contains no sample-name selection or fixed sample edge-number table. Feature measurements originate in BRep surfaces, wires, supporting planes and measured stations. The sample identifiers appear in regression checks and diagnostic artifact naming. Nevertheless, absence of a filename branch does not prove a general system.

| Risk | Current behavior and remaining limit |
| --- | --- |
| Axis and roll assumptions | Dominant analytic common axes and supported planar symmetry; arbitrary transforms are tested. Multiple competing axes, assemblies or unclear orientation remain unresolved. An explicit view-axis override does not authorize unsupported feature classification. |
| Analytic feature coverage | Cylinders, planes, cones and supported radii dominate. Nonanalytic trims, deformed/spline faces, unusual drives and thread forms remain incompletely recognized; unmapped faces and unresolved candidates are exposed. |
| Opening profile rule | Requires one uniquely supported terminal boundary. Ambiguous or multiple openings do not receive a guessed detail. It presently favors this geometry family; side features and competing details need broader allocation rules. |
| Layout heuristics | Rows, 7 mm lanes, preferred scales, physical arc radii and paper fractions are general layout choices, but not a routing optimizer. Long shafts, many offset features and crowded annotation groups can need larger sheets or manual work. Multi-sheet layout is not implemented. |
| Native references | Projected numbering can change on restore; source measurement, loci and fingerprints are repeated. STEP/OCC changes or edited source topology can still invalidate the support. Original edge IDs are tied to the source hash/import, not guaranteed stable CAD names. |
| Defective BReps | Each region and segment is checked against the original solid. Native Boolean operations are themselves kernel-dependent; retaining original extended-check warnings is essential. No unreliable section is repaired merely to make it hatch. |
| Feature function | A measured opening or enlargement does not establish a drive type, head function, simplified thread or manufacturing intent. Unknown roles remain unknown. |
| Runtime dependence | Actual FreeCAD 1.1.4, Python 3.11.14, OCC 7.8.1 and Qt 6.8.3 were tested. Other importer/kernel versions require their own verification, particularly section conversion, references and PDF export. |

Four additional controls were independently constructed rather than edited from either development model:

| Synthetic fixture | Distinct geometry | Known overall length |
| --- | --- | ---: |
| countersunk_pin | Smooth shaft and terminal cone | 27 mm |
| shoulder_pin | Multiple shaft diameters, circular head, transverse hole | 31 mm |
| slotted_round_head | Round head with shallow slot | 24 mm |
| grooved_dowel | Circumferential groove on unheaded pin | 35 mm |

All are rotated 73° about a nonprincipal axis and translated far from the origin. In-memory validity and lengths are checked; durable STEP inputs and a hash/expectation manifest are in `input/fixtures/`. Actual CLI analyses are in `output/generalization_phase3_1/`. The cross-drilled shoulder pin acquires 12 curve-on-surface Boolean diagnostics during STEP roundtrip, which are retained and yield exit 2. This exposes importer/kernel limitations even for a constructed control.

Two of these families also exercise actual native drawing generation, source preservation, dimension values and saved-project reopen. They exposed insufficient end-diameter lane reservation, which was fixed. Section controls cover both a through bore (two separate material regions, 108 mm²) and a fully enclosed void (one 140 mm² material face with two nested wires). Complete hatch segments are verified in both cases, so the nested inner loop cannot be filled as material. The additional enclosed-void check was executed separately and passed; its result is in `output/test_results_phase3_1_nested_material.txt`. The defective hex-drive cut verifies fallback refusal for open traces. A cube with no recoverable axis returns a complete unresolved discovery schema instead of failing with a missing key.

**Synthetic regression controls do not demonstrate real-world generalization.** Further evaluation needs independently supplied STEP samples from different CAD systems: ordinary hex bolts, socket heads, countersunk and flanged screws, cross-drilled/grooved pins, modeled threads, short squat parts, long slender shafts, asymmetric features, multiple openings and poor-quality imports. No broad applicability claim is made from the current two vendor models and constructed controls.

## Validation record and remaining work

The full existing regression suite plus the six new quality tests is run with the installed bundled interpreter:

```powershell
& 'C:\Program Files\FreeCAD 1.1\bin\python.exe' -m unittest discover -s tests -v
```

All 69 tests passed in 293.649 seconds; the complete result is recorded in `output/test_results_phase3_1.txt`. The added enclosed-void subcase also passed its separate focused execution. Both supplied models were regenerated at the canonical output paths. The final source, dimensions, native views, material checks and persisted cosmetics pass automatic reopen validation. Source topology, types, extrema, area/volume and per-face/edge probes agree after reopen: maximum numerical deviations are approximately 7.96e-13 and 9.09e-13 in the native quantities, respectively. The comparison threshold is 1e-8; these are computational roundtrip checks, not assigned engineering tolerances. `output/generation_results_phase3_1.json` records their review-required exit codes. `output/pdf_validation_phase3_1.json` ties independent renderer previews, labels, operator diagnostics and visual review to each final PDF hash. Review is preliminary, not an engineering release.

Remaining limits are the original Boolean defects, cached fallback regeneration, native PDF syntax warnings, incomplete feature coverage, heuristic routing and lack of an independent real-world test corpus. No graphical interface or large feature-recognition expansion was undertaken in this phase.

Final previews:

![FC00AAB09748 final Poppler preview](C:/Users/vsche/Projects/FastenerDrawing/output/preview_phase3_1_FC00AAB09748.png)

![FC00AAB13125 final Poppler preview](C:/Users/vsche/Projects/FastenerDrawing/output/preview_phase3_1_FC00AAB13125.png)
