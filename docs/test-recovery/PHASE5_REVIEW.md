# Phase 5 review: Windows desktop workflow

> Historical review: the requested directory cleanup removed archived development outputs, regression suites, synthetic fixtures and investigation scripts. Artifact paths and test commands below record earlier work; they are not all present in this runtime-focused directory. Current usage is in README.md; preservation and post-cleanup checks are in [docs/CLEANUP.md](docs/CLEANUP.md).

Implemented and verified on 2026-10-12. Phase 5 adds a PySide6 desktop application around the reviewed Phase 4 pipeline. Geometry recognition, native dimension construction, section material verification and PDF correction algorithms remain unchanged. No installer or additional feature-recognition work was undertaken.

## Delivered behavior

- Import `.step`/`.stp` files from arbitrary locations and perform a fresh native geometry analysis. The filename, location tooltip, recognized-feature summary and extended Boolean problems are exposed.
- Configure Basic, Comprehensive and Custom using the existing JSON schema: individual stable source identities, automatic/explicit paper and scale, optional isometric/opposite-end/section/opening-detail views, title/number/revision/date, and verified axis/up overrides.
- Custom candidate checkboxes show measured values, units and source status. The row inspector exposes the full description and unresolved reason. Measurements cannot be edited through the interface. Source measurement is explicitly distinguished from subsequent CAD reference verification.
- Generate asynchronously through a QProcess external worker. Display actual stage names, indeterminate activity, messages, errors and safe cancellation; exit 2 is a completed preliminary drawing requiring engineering review.
- Verify the current manifest, expected run/source/release paths, every recorded file checksum, PDF verification and native project reopen evidence before loading the final normalized PDF. Native intermediate PDFs remain in the retained run.
- Embedded Qt PDF preview provides page navigation, zoom and fit. Open the PDF using the Windows association, open the FCStd in native FreeCAD, and make checksum-verified export copies without changing immutable releases.
- Preserve release history. Failed/cancelled new processing clears both the preview and prior drawing-verification text; an earlier drawing requires explicit selection and is labeled with its historical run and drawing mode.
- Persist configurations by normalized source location. Fresh analysis gates restoration. Changed bindings or invalid saved identities disable generation, retain the old policy, and require an explicit new configuration. Saving replacement policies archives previous bytes, including corrupt old JSON.
- Separate PDF success, reopened CAD measurement/associativity, unsupported candidates, unrecognized semantic roles, thread classification, source geometry problems and unassigned engineering approval in the review panel.

## Runtime separation and implementation

The detected FreeCAD installation is 1.1.4 with bundled Python 3.11.14, Qt 6.8.3 and OpenCascade 7.8.1. The GUI uses external Python 3.12.14 with PySide6/Qt PDF 6.12.0. Its pipeline dependencies are pypdf 6.10.0, pypdfium2 5.14.0 and Pillow 12.3.0. Qt plugin/Python path variables are stripped before launching native processes. No dependencies were installed into FreeCAD's bundled environment.

`Launch Fastener Drawing.cmd` and `scripts/launch-gui.ps1` discover/probe FreeCAD and launch `scripts/fastener_gui.py`. Runtime paths can be overridden. The existing project `.venv-gui` is prepared. Setup, including the development runtime's missing-ensurepip workaround, is documented in [desktop usage](../DESKTOP_USAGE.md).

| Component | Responsibility |
| --- | --- |
| `fastener_gui/window.py` | Import/configuration/review controls and workflow transitions |
| `state.py` | Source-bound state and configuration storage/history |
| `controller.py`, `scripts/gui_worker.py` | Nonblocking JSON-line worker transport and existing pipeline invocation |
| `outputs.py` | Manifest/history/path/checksum verification and safe export copies |
| `preview.py` | Final normalized PDF display |
| `file_opener.py`, `scripts/open_system_file.py` | Bounded external Windows default-viewer dispatch |
| `theme.py` | Consistent readable Qt palette independent of the Windows dark theme |
| `fastener_drawing/process_control.py` | Cooperative cancellation and Windows process containment |

The backend change is an optional process-control argument and real stage/cancellation boundaries in `pipeline.generate`. Existing CLI callers keep their prior execution path. Native processing still runs in FreeCAD's child interpreter; normalization and verification remain external.

The GUI owns a Windows job containing its backend worker. The worker owns a nested job containing its descendants; native commands are contained separately for cancellation. Actual Windows tests confirmed that cancellation, worker crash and abrupt GUI process death stop the appropriate descendants. Normal closing while busy waits for cancellation. External viewer applications are intentionally independent of the drawing worker.

Publication retains the single atomic manifest commit. Cancellation checkpoints precede the commit; there is no post-commit cancellation check that could misreport an already published release as cancelled. The publish stage disables further cancellation. Native logs and retained diagnostics survive ordinary cancellation.

## Executed automated verification

| Suite | Actual result | Evidence |
| --- | --- | --- |
| Existing native regression suite | 77 passed; 407.619 seconds | `output/test_results_phase5_native.txt` |
| Existing external PDF/pipeline regression suite | 17 passed; 15.821 seconds | `output/test_results_phase5_pdf.txt` |
| GUI/state/output/process/viewer tests | 32 passed | `output/test_results_phase5_gui.txt` |
| Real offscreen Qt + QProcess + FreeCAD matrix | Both samples in all three modes passed | `output/phase5/integration_results.json` |
| Additional native controls | External source, changed-source binding and output lock passed | `output/phase5/controls_results.json` |
| Artifact/material audit | All six retained matrix releases passed | `output/phase5/release_audit.json` |
| Small-window Qt scaling check | 960 x 720 logical window at 150%; real PDF and evidence controls available | `output/phase5/scaling_results.json` |

The GUI suite uses mocked backend behavior and portable recorded source data for fast widget/state checks, actual QProcess stubs for responsiveness and exit codes, and actual Windows descendants for lifetime tests. Its blank PDF/placeholder project fixtures are explicitly test-only and require no prior generated Phase 4 output. The default-viewer suite checks success wording, failure, timeout and event-loop activity using bounded subprocess stubs. These are distinguished from the actual native matrix below.

| Supplied model | Basic | Comprehensive | Custom |
| --- | ---: | ---: | ---: |
| FC00AAB09748 | 6 dimensions | 11 dimensions | 5 explicitly selected dimensions |
| FC00AAB13125 | 7 dimensions | 23 dimensions | 6 explicitly selected dimensions |

All six real matrix cases completed with exit 2, loaded one-page normalized PDFs in Qt, validated manifests/hashes, and produced matching PDF/FCStd export copies. Exact custom stable-identity sets were checked; suppressed identities did not reappear. Comprehensive candidate IDs, native measurements, dimension positions and view positions matched the Phase 3.2 baseline. Event-loop heartbeats continued throughout; the largest recorded gap was approximately 78 ms.

Both saved custom policies restored after fresh native analysis. Both invalid saved-reference tests retained the old JSON bytes and disabled generation until explicit reset. Actual native cancellation during drawing generation preserved the previous manifest, removed the ordinary generation lock, and cleared the preview. An actual missing FreeCAD executable failed with exit 1 while preserving the previous current release and clearing the preview.

The additional controls generated a one-dimension drawing from a copied STEP outside `input/`. Replacing only that disposable copy with an independently constructed FreeCAD cylinder changed the native fingerprint, retained the incompatible old selections and blocked generation. An explicit fresh save archived the previous policy. An existing test lock was not stolen and did not change the current manifest. These controls ran again after the final process-containment changes.

## Interactive and visual checks

The actual Windows application was opened and exercised through computer use. This included Browse/Analyze, changing to Custom, checking overall length and flange diameter, generating the second model, loading its normalized PDF, and exporting PDF/FCStd through actual file chooser dialogs. Both export checksums matched the published files. **Open In FreeCAD** opened the native project and displayed its drawing; the test document was closed without saving its in-memory recomputation changes. The published file checksum remained valid.

The app was restarted, the model was reanalyzed, the compatible Custom selections restored, and **Open Current Release** revalidated/reloaded the current PDF. The updated candidate inspector was exercised and captured in the actual Windows screenshot used in README. A light/dark-theme contrast defect and an excessively wide unresolved-reason column were corrected during this review. Qt file choosers now use the same palette and scaling as the application.

The Windows default PDF association is **MSEdgePDF**, rather than Nitro. The original synchronous open request was followed by computer-use input timeouts; that evidence does not independently prove where the stall occurred. Default opening was therefore isolated in an external helper with a 15-second bound. The final real helper returned an accepted-by-Windows status. Desktop automation could not confirm an Edge window rendering the document or complete all subsequent native input checks. Default-viewer rendering remains **unverified**; embedded rendering and FreeCAD opening were verified. This phase makes no new claim of Nitro interactive validation. The Phase 3.2 correction and regression gates remain intact.

Both six-case Poppler/PDFium contact sheets were visually inspected, together with both full-resolution comprehensive pages. Expected views, labels, selected dimensions, section boundaries and hatching were present. No new missing content or layout regressions were observed. The independent PDF gates retain structure, label and renderer diagnostics. Verified material hatching remains native for FC00AAB09748 and uses the existing verified-boundary material overlay for FC00AAB13125. Its documented native section-face conversion limitation is retained.

The 150% scaling check used Qt's offscreen platform with explicitly loaded installed Windows fonts and an actual verified release. It is a layout check, not a physical monitor DPI-switch test. Small windows require scrolling and row inspection for long descriptions. More physical multi-monitor/DPI testing remains appropriate before distribution.

## Preserved engineering limitations

- The source extended Boolean checks still report 55 problems for FC00AAB09748 and 72 for FC00AAB13125. Neither original STEP was altered. All created dimensions in the six audited matrix projects passed measurement and reference checks after native reopen.
- Source measurement and inferred feature function remain distinct. No nominal dimensions, tolerances, thread designations, materials, finishes or GD&T are assigned by the GUI.
- Source binding is intentionally conservative. Compatible native fingerprints/candidate sets can preserve configuration; changed identities are not guessed or remapped to similarly valued geometry.
- Custom inclusion requests do not guarantee that every candidate has sufficient support, suitable view geometry or nonredundant placement. The selected/unresolved reasons remain visible in the report.
- PDFs are verified preliminary drawings. Engineering approval remains unassigned even when PDF and CAD checks pass.
- These two supplied models and synthetic fixtures do not establish real-world generalization across fastener families. Additional independently supplied STEP parts remain necessary.
- Cancellation of native work is prompt. PDF normalization/verification can finish their current operation before a stage checkpoint notices cancellation. Crash recovery may leave a stale output lock; manual PID/run inspection is required before removing it. No silent lock recovery is introduced.
- The pipeline currently produces one drawing sheet; the preview supports page navigation, but a real multipage output was not exercised in this phase.
- No installer, standalone executable packaging, Qt deployment/licensing audit, automatic dependency downloader or large-scale recognition work is included. The PySide6 umbrella dependency installs unused WebEngine components; distribution size should be addressed during packaging.

## Deliverable locations

Use the current manifest for the selected output directory; independent historical root aliases are still not rewritten. The six integration exports are in `output/phase5/exports/{basic,comprehensive,custom}/`, with full immutable releases and diagnostics in `output/phase5/drawings/`. The subsequent interactive two-dimension drawing is a separate retained release, now current for FC00AAB13125 in that validation directory; the six matrix run IDs remain explicitly recorded and auditable.

Readable usage/setup instructions are in `docs/DESKTOP_USAGE.md`, and actual Windows screenshots are under `docs/screenshots/`. Source code and regression/integration scripts are retained alongside the existing backend. Phase 5 stops here.

## Launcher correction after user review

The initial shell checks used PowerShell 7, while the double-click batch file invokes Windows PowerShell 5.1. Its native argument handling stripped double quotes in embedded Python `-c` probes, causing `NameError: name 'GUI_RUNTIME_OK' is not defined` and a misleading missing-dependencies error. The FreeCAD and external PDF probes had the same defect. All three now invoke a standalone Python probe script. The prepared dependencies did not require reinstallation.

The batch launcher now preserves the Python/PowerShell failure status across its pause prompt. A diagnostic `-StartupCheck` exercises actual dependency imports, native FreeCAD discovery and Qt window/event-loop initialization with isolated temporary settings, then exits without generation.

Executed follow-up validation on 2026-10-12: **35 GUI/process tests passed**, including real Windows PowerShell dependency probes; **3 Windows launcher integration tests passed**, covering full startup via Windows PowerShell 5.1 and the actual batch file, plus failed-launch status propagation. Logs: `output/test_results_launcher_fix_gui.txt` and `output/test_results_launcher_fix_windows.txt`. These checks verify startup, not another interactive workflow or drawing generation. The native geometry and PDF algorithms were unchanged; the earlier native/PDF suite and six-case generation results above were not rerun for this launcher correction.
