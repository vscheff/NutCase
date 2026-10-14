# Phase 3.2: Nitro PDF compatibility

> Historical review: the requested directory cleanup removed archived development outputs, regression suites, synthetic fixtures and investigation scripts. Artifact paths and test commands below record earlier work; they are not all present in this runtime-focused directory. Current usage is in README.md; preservation and post-cleanup checks are in [docs/CLEANUP.md](docs/CLEANUP.md).

Completed on 2026-10-12. Both corrected drawings were opened and inspected in **Nitro PDF Pro 14.22.1.0 on this machine**, including the final files at their usual `output/` paths. The missing views, diameter dimensions, section indicators and captions are visible. This is an observed result for this Nitro version and these files, not a promise about every PDF viewer.

## Confirmed cause

The failure is caused by three **operandless stroking `SCN` commands** emitted for native sectional cutting-line graphics. It is not a diameter-only font failure. Nitro loses subsequent content in the page stream, including projected geometry, ordinary text, native dimensions and section graphics.

The relevant sequence is:

```text
/CSp CS
SCN
```

`/CSp` resolves to `/DeviceRGB`, whose stroking color needs three components. The first defective operation occurs at zero-based stream index 53966 in FC00AAB09748 and 59961 in FC00AAB13125. The longitudinal dimensions occur before it; the end dimensions, captions and lower views occur after it. A diagnostic PDF truncated just before the first bad `SCN` reproduces the user's screenshot pattern: the template, longitudinal view and right-end geometry remain, while the later drawing content disappears. The prefix file is deliberately incomplete and is never a deliverable.

A live Qt scene inspection found three `QGraphicsPathItem` objects with invalid pen colors beneath the `RightEnd` native section-line group. The public view property `SectionLineColor` already reports valid black; setting ordinary view colors is therefore insufficient. The scene objects account for the three bad PDF commands.

This matches the mechanism documented in [FreeCAD issue 28688](https://github.com/FreeCAD/FreeCAD/issues/28688): Qt writes a color-space selection, exits color serialization when a pen color is invalid, but still writes `SCN`. [FreeCAD PR 31650](https://github.com/FreeCAD/FreeCAD/pull/31650/files) initializes section-line color attributes and was merged into main. The installed 1.1.4 binary still reproduces the defect. No upgrade, rebuild or modification of the installed application was performed.

## Controlled tests in Nitro

Diagnostic variants are in `output/phase3_2/experiments/`; original PDFs and projects are retained in `output/phase3_2/originals/`. Both defect corrections were tested independently before release.

| Test | Syntax issues remaining | Direct Nitro result |
| --- | ---: | --- |
| Original FC00AAB13125 | 21 | User screenshot shows missing left/lower content and end callouts |
| Only remove the 18 pathless `h` commands | 3 | Same failure reproduced directly in Nitro |
| Only correct the 3 RGB `SCN` commands | 18 | Missing drawing content restored directly in Nitro |
| Correct both defect types, FC00AAB13125 | 0 | Full sheet and diameter/radius/AF/angular callouts visible |
| Correct both defect types, FC00AAB09748 | 0 | Full sheet, diameter/AF/radius/angle callouts and hatching visible |
| Final normalized files at their usual paths | 0 each | Both actually opened and visually inspected in Nitro |

There is also an unchanged-operator rewrite control for each part. These files and their operator reports are retained; they were not separately inspected in Nitro. The closepath-only failure and color-only success distinguish the defects without relying on the container rewrite alone.

Durable screenshots of the final Nitro checks and the independent control are in `output/phase3_2/nitro/`. Nitro was closed again after testing, releasing the file handles. No Nitro rendering preferences, security settings or font settings were changed. Final full-sheet inspection used 75% zoom; the restored content was also seen at 100% and, for the final second part, 125%.

## Independent native reproduction

`scripts/build_pdf_reproducer.py` constructs a native solid cylinder of radius 5 mm and length 20 mm, with its axis along X. The end view contains a circle and an associative diameter dimension measuring 10 mm. The longitudinal view has a native extent dimension measuring 20 mm. An ordinary TechDraw annotation also contains `⌀10.00`.

| Native control | Operator diagnostics | Actual Nitro result |
| --- | --- | --- |
| `minimal/without_section.pdf` | No identified defects | Native diameter, linear dimension and ordinary diameter text all visible |
| `minimal/with_section.pdf` | Three bad RGB `SCN`, no empty `h` | Linear dimension remains; later diameter, ordinary text, section arrows and hatch disappear |
| `minimal/with_section_corrected.pdf` | No identified defects | All control content restored, including section material hatch |

These files, native SVG exports, `native_control.FCStd`, a source/association manifest, parser inventories and renderer previews are retained under `output/phase3_2/`. The cylinder is constructed independently of the two STEP samples. It establishes that their BRep defects are **not required for this PDF failure**. It does not excuse their existing Boolean-validation warnings or establish broad fastener recognition accuracy.

## PDF construction findings

- Both originals are PDF 1.4, one ANSI B landscape page, **1224 × 792 points**, or 431.8 × 279.4 mm. Media/trim boxes and page properties are preserved.
- Drawing geometry, extension lines, arrows, hatch strokes and the border remain vector paths. Native dimensions and view captions use PDF text operators, rather than interactive PDF annotations. The originals contain no image XObjects and no interactive annotations.
- Embedded Type0/CID TrueType resources include `ArialMT` and `osifont-italic`, with `/Identity-H` encoding and ToUnicode maps. The diameter glyph is supplied by the osifont fallback; numerical text uses Arial. This native font split is preserved exactly.
- Title-block and drawing-note text is principally vector outlined, explaining why it survives and does not appear in ordinary text extraction. A successful title-block render does not prove dimension-font rendering or later drawing completeness.
- There are no explicit `Tr` overrides; text uses the default filled-text mode. No evidence supports a stroke-only glyph fault. Font streams, glyph codes, mappings and widths compare unchanged after repair.
- The graphics-state stack is balanced: minimum/final depth zero, maximum three. Clipping, transforms, dash patterns, line widths and caps/joins are present and preserved. A transparency state with zero alpha exists alongside opaque states; normalization preserves both rather than making invisible template objects visible.
- The 18 empty `h` commands occur without a current subpath in template rendering. They produce Poppler warnings but are not necessary for the observed Nitro failure. Genuine path-closing operations remain intact.

`investigation.json` contains the resource inventory, embedded font hashes, operator counts, text ordering and graphic-state diagnostics. It is diagnostic evidence, not a full PDF specification validator.

## Chosen correction and alternatives

The implemented solution is a **bounded post-export repair with pypdf 6.10.0**, separate from FreeCAD geometry generation:

1. After an immediate stroking color-space selection resolving to DeviceRGB, replace an empty `SCN` with `0 0 0 SCN`.
2. Remove a pathless `h` only when no clipping operation is pending and a path-ending operation immediately follows. Preserve that ending operation and all graphics state.
3. Reparse the output and compare every other drawing operator/operand, resolved page/resource content, embedded streams, extracted text, page count, PDF version and expected dimension labels before publishing a separate candidate.

Black is defensible here: selecting DeviceRGB with `CS` resets the stroking color to its initial black. The repair makes the already-selected initial color explicit; it does not infer a previous color or assign a new drawing convention. PDF color-space initialization and path-closing behavior are defined in the [Adobe PDF reference](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.2.pdf).

The normalizer refuses in-place input replacement, ambiguous instances of these defects, unbalanced graphics state, unfinished clipping, encrypted input, interactive annotations and nested Form/Image XObjects. Unknown structures are not flattened. It is not a general repair tool, PDF/A converter, or substitute for viewer checks. Object numbers/container serialization can change; resolved resource content and valid drawing operations are checked. The PDF 1.4 header and original metadata are retained; a separate JSON audit identifies the postprocessor and hashes.

Source correction remains preferable when a tested FreeCAD release includes the upstream fix. A transient Qt pen-color experiment removed all three `SCN` defects, but its fresh native re-export omitted `⌀11.00` and the A symbols. That experiment did not isolate the scene-restoration problem from the color patch, so it cannot establish a safe production export. The internal scene approach also depends on native graphics-item structure. It was not adopted, and its incomplete PDF is explicitly diagnostic.

The installed TechDraw Python export accepts a page and filename; it does not expose a PDF-writer/color-model configuration. [Qt's QPdfWriter API](https://doc.qt.io/qt-6.8/qpdfwriter.html) has writer settings, but changing the PDF version does not initialize FreeCAD's invalid section-line colors. A global application rebuild or replacement would be a larger, unverified change.

qpdf, pikepdf, MuPDF and Ghostscript were not found in this environment. Their repair behavior was not tested. General rewriting/conversion would need fresh font, path and scale comparisons. The available pypdf library permits an explicitly constrained edit without invoking a second vector renderer. SVG-to-PDF conversion and rasterization were unnecessary and were not used.

## Preservation and validation actually executed

| Check | FC00AAB09748 | FC00AAB13125 |
| --- | --- | --- |
| Existing native dimensions retained | 11 | 23 |
| Expected labels in corrected PDF | All | All |
| Valid drawing operators/positions | Identical | Identical |
| Font streams and glyph mappings | Identical | Identical |
| Physical sheet/main scale | ANSI B / 2:1 | ANSI B / 2:1 |
| Existing detail scale | No detail | 5:1, unchanged |
| Poppler syntax warnings after repair | 0 | 0 |
| Changed pixels before/after, Poppler at 2000 px width | 0 | 0 |
| Changed pixels before/after, PDFium at 2000 px width | 0 | 0 |
| Original STEP hash | Unchanged | Unchanged |
| Editable FCStd bytes | Unchanged | Unchanged |
| Fresh native reopen/geometry/reference checks | Passed, 11 dimensions | Passed, 23 dimensions |
| Final PDF in Nitro 14.22.1.0 | Inspected complete | Inspected complete |

The same-renderer comparisons are exactly equal, not merely within an antialiasing allowance. Across Poppler and PDFium, dark-pixel counts differ due to rasterization. With a two-pixel neighborhood allowance, unmatched dark pixels are 0/3 for the first part and 0/0 for the second. Both full rendered drawings were inspected; no missing drawing region was observed. The comparison metric is not evidence of source geometric validity.

All **69 existing native regression tests passed** (`output/test_results_phase3_2_native.txt`, 310.188 s). All **10 PDF compatibility tests passed** (`output/test_results_phase3_2_pdf.txt`). The latter include independent valid/defective PDF fixtures, the actual native Unicode control, deterministic repeated output, unchanged real path closures, retained text/resources, ambiguous repair rejection and safe failure before output publication. An initial test run hit sandbox temporary-directory permissions; the fixtures now use workspace-local temporary directories and the successful rerun is recorded. No dependency was installed into FreeCAD's bundled Python.

`scripts/verify_preserved_projects.py` also reopened the actual existing final FCStd projects read only, verified geometry, views, native dimensions, centerlines and section/material associations, and checked hashes before/after. It never saved those documents. Their existing source-validation warnings remain intact. No tolerance, material, finish, manufacturing function or GD&T was assigned.

## Deliverables and repeat procedure

The usual `output/` PDFs are corrected; the usual FCStd files are unchanged. Their drawing JSON reports now carry the PDF compatibility audit. Earlier native PDFs, projects, reports and SVG scenes remain in `output/phase3_2/originals/`. `release_manifest.json`, per-part normalization audits, `render_comparison.json`, `preserved_project_checks.json`, `minimal_validation.json`, control PDFs and Nitro screenshots provide traceable evidence.

For future exports, use the separate CLI documented in README. Native FreeCAD generation continues to produce a native PDF; the compatibility stage needs an external Python with the optional pinned pypdf dependency. It does not silently change the CAD export or overwrite its source.

To repeat the Nitro check:

1. Open the final PDFs from `output/`, using **File → Open → Computer → Browse**, or Ctrl+Shift+O. Record Nitro's version. Avoid testing an older desktop copy or an already-cached tab.
2. At full-sheet zoom verify all views, border, notes/title block and both A indicators. At 100% inspect diameter glyphs, dimension arrows and section hatch. For the first part check `⌀20.00`, `⌀9.50`, `⌀9.60`, `⌀6.00`, `9.60 AF`, `6X R0.30`, `16.00°` and axial callouts. For the second check `⌀22.00`, `⌀12.70`, `⌀10.70`, `⌀11.00`, `⌀12.55`, `⌀9.00`, `12.70 AF`, radii and `115.09°`/`129.81°` in Detail B. Compare all labels against the report inventory.
3. Compare `experiments/FC00AAB13125_closepath.pdf` with `experiments/FC00AAB13125_color.pdf`. The former should reproduce the failure on the tested Nitro version; the latter should restore content despite remaining closepath warnings.
4. Compare the three `minimal/` PDFs above to isolate native text/glyph handling from section-line export. Preserve a screenshot for any discrepancy.
5. Close the PDF tabs before replacing outputs. Print with **Actual size / 100%** on ANSI B paper if checking scale. A physical print was not performed during this phase.

No manual Nitro test remains outstanding for the released files on this installed version. Other Nitro versions, Acrobat and future FreeCAD/Qt combinations still require direct testing. PDF parsing and two successful independent renderers alone do not establish universal compatibility. Source BRep defects and the Phase 3.1 engineering-review limitations remain unresolved by design; this phase repairs PDF serialization only.
