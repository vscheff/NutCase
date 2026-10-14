# Phase 1 review — October 9, 2026

> Historical review: the requested directory cleanup removed archived development outputs, regression suites, synthetic fixtures and investigation scripts. Artifact paths and test commands below record earlier work; they are not all present in this runtime-focused directory. Current usage is in README.md; preservation and post-cleanup checks are in [docs/CLEANUP.md](docs/CLEANUP.md).

Phase 1 was executed against **both** supplied STEP files using the installed FreeCAD 1.1.4 bundled Python 3.11.14 and Open CASCADE 7.8.1. The Windows launcher discovered and tested the interpreter. Both runs saved JSON/logs and returned code **2**: completed analysis with geometry problems requiring review. This is distinct from an execution failure.

Phase 2 has not been implemented. All values below are preliminary geometry measurements in millimeters, not nominal specifications or toleranced manufacturing dimensions. Display rounding does not assert engineering accuracy.

## Measured results

The filename abbreviations identify the supplied files only; they do not supply recognition evidence.

| Observation | `FC00AAB09748` — HEX.DRIVE filename | `FC00AAB13125` — U_SHAPED filename |
| --- | ---: | ---: |
| Imported solids / faces | 1 / 20 | 1 / 64 |
| Global XYZ envelope | 19.984502 × 21.221410 × 20.895933 | 22.038228 × 22.000656 × 21.809389 |
| Axis-aligned axial extent | **16.24** | **18.90** |
| Complete circular terminal enlargement diameter | **20.00** | **22.00** |
| External hexagonal supporting-plane spacing | **9.60** | **12.70** |
| Measured smooth cylindrical bore diameter | **6.00** | **9.00** |
| Axial extent of that bore's cylindrical faces | 16.24 | 8.70 |
| Other measured coaxial external diameters | 9.50 | 12.70 (partial bands), 10.70 |
| Basic validity / detailed BRep check | Passed / passed | Passed / passed |
| Closed solid | Yes | Yes |
| Extended Boolean check | **Failed** | **Failed** |
| Thread classification | **Cannot determine** | **Cannot determine** |

The external cylinder diameter of 12.70 in the second file is a surface-radius measurement. Its two trimmed half faces have slightly different end bounds, so the analyzer deliberately does not label their union a complete rectangular band.

The selected unit direction vectors are approximately:

- `FC00AAB09748`: `(0.071563951, 0.840469291, 0.537112625)`.
- `FC00AAB13125`: `(-0.033932027, 0.976115516, -0.214585920)`.

These are common analytic centerlines recovered from native geometry. Neither coincides with global Z. Their longitudinal fastener role is inferred, and their signs do not identify the head end. The axis-aligned envelope's transverse X/Y basis is arbitrary.

## What is recognized, and what remains unresolved

Both reports recognize overall geometric extent along the selected common axis. Both also recognize the diameter of a terminal annular **flange-like** enlargement: complete external circular bands, circular shoulder rims and narrower coaxial body geometry support this role. The engineering function of the enlargement remains an inference.

External hexagonal geometry is supported by six planar faces and three equal opposite-plane spacings. It is retained under `geometry.hexagonal_regions`; neither model establishes a bolt/screw **head**. Consequently the requested head `across_flats` dimension remains null even though the external hex spacing is measured. This avoids turning a hexagonal body into a head by assumption.

The bore diameters and cylindrical axial spans are direct geometric observations. A 6.00 or 9.00 bore is not sufficient evidence for an M6/M9 thread, nor does its cylindrical span establish threaded length. The filenames are not treated as thread annotations. No sufficient repeated helical flank geometry was detected, so simplified, omitted and unthreaded geometry remain indistinguishable here.

For both samples, these requested feature dimensions are unrecognized (`value_mm: null`):

- Length under head, head height and head diameter.
- Shank diameter.
- Thread major diameter and threaded length.
- Across-flats dimension **as a head dimension**.

The second file's name says U-shaped spring nut. The measured solid has a common cylindrical axis, a circular enlargement, six external supporting flats and a smooth bore. Those observations do not establish a U-shaped spring-nut classification. The mismatch should be reviewed against the intended source part; the program does not force the filename's description onto the geometry.

## Geometry diagnostics requiring review

The first model's extended check reports **55** error entries:

- 13 `Error in Edge: BOPAlgo GeomAbs_C0` entries.
- 21 `Error in Edge: BOPAlgo_InvalidCurveOnSurface` entries.
- 21 `Error in Face: BOPAlgo_InvalidCurveOnSurface` entries.

The second model reports **72** error entries:

- 16 `Error in Edge: BOPAlgo GeomAbs_C0` entries.
- 28 `Error in Edge: BOPAlgo_InvalidCurveOnSurface` entries.
- 28 `Error in Face: BOPAlgo_InvalidCurveOnSurface` entries.

These are diagnostic entries, not a proven count of distinct defective entities. This installed API's exception text does not expose stable face/edge IDs for the failed checks. Raw text, count summaries and basic-check results are saved in the JSON. Passing basic validity does not cancel these extended failures.

The maximum native BRep tolerances are about **0.001184396 mm** and **0.020144728 mm**, respectively. These describe the imported geometry's kernel tolerances; they are neither manufacturing tolerances nor established uncertainty bounds for every reported measurement. The larger value in the second model reinforces the need to inspect its source geometry. The analyzer applies no explicit healing and does not silently relax its recognition threshold to that value.

The extended diagnostics do not prevent direct radius/plane measurements from being recorded, but they make the models unsuitable for being declared verified drawing sources. Before relying on downstream projection or dimension references, review the intended parts and whether their STEP exports should be repaired or replaced. No repairs were applied in this phase.

## Saved artifacts and verification

- `output/environment.json`: executing versions, paths and available native capabilities.
- `output/FC00AAB09748_003-NUT_RIVET HEX.DRIVE; refset Entire Part.analysis.json` and matching log.
- `output/FC00AAB13125_002.0006-NUT_SPRG._U_1THD - _U_ SHAPED; refset Entire Part.analysis.json` and matching log.
- `output/freecad_probe.txt`: installed method documentation and development face inspection.
- `output/test_results.txt`: **22 passing native-kernel tests**.
- `output/sample_verification.json`: independent end-plane/flat-plane distance and native radius checks against both saved reports.

Both reports include matching SHA-256 hashes before and after analysis. The original STEP files were preserved. Independent end-plane separations also agree with the reported axial extents, and opposite-flat plane separations agree with the hexagonal measurements. The regression suite actually constructed and analyzed circular/hexagonal headed shafts, hollow parts, analytic cones, an external helical thread example and a coil counterexample; it also performed real STEP export/import and checked arbitrary orientations.

No GUI/visual review, TechDraw view creation, FCStd save or PDF export was performed or claimed. The next phase remains pending review of these results and recognition limits.
