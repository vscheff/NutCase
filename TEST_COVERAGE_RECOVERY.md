# NutCase Phase 6.1: regression coverage recovery

Date: 2026-10-13. Application version remains **0.6.0**. Work branch:
`test-coverage-recovery`. This phase restores development coverage; it does not
rebuild an installer or publish a release.

## Recovery findings and provenance

The historical test **contents were found**, rather than reconstructed solely
from pass counts. The retained Codex session
`01a12182-1405-7182-984a-eaf0ee3313bc` contains the original Add/Update patch inputs.
Sequential replay recovered all 77 native, 17 PDF/publication, 35 GUI/process and
3 Windows launcher test methods, their native reference-check helper, and
several fixture/validation scripts. These counts describe the recovered code;
they were not used as a target for invented tests.

`docs/test-recovery/recovered-originals.zip` retains the JSON-decoded patch inputs,
replayed original files and event provenance before adaptation. Its SHA-256 is
`722b38a85e89b2be4bf6649b479422fb8e6cdf32bf0e2ca4c4fd41aa51914b1c`.
`docs/test-recovery/provenance.json` lists per-file hashes, session lines and patch
events. Recovery normalizes file text to LF; original on-disk byte encoding and
line endings are not claimed. The recovery script records failed contextual
replay rather than guessing. One auxiliary `validate_phase5_controls.py` update
has missing context, so its retained snapshot is incomplete. No recovered test
module has a replay failure. The deleted GUI `recorded_source.json` fixture and
the old minimal Unicode PDF reproducer were **not recovered**.

The Recycle Bin retained the Phase 1–5 review documents and `docs/CLEANUP.md`.
Copies under `docs/test-recovery/` preserve their historical wording. The cleanup
report explicitly records removal of the development suites and fixtures on
2026-10-12. Those reviews corroborate historical behavior, but their reported
results are not counted as new test execution.

| Recovery location | Result |
| --- | --- |
| Git commits, branches, tags, reflogs, stash | Initial commit/push only; no tags or stash; no historical test tree |
| Unreachable Git objects | 57 objects inspected; no test/fixture paths in their trees; blobs were unrelated application/doc changes |
| Recycle Bin | Project-specific metadata/payloads inspected; historical reviews recovered, no test directory payload found |
| Windows File History | Local configuration directory absent |
| Shadow-copy interface | `Win32_ShadowCopy` query failed with initialization failure; backup absence is not established |
| Codex task artifacts/workspaces | No attached artifacts or additional worktree/artifact directory found; four relevant session records searched |
| Prior project directory | Old `Projects/FastenerDrawing` contains output only; no test sources |
| Phase 3/4/5 outputs | Most historical artifacts deleted; retained diameter scripts and Phase 6 verification harness inspected |
| Source distribution | Existing 0.6.0 source ZIP contains only `tests/test_packaging.py` |
| Scoped local backup/archive searches | Project-name/test-file searches in Projects, repos, Desktop, Documents and Downloads found no additional suite snapshot |

See `docs/test-recovery/search-results.json`. This was a scoped local search;
inaccessible system history, remote backups and unmounted volumes were not
searched. Recovery sources, supplied STEP files, existing release manifests,
candidate installer and source distribution were not changed. Initial dirty
work and artifact hashes were recorded under `build/test-recovery/`.

## What was restored, adapted and newly designed

| Suite/support | Provenance | Behavior |
| --- | --- | --- |
| `tests_native/test_analysis.py` | Recovered, adapted | Actual STEP roundtrip/hash integrity; valid/open/invalid/assembly reporting; axis under rotation/translation; head/flange/hex geometry; native helical evidence and coil rejection; withheld unsupported roles |
| `tests_native/test_drawing.py` | Recovered, adapted | Third-angle frames, optional views, A4/ANSI layout, native envelopes, signature changes, title-block escaping, actual export/save/reopen, failure without PDF |
| `tests_native/test_dimensions.py`, `native_reference_checks.py` | Recovered, adapted | Known flange/bore/AF/length, ambiguity refusal, collision spacing; independently repeated values and persisted native associations; seven adversarial reference/value/presentation changes |
| `tests_native/test_features.py` | Recovered | External/internal steps, cone angle/extent, polygon wall spacing, recess, fillet radius, noncircular opening and offset bore |
| `tests_native/test_comprehensive.py`, `test_quality.py` | Recovered, adapted | Dedup needs geometric locus, spanning dimension chains, section material and enclosed voids, refusal of open boundaries, centerlines, compact angle anchor, detail-view placement and four independent part families |
| `tests_native/test_configuration.py` | Recovered | Stable identity survives transient renumbering; same value at a changed locus does not rebind; source changes, explicit suppression, three modes, reviewed frame override and schema rejection |
| `tests_native/test_presentation.py` | Newly designed from retained diameter probe | Seven actual diameter/scale cases; native trimmed labels, filled-arrow clearance, save/reopen and preserved geometry; produces native embedded-font/diameter PDF control |
| `tests_pdf/test_compatibility.py` | Recovered, adapted | Operandless RGB SCN and pathless h repair; deterministic/idempotent output, real path/text/resource preservation, ambiguous color/clip/state failures; optional fresh sample/native glyph controls |
| `tests_pdf/test_pipeline.py` | Recovered, adapted | Real temporary files and truncated PDF; native/verification fault injection; old manifest preserved, atomic commit failure, unreadable final children, exact artifact hashes, lock refusal |
| `tests_pdf/test_gates.py`, `test_concurrency.py` | Newly designed | Valid RGB operations, encryption/annotation/XObject refusal, prior target preservation, page/label/sheet gates, two actual renderers, config/date rejection, two competing OS processes and output lock ownership |
| `tests_gui/test_state.py`, `test_interface.py` | Recovered, adapted | Source-bound selection, history/corrupt-policy preservation, preview/export validation, async generation/completion/cancel states, controls, stale binding, explicit reset, Qt PDF preview |
| `tests_gui/test_process_control.py`, `test_file_opener.py`, `test_runtime_probe.py` | Recovered, adapted | Actual Windows descendants, worker/GUI crash containment; bounded responsive file-association dispatch; real PowerShell 5.1 dependency probes and failure markers |
| `tests_gui/test_refinements.py`, `test_transport_failures.py` | Newly designed | Picker filtering/space/read-only UI, degree/mm/in precision, dates, browse/reload, implicit extensions, wrong suffix rejection, title/mode tooltips, missing worker, split UTF-8 pipe reads and error framing |
| `tests_gui/test_export_failures.py` | Newly designed | Corrupt staged copies and locked destination replacement cannot destroy an existing exported file |
| `tests_gui/test_cad_workflow.py` | Newly designed from retained Phase 6 harness | Real QProcess CAD/PDF/preview/export matrix, three modes, explicit Custom inclusion/exclusion, regeneration and restart persistence, optional views, cancellation/failure preserving current release |
| `tests_launchers/test_windows_launcher.py` | Recovered, adapted | Real PowerShell 5.1 and NutCase.cmd startup, standalone dependency probes, preserved failure status |
| `tests/test_packaging.py` | Existing, unchanged | All 13 packaging/data/process/publication boundary tests retained |
| `tests_support/build_quality_fixtures.py` | Recovered constructors, adapted output paths | Four rotated synthetic STEP families with known lengths and hashes; writes isolated test output |
| `tests_support/build_gui_fixture.py`, GUI JSON fixture | Newly designed replacement | Independent native hollow-pin measurements; explicitly mocked unsupported/warning/publication flags, no supplied model data |
| `scripts/run-tests.py` | Newly designed | Runtime separation, full/fast/suite commands, structured results and explicit skips |

The recovered Stage B “basic” CLI four-dimension behavior is intentionally tested
separately from the newer configuration Basic policy. They are distinct existing
interfaces. Assertions about removed GUI orientation controls and the former
details box were replaced with current metadata and full-picker assertions.
Native frame overrides remain covered through the configuration/native API.
Unicode test/evidence reads are explicitly UTF-8.

Tests deliberately distinguish source values, inferred functions, selected
candidates and drawable/verified dimensions. Mock GUI verification flags are
never counted as CAD/PDF evidence. The public fast suites require no prior output
archive and no supplied STEP assets. Local-sample tests require `--samples` and
skip explicitly if the pair is unavailable. No supplied BRep or STEP is copied
into a committed fixture or CI artifact.

The Windows cancellation fixture now waits for its descendant PID file rather
than assuming it starts within 0.7 seconds; the readiness-based cancellation and
both crash-containment tests were rerun successfully. Offscreen GUI bootstrap
loads installed fonts so widget layout checks use actual text metrics.

## Commands and runtime separation

The README documents external test-environment setup and every suite command.
Use `scripts/run-tests.py --suite fast`, `pdf`, `gui`, `launchers`, `packaging`,
`native` or `full`. FreeCAD's bundled Python runs `native`; `full` requires
`--freecad-python` and external Python. Poppler/PDFium integration additionally
needs `--poppler`. Add `--samples` for optional local assets. Choose a fresh
`--results` directory for an independent evidence run.

`requirements-tests.txt` is separate from shipped runtime/build entry points.
Tests use standard-library unittest with the production Qt/PDF dependencies.
They are not added to the frozen module graph. The new read-only CI workflow
runs the practical external Windows subset on a fresh checkout; it does not
build an installer or publish a release. FreeCAD, Poppler integration and
private-model checks are local gates. No hosted workflow run is claimed.

## Execution results

**166 distinct test methods passed across the complete suite run and targeted
reruns.** This is not a claim that the first full invocation passed: its native,
GUI, launcher and packaging suites passed, while two independent PDF controls
failed. Corrected fixtures and the complete PDF suite were then rerun successfully.
Two late-added export controls were executed separately and included in the final
GUI rerun. No production application code was changed to make tests pass.

| Category | Current methods | Executed result / evidence |
| --- | ---: | --- |
| Native FreeCAD geometry/drawing | 78 | Full suite 78 passed, zero skips; updated native annotation/arrow control additionally rerun and passed |
| PDF/publication/config/process competition | 24 | Final complete PDF rerun 24 passed, zero skips, including actual Poppler/PDFium and native glyph controls |
| GUI/process/export | 48 | Final font-aware fast run: 47 passed, one explicit CAD-matrix skip; that matrix passed in the preceding full run, along with the other then-existing 45 GUI methods |
| Windows launchers | 3 | All three passed through real Windows PowerShell 5.1/NutCase.cmd startup and failed-launch propagation |
| Existing packaging | 13 | All 13 passed; original test file checksum unchanged |

Native runtime: **FreeCAD 1.1.4**, bundled Python 3.11.14. External full-run
runtime: pinned build environment **CPython 3.13.16**, **PySide6 6.12.0**,
**pypdf 6.10.0**, **pypdfium2 5.14.0**, packaged **Poppler 26.09.0**.
The prepared development Python 3.12.14 was also used for initial recovery checks.
Python source compilation and `git diff --check` passed; existing LF/CRLF notices
are not whitespace failures. CI was authored but not executed on GitHub.

| Real GUI/QProcess matrix source | Basic dimensions | Comprehensive dimensions | Custom dimensions | Exit |
| --- | ---: | ---: | ---: | --- |
| Independently constructed, rotated countersunk pin | 2 | 4 | 1 | 0 |
| Local FC00AAB09748 | 6 | 11 | 1 | 2, engineering review required |
| Local FC00AAB13125 | 7 | 23 | 1 | 2, engineering review required |

All nine generations passed native save/reopen, reference/measurement checks,
automatic normalization, vector/label/page verification, zero-diagnostic Poppler,
PDFium comparison, Qt PDF preview render and hash-verified PDF/project export.
For each source, Custom selections and exclusions survived restart, fresh
analysis and actual regeneration. Disabling optional views left just the two
required views. Cancellation returned 3, cleared preview and preserved the
current manifest; invalid native-executable failure returned 1 and likewise
preserved it. The six local-model outputs remain preliminary because the original
Boolean-validation problems remain present. Comprehensive presentation retained
ANSI B, 2:1 scale, 11/23 measurements, native rivet hatching and the spring nut's
verified-boundary fallback. Both Comprehensive Poppler renderings were visually
inspected: all views, rounded labels, separated diameter arrows, section material
and localized opening-detail angles were visible.

Fixture failures were useful distinctions: native SVG template text is outlined,
so searchable ordinary text must come from a native annotation; extracted spaces
can be tabs. The packaged Poppler reports missing Symbol/ArialUnicode display
fallbacks for the unembedded Helvetica control. The renderer gate was retained,
and the new minimal vector fixture uses installed font bytes embedded by Qt.
Windows offscreen Qt can enumerate no fonts, so fixture/GUI bootstrap explicitly
loads installed fonts. No font binary is committed. These changes repair test
controls, not the PDF normalizer or CAD implementation.

Original STEP checksums remained unchanged:

```text
FC00AAB09748 f3d97d4cab35e9a0443a20ff4c61d68d488860eaa27936d7200dc907d4264264
FC00AAB13125 546fafd4f1317079f929c56af69d96cc51c4450bc8e66e8782b79e7ac5860093
```

The installer, original source ZIP and `tests/test_packaging.py` match their
pre-recovery hashes. Existing generated releases were not replaced. Retained
matrix/control drawings live under isolated `build/test-results/` directories;
recovered native tests also use new temporary subdirectories under `tmp/` and
`output/test_work/`, cleaning only their own newly created temporary files.
No installer build,
GitHub publication, version bump, source healing or geometry-recognition expansion
was performed.

`docs/test-recovery/verification-results.json` and `test-inventory.json` retain
the final summarized execution and current method inventory. Detailed logs,
intermediate native PDFs, projects, manifests, renderer PNGs and matrix results
remain under `build/test-results/full/`, `presentation-final/` and
`gui-final-fonts/`. The original failed full result is retained as `full.json`;
later successful PDF evidence is `pdf.json`, with logs under
`build/test-recovery/pdf-corrected.log`. Do not infer final success from the earlier
failed aggregate. `build/test-recovery/` also preserves the initial adaptation
errors rather than deleting them.

## Remaining coverage and engineering limits

- Synthetic pin/bolt/shoulder/countersunk/slotted/grooved/stepped-hollow fixtures
  are independent known-geometry controls, not proof of real-world generalization.
  Additional independently supplied STEP models remain necessary.
- Source invalidity withholds recognition, and actual open/assembly imports are
  exercised. One invalid-BRep recognition branch uses an injected validation
  record; it is not a corpus of damaged STEP encodings.
- Native section/material tests verify exact boundaries, cavity exclusion and
  complete hatch segments. Raster agreement and the existing rendered-hatch
  diagnostics cannot establish every native stroke as an engineering-approved
  boundary; visual/material review remains required.
- Live Nitro rendering is not automated or newly verified. Poppler and PDFium
  agreement plus narrow audited repair are compatibility gates, not a universal
  PDF validator. General unknown operators, arbitrary resource graphs, pattern
  colors and every malformed encoding are not exhaustively tested.
  The packaged Poppler's fallback-font warnings on unembedded standard-font PDFs
  remain an observed limit; current FreeCAD output embeds its fonts.
- Degree/mm/in formatting helpers are tested; native drawings currently use mm.
  No native inch drawing/export support is claimed from string-format tests.
- The GUI uses automatic orientation; native configuration/frame overrides are
  tested. Interactive DPI/multi-monitor, physical hover/drag/file dialogs,
  real external viewer rendering, clean-machine installer lifecycle and genuine
  old-version upgrade are outside this regression run.
- Mock association helpers prove request/error handling and responsiveness;
  they do not prove a viewer renders a drawing. Real worker/process containment
  uses Windows Job Objects and test-owned descendants.
- Locks are deliberately not stolen. Hard-crash/stale-lock manual recovery and
  power-loss/network-filesystem durability are not established by injected
  rename/write failures or the competing-process test.
- The pipeline still generates one sheet. Multi-page UI navigation and
  separate-sheet production layout are not claimed. This phase adds no feature
  recognition, drawing tolerances, manufacturing specifications or GUI feature.
