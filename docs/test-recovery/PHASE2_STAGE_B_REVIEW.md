# Phase 2 Stage B review

> Historical review: the requested directory cleanup removed archived development outputs, regression suites, synthetic fixtures and investigation scripts. Artifact paths and test commands below record earlier work; they are not all present in this runtime-focused directory. Current usage is in README.md; preservation and post-cleanup checks are in [docs/CLEANUP.md](docs/CLEANUP.md).

Stage B implements native associative dimensions on the two supplied STEP models. All four requested characteristics were supported by analytic source geometry and matched to native TechDraw projections. The first sample was generated and visually checked before dimensioning the second. These are measured STEP dimensions, not approved manufacturing specifications.

## Measurements and presentation

| Characteristic | FC00AAB09748 | FC00AAB13125 | Native measurement and attachment |
| --- | ---: | ---: | --- |
| Overall axial length | 16.24 mm | 18.90 mm | `DrawViewDimExtent`, horizontal extent of the longitudinal view; independently checked against terminal source planes |
| Flange-like diameter | 20.00 mm | 22.00 mm | `DrawViewDimension`, diameter of a verified visible circular rim on the right end |
| Smooth bore diameter | 6.00 mm | 9.00 mm | `DrawViewDimension`, diameter of the verified inner circular rim on the right end |
| External hex across flats | 9.60 mm | 12.70 mm | `DrawViewDimension`, vertical distance between opposing support-plane traces on the left end |

Values come from fresh analysis of each current source file; the generator contains no sample-specific measurement constants. Two decimal places are formatting, not an assigned tolerance. The hex region is not called a head. The smooth cylindrical bore receives no thread designation.

ANSI B landscape, third-angle projection, millimeter units, title block, notes and isometric reference are retained. Native views and dimensions share the page scale. Reserved dimension lanes select 3:1 for FC00AAB09748 and 2.5:1 for FC00AAB13125. Overall/flange dimensions occupy separate upper lanes; across flats is to the left and the bore uses a lower-right leader. No redundant diameters or manufacturing specifications are added.

## Verification

Each dimension's drawing JSON identifies source face IDs, independent BRep measurement, projected geometry fingerprints, actual `References2D`, native type/value, formatting, paper position, text bounds and reopened verification. Source face IDs belong to the single solid in the recorded import. Native edge names are discovered and checked against actual getter geometry, rather than assumed from an example drawing.

Circle matching checks radius, projected center, supporting cylinder axis and actual source boundary rims. This prevents selecting a nearby concentric circle with a plausible diameter. Across flats checks two actual opposing planes, visible straight traces at those planar loci, and their native trimmed extents. Analytic lines and geometrically straight spline traces can coexist in the projection; the selected saved traces must themselves remain supported after reopening. Equivalent projected rim/trace candidates are recorded.

Four measurements must agree: Phase 1 value, independently measured source geometry, native projected geometry, and `getRawValue()` from the associative dimension. The numerical matching threshold is **0.00001 mm**. It is an algorithm setting, not a manufacturing tolerance. Arbitrary values, arbitrary tolerances, theoretical-exact dimensions and nonzero assigned tolerances are rejected.

The saved project is reopened, its original source geometry checked at **0.00000001** in native quantities, and its source features measured again. Reference names, projected fingerprints, source-to-projection support, raw values, measurement mode, formatting, presentation and position are verified. Source STEP hashes remain unchanged. Serialization bytes can change through FreeCAD persistence; the report distinguishes that from native geometric equivalence.

Placement checks use actual native Qt datum/caption bounds in physical paper millimeters, not pixels or screenshots. Text must stay inside the content area and at least 1 mm from view envelopes, captions and other dimension text. Layout lanes are allocated before selecting scale. Unsupported features are omitted with explicit reasons; a placement failure stops generation and writes diagnostic JSON.

## Installed API findings

The implementation was executed with installed FreeCAD 1.1.4, Python 3.11.14, OCC 7.8.1 and Qt/PySide 6.8.3. Installation discovery remains in the existing Windows launcher.

- On this installation, `getEdgeByIndex(0)` corresponds to `getEdgeBySelection("Edge0")`. The correspondence is verified at runtime. Getters return unscaled geometry with reflected Y; visible-edge results are normalized and matched in the same coordinates.
- `getGeometricCenter()` examines a source that may already contain display triangulation. TechDraw centers a geometry copy without that triangulation, so the getter differed slightly on freshly generated samples. Source-point projection now reproduces TechDraw centering on a mesh-free native BRep copy. This changes reference matching, not source geometry.
- Native dimension X/Y are paper offsets relative to the referenced view. View X/Y are absolute bottom-origin page positions.
- Creating/saving an extent dimension left the initial GUI scene without its longitudinal view in one exported PDF. The raw value and geometry checks had passed. Final PDF export now uses a fresh native scene from the reopened FCStd. Native SVG scene export checks computed labels immediately before PDF export. This is why visual validation is kept separate from successful native measurements.
- Qt SVG output splits diameter glyphs and digits into sibling text runs. The native scene check joins those runs; it does not replace or manufacture labels.

## Tests and visual review

**45 tests passed** in the complete native regression run recorded in `output/test_results_stage_b.txt`. This includes 22 Phase 1 tests, 15 drawing tests and 8 Stage B tests. An independently constructed hollow hex fixture specifies 21 mm overall length, 16 mm flange diameter, 4 mm bore and 10 mm across flats. These known values survive rotation, translation, STEP export/import, native dimension creation and project reopening.

Adversarial native checks reject an equal-radius circle at the wrong center, hidden-only references, missing projected geometry, changed native references, missing native references and arbitrary value overrides. Source tessellation does not alter reference matching. A stepped bore is correctly omitted rather than selecting one of several diameters. Layout, collision boundaries, scale reduction, both supplied models, vector PDF export, provenance and persistence are covered.

Final PDFs are directly under `output/` with their corresponding FCStd, JSON, logs and SVG files. Approved Stage A artifacts are retained in `output/stage_a/`. Independent final PDF checks and rendered previews are recorded in `output/pdf_validation_stage_b.json` and `preview_stage_b_*.png`. Drawing JSON distinguishes automated verification, recorded visual review and pending engineering approval.

Both final sheets were inspected in Poppler and independent PDFium renders. All four displayed dimensions and diameter/AF notation were readable and consistent with the independently checked source measurements. Views, captions, leaders/arrows, title block, notes and borders were complete with no observed text collision or clipping. `pypdf` independently extracted all four computed labels from each PDF. Each is one 1224 × 792 point page (17 × 11 inches), with zero image XObjects. Poppler returned success with 16 native `closepath` warnings per PDF; PDFium also rendered both. Review records include the hashes of the exact delivered PDFs. These visual checks do not constitute engineering approval.

## Limits requiring review

Both original solids remain basically valid and closed, with detailed BRep checks passing, but extended Boolean checks still fail: 55 diagnostic entries for FC00AAB09748 and 72 for FC00AAB13125. No healing or source modification was performed. Successful measurements and projections do not resolve those failures.

Thread appearance remains undetermined. Bore/flange/hex measurements establish geometric characteristics, not nominal fastener specifications, manufacturing function or thread requirements. Tolerances, materials, finishes, GD&T and thread specifications remain unassigned.

Reference verification covers these saved projects and their current source hashes. It is not a guarantee that topological names survive arbitrary future model revisions or another FreeCAD release. Rerun analysis and verification after a change. Multiple distinct supported bore diameters, missing visible analytic rims, unmatched flats and unsupported source features remain unresolved.

The placement algorithm reserves lanes and checks text bounds; it is not a general extension-line/leader-routing solver. Arrows, unrelated line crossings and complex geometry still need PDF review. Native geometry fingerprints and extent checks cannot establish manufacturing suitability or certify every projected internal curve.

Poppler reports `No current point in closepath` warnings from the native FreeCAD/Qt PDF. The native PDFs are retained rather than rewritten through another drawing engine; independent Poppler/PDFium rendering and extracted labels are used to assess the delivered sheets. A visible desktop FreeCAD GUI session was not tested. Engineering verification is still required.
