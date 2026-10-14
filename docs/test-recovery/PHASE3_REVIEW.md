# Phase 3 review

> Historical review: the requested directory cleanup removed archived development outputs, regression suites, synthetic fixtures and investigation scripts. Artifact paths and test commands below record earlier work; they are not all present in this runtime-focused directory. Current usage is in README.md; preservation and post-cleanup checks are in [docs/CLEANUP.md](docs/CLEANUP.md).

Phase 3 replaces the fixed four-characteristic drawing path with geometric feature discovery, dimension candidates, geometry-aware selection, native axial cuts and verified associative dimensions. Both supplied STEP files were actually analyzed and regenerated with the installed FreeCAD runtime on October 9, 2026.

The hex-drive sample has **11 placed native dimensions** and the shaped spring nut has **23**. All confidently supported, nonredundant candidates were placed. Other candidates have specific geometric limitations or verified redundancy reasons. **Neither drawing is claimed dimensionally complete or approved for manufacture.** The spring nut's native cut remains unhatched and requires manual material depiction.

## Delivered results

| Result | FC00AAB09748 | FC00AAB13125 |
| --- | ---: | ---: |
| Discovered dimension candidates | 24 | 53 |
| Placed and verified through save/reopen | 11 | 23 |
| Unresolved geometric interpretations | 2 | 14 |
| Omitted with verified redundancy reason | 11 | 16 |
| Optional omissions | 0 | 0 |
| Native views | 5 | 5 |
| Sheet / scale | ANSI C landscape / 3:1 | ANSI C landscape / 3:1 |
| Native hatching | Rendered, 82 diagonal strokes | Not rendered, 0 diagonal strokes |
| Basic validity / detailed BRep check | Passed / passed | Passed / passed |
| Extended Boolean diagnostics retained | 55 errors | 72 errors |
| Drawing CLI exit code | 2: engineering review required | 2: engineering review required |

ANSI C was selected automatically from the default ANSI B request to reserve legible dimension lanes and a second view row. The sheets contain longitudinal and both end views in third-angle orientation, an axial section/cut, an isometric reference, a native border/title block and preliminary verification notes. Dimensions use millimeters, degrees, diameter/radius symbols and two decimal places; displayed precision assigns no manufacturing tolerance.

The final files are directly in `output/`. Each complete source stem has `.FCStd`, `.pdf`, `.analysis.json`, `.drawing.json`, `.coverage.md`, `.template.svg`, `.render.svg`, `.drawing.log` and `.finishing.log` outputs. Earlier reviewed artifacts are retained in `output/stage_a/` and `output/stage_b/`.

- Hex-drive sample: [editable project](<output/FC00AAB09748_003-NUT_RIVET HEX.DRIVE; refset Entire Part.FCStd>), [drawing/coverage JSON](<output/FC00AAB09748_003-NUT_RIVET HEX.DRIVE; refset Entire Part.drawing.json>), [geometry JSON](<output/FC00AAB09748_003-NUT_RIVET HEX.DRIVE; refset Entire Part.analysis.json>), [coverage summary](<output/FC00AAB09748_003-NUT_RIVET HEX.DRIVE; refset Entire Part.coverage.md>).
- Shaped spring nut: [editable project](<output/FC00AAB13125_002.0006-NUT_SPRG._U_1THD - _U_ SHAPED; refset Entire Part.FCStd>), [drawing/coverage JSON](<output/FC00AAB13125_002.0006-NUT_SPRG._U_1THD - _U_ SHAPED; refset Entire Part.drawing.json>), [geometry JSON](<output/FC00AAB13125_002.0006-NUT_SPRG._U_1THD - _U_ SHAPED; refset Entire Part.analysis.json>), [coverage summary](<output/FC00AAB13125_002.0006-NUT_SPRG._U_1THD - _U_ SHAPED; refset Entire Part.coverage.md>).

## Hex-drive sample measurements

| Characteristic | Displayed measurement | Placement / evidence |
| --- | ---: | --- |
| Overall axial length | 16.24 | Longitudinal; actual terminal stations and native vertices |
| Total flange thickness | 1.00 | Longitudinal; bearing shoulder to front terminal surface |
| Flange outside diameter | ⌀20.00 | Left end; complete analytic cylindrical band |
| External regular region across flats | 9.60 AF | Left end; six equal-offset support planes with regular normal spacing |
| Tail collar diameter | ⌀9.50 | Left end; distinct complete cylindrical band |
| Through bore diameter | ⌀6.00 | Section; opposite native cut traces on the original internal cylinder |
| Front conical land/rim diameter | ⌀9.60 | Right end; source rim and independent cone-law measurement |
| Bearing datum to tail transition | 14.24 | Longitudinal; actual perpendicular boundary support |
| Bearing datum to flange-rim transition | 0.50 | Longitudinal; actual constant-station rim |
| Repeated tangent corner radius | 6X R0.30 | Left end; six native cylindrical patches and tangent neighboring planes |
| Included body taper angle | 16.00° | Section; native generatrices and analytic source cone |

The 1.00 total flange thickness includes the conical portion. Its straight cylindrical rim occupies only 0.50 axially; those are different supported measurements. Likewise, ⌀9.60 is an actual circular rim and 9.60 AF is a planar spacing; matching numbers do not make them duplicates.

The body length below the flange is measured as **15.24**, then omitted because overall length and flange thickness already determine it. The 1.00 tail-collar length and further station relationships are also recoverable from the placed axial graph. The shallow flange cone's included angle is dependent on its two rim diameters and axial separation, so it is omitted.

Two candidate classifications remain unresolved: the polygonal region's axial span and the body's conical span. Their boundaries vary around curved intersections; bounding-box extrema do not establish uniform perpendicular ends. Connecting planar face **19** is retained as unmapped geometry requiring review.

## Shaped spring nut measurements

| Characteristic | Displayed measurement | Placement / evidence |
| --- | ---: | --- |
| Overall axial length | 18.90 | Longitudinal; actual terminal stations |
| Total flange thickness | 1.50 | Longitudinal; actual bearing and terminal planes |
| Flange outside diameter | ⌀22.00 | Left end; complete coaxial band |
| External regular region across flats | 12.70 AF | Left end; supported external polygon planes |
| Distinct external cylindrical diameters | ⌀12.70, ⌀10.70 | Left end; separate analytic source regions |
| Internal cylindrical bore diameter | ⌀9.00 | Cut; opposite original-cylinder traces |
| Circular internal transition rim | ⌀11.00 | Right end; actual rim and independent cone law |
| Rounded tail's conical rim | ⌀12.55 | Cut; actual rim vertices; unrounded value 12.547697… |
| Noncircular internal region depth | 9.20 | Cut; actual axial support stations |
| Cylindrical bore depth from bearing datum | 8.70 | Cut; actual internal transition station |
| Bearing-datum external transition positions | 16.40, 15.48, 15.29, 2.00 | Longitudinal; distinct real boundary stations |
| Repeated opposing internal wall spacing | 3X 11.55 | Right end; three independently verified opposing source-plane pairs |
| Actual opening width in recorded end-view frame | 12.11 | Right end; native extent of the terminal inner wire |
| Included cavity-side wall angles | 115.09°, 129.81° | Right end; oriented source-wall halfspaces and native projected traces |
| Repeated small tangent radius | 6X R0.50 | Left end; analytic source patches |
| Distinct repeated curved regions | 6X R3.05, 6X R3.05 | Opposite end views; different source surfaces and boundary sides |
| Toroidal tail-transition minor radius | R0.26 | Cut; native torus and circular section arc |

The internal opening is **not classified as a regular hexagon**. Its six planar walls have unequal angular spacing. The three equal opposing spacings are grouped only after measuring all three actual pairs, and the two wall angles describe their nonregular orientation. The opening height, 11.546679… in the recorded frame, lies on one of those same actual opposing wall pairs and is omitted as redundant. The width measures the trimmed wire envelope, not a theoretical sharp across-corners size.

The below-flange body length is measured as **17.40** and omitted as dependent on 18.90 overall and 1.50 flange thickness. The 1.00 collar span, internal conical span and other station relationships are derivable from the retained axial graph. The two 90° included coaxial cone angles are dependent on supported rim diameters and station separation; they are recorded as redundant.

Fourteen candidates remain unresolved: one variably trimmed cylindrical length, one variably trimmed polygonal length, and lengths/part-level taper classifications for six local oblique conical patches. Their local analytic parameters are retained, but they do not establish six uniform coaxial chamfers. Planar connecting face **21** and native BSpline surface **27** remain unmapped. The source-defined curved end boundaries need further engineering interpretation; no nominal replacement profile is invented.

## Verification and implementation

The executing runtime was FreeCAD **1.1.4**, bundled Python **3.11.14**, OCC **7.8.1**, Qt/PySide **6.8.3**. Runtime paths are discovered by the Windows launcher; drawing modules do not assume this installation location.

Feature discovery, dimension selection, source/projection matching, placement, native views and export are separate modules. Analysis records geometric measurements separately from inferred classifications. Candidate source references and numerical thresholds are tied to the current source hash and native import, rather than fixed sample coordinates or edge numbers.

Every placed dimension passed discovery/source/projected/native agreement and a repeated save/reopen check. Source measurements use native surface radii, support-plane locations, actual station boundaries, torus parameters, cone-law evaluation or terminal-wire extrema. Projected measurements use actual native edges/vertices. Included wall angles use the cavity-side orientation of the source halfspaces and independently oriented projected line normals; no arbitrary angle override substitutes for an incorrect acute/supplementary value.

Native `References2D`, type, value, units, format, presentation and position are retained in JSON. Source geometry is compared through topology/types, native bounds, area/volume, UV ranges, nine face probes and five curve probes per entity. The maximum recorded numerical deviations after persistence were **7.96e-13** and **9.09e-13**; the geometric roundtrip threshold is 1e-8 in native quantities. BRep serialization bytes changed, while these geometric comparisons passed. This is explicitly distinguished from byte identity.

FreeCAD restore can renumber projected edges/vertices or repartition a circular arc. The tool accepts such a remap only if the analytic circle/straight carrier or exact vertex is unchanged and source support is matched again. Remaps are recorded; references are not rewritten to conceal failure. A matching scalar alone cannot pass verification. Arbitrary values, angle overrides, arbitrary tolerances, theoretical-exact flags and assigned tolerances are rejected.

The finishing process reopens a staged native document in a fresh GUI host, checks associativity, settles actual native vector-text bounds and exports from the persisted project. This avoids stale Qt drawing groups observed on the installed runtime. Basic Stage B rendering was also corrected to wait for native projection/measurement completion before validating persisted text. Scene files are isolated per process.

The source STEP hashes were checked before import and after generation:

| Source | SHA-256, unchanged |
| --- | --- |
| FC00AAB09748 | `f3d97d4cab35e9a0443a20ff4c61d68d488860eaa27936d7200dc907d4264264` |
| FC00AAB13125 | `546fafd4f1317079f929c56af69d96cc51c4450bc8e66e8782b79e7ac5860093` |

## Section limitation

Both cuts are native `TechDraw::DrawViewSection` objects referencing `OriginalSTEP`. Their plane passes through the recovered fastener axis; normal, origin, direction, base view, symbol, pattern, scale, placement and source references are checked after reopening. No source reconstruction or healing is performed.

The independent original-BRep plane intersection yields **one closed loop and one open trace** for the hex-drive sample, despite the native view rendering a hatched material section. The open trace remains an explicit source-quality warning. The spring nut yields **two closed loops and no open traces**, but native TechDraw section-face conversion does not produce its hatch pattern. A diagnostic probe found four closed native intersection faces and zero mapped hatchable section faces. Thus a successful mathematical cut does not by itself establish successful drawing hatching.

The spring nut is labeled **AXIAL CUT A-A (UNHATCHED)**. Its outlines and measurements remain source-verified, while the conventional material depiction needs manual completion. Generic 45° hatch patterns do not imply a material specification. Automatic detection of hatch strokes is only a presentation check, not proof that every material boundary has been communicated correctly.

## Tests and final PDF review

**All 63 tests passed** in the complete native regression run recorded in [test_results_phase3.txt](output/test_results_phase3.txt), taking 262.507 seconds: 22 analysis tests, 15 original drawing tests, 8 Stage B tests, 9 generalized feature tests and 9 comprehensive selection/integration tests. Independently constructed fixtures cover stepped external cylinders and bores, variable flange thickness, a cone, a native toroidal fillet, an annular recess, an offset bore, regular and nonregular openings, rotation/translation, section generation, axial relationship graphs, deduplication, collision checks, save/reopen and actual native vector export. The irregular opening fixture has known 10 mm opposing wall spacings and known wall angles, without relying on either supplied part.

Final PDF QA is recorded in [pdf_validation_phase3.json](output/pdf_validation_phase3.json). `pypdf` checks the physical page size, searchable computed dimension labels and absence of image XObjects. Poppler and independent PDFium renders are inspected separately from source measurements. Each final sheet is one **1584 × 1224 point** page (22 × 17 inches) and remains the unmodified native vector PDF export.

Native Qt/FreeCAD PDFs emit `No current point in closepath` warnings in Poppler: **21 per sheet**, retained in the render logs. Both rendering engines complete successfully. Native SVG/PDF label checks, physical text collision checks and rendered inspection are separate evidence categories. Visible hatching succeeds only for the first sample. Angular arcs and short-span datum text were separated during the final layout pass; the spring-nut end caption was moved beside the view to clear angular extension rays. The second model remains visually more complex.

After the angular-lane refinement, all **9 comprehensive regression tests passed again** in [test_results_phase3_final_layout.txt](output/test_results_phase3_final_layout.txt). The final generated documents also repeat source, reference, placement and caption-position checks through native save/reopen.

The following previews represent the exact final PDFs; their hashes and visual-review status are recorded in the corresponding JSON reports. Visual inspection is preliminary and does not approve source defects, design intent, manufacturing tolerances or dimensional completeness.

### FC00AAB09748

![Hex-drive sample final native drawing](C:/Users/vsche/Projects/FastenerDrawing/output/preview_phase3_FC00AAB09748.png)

### FC00AAB13125

![Shaped spring nut final native drawing](C:/Users/vsche/Projects/FastenerDrawing/output/preview_phase3_FC00AAB13125.png)

## Remaining engineering work

Resolve the retained BRep/Boolean defects and complex trimmed regions, complete and verify the spring nut's section hatching, and review unrecognized source surfaces and any additional characteristics required by the part's intended use. Thread appearance remains `cannot_determine`: a smooth bore supplies no defensible nominal thread designation. No tolerances, GD&T, materials, finishes or manufacturing processes were assigned.

Recognition and candidate coverage are explicitly nonexhaustive. This implementation completes the Phase 3 development/measurement/reporting scope with the documented section limitation; it does not deliver manufacturing-approved or provably complete part definitions. No graphical user interface was developed.
