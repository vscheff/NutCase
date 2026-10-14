# Phase 6: NutCase Windows candidate review

Historical review: Phase 6.1 restored regression suites; see TEST_COVERAGE_RECOVERY.md.
Phase 6.2 acquired dependency sources/notices and added an inspected inventory and
release gate; see PHASE6_2_LICENSING_REVIEW.md. Claims below describe the earlier run,
including suites that were absent at that time.

Date: 2026-10-13. Version: **0.6.0**. Status: **local acceptance candidate**.
No GitHub release was published. Final human acceptance and dependency
redistribution review remain required before public distribution.

## Deliverables

- `artifacts/NutCase-0.6.0-windows-x64-setup.exe`: versioned, unsigned per-user installer.
- `dist/NutCase/NutCase.exe`: frozen application; keep the entire adjacent directory.
- `artifacts/NutCase-0.6.0-source.zip`: actual working application source and build scripts.
- `artifacts/SHA256SUMS.txt`: installer and application-source archive checksums.
- `artifacts/nutcase-build.json`: exact runtime/tool inputs and Poppler binary hashes.
- `scripts/bootstrap-build.ps1` and `scripts/build-windows.ps1`: pinned build procedure.
- `scripts/verify-windows.ps1`, `scripts/verify-installer.ps1`, `tests/test_packaging.py`:
  executable verification and packaging/safety regressions.
- `docs/WINDOWS_PACKAGING.md`, `docs/INSTALLATION.md`, `docs/LICENSING_AUDIT.md`,
  `docs/RELEASE_NOTES_0.6.0.md`, `docs/RELEASE_READINESS.md`: build, user and release documentation.

The source archive is **application source**, not a complete corresponding-source
package for every dependency. Supplied STEP assets are excluded from installer
and source archive pending ownership/redistribution review; originals remain in
the repository. Existing dirty work and prior generated results were retained.

## Architecture and scope

PyInstaller 6.22.3 produces a directory bundle with a windowed `NutCase.exe` and
explicit `NutCaseWorker.exe` actions. Inno Setup 7.1.0 wraps it in a conventional
installer with a stable AppId, Start Menu shortcut, optional desktop shortcut
and uninstall. Standard temporary executable icons remain; no design was invented.

CPython 3.13.16, PySide6/Qt 6.12.0, Qt PDF 6.12.0.140 and the pinned PDF libraries
are bundled. Poppler 26.09.0's pdftoppm, recursive PE imports and upstream data
live in a separate DLL directory. FreeCAD is not bundled. Discovery checks its
native architecture, version and Part/TechDraw/GUI imports; 64-bit FreeCAD 1.1.x
is the accepted branch, with **1.1.4** tested here. Users need no Python, pip,
virtual environment, environment-variable edits or PowerShell commands.

The frozen worker invokes FreeCAD's own Python against staged `native-src`.
External launch environments and DLL search state are isolated from frozen Qt.
QProcess protocol, job containment, source-bound configurations, exit 2 semantics,
atomic manifests, native/PDF checks and previous-release preservation remain active.
Mutable defaults move to `%LOCALAPPDATA%\NutCase`; native preferences and scratch
SVGs use the cache. Explicit output/settings paths inside the installation are
rejected. CAD recognition and dimensioning algorithms were not redesigned.

## Build and boundary verification

- Pinned tool archives and hash-locked wheels were downloaded, verified and used
  in a separate build environment. No Codex Python runtime is bundled or required.
- Candidate builds completed, including the actual frozen GUI/event loop, worker
  diagnostics, JSON job dispatch and expected missing-manifest failure smoke checks.
- **13/13 packaging tests passed**, including atomic publication/hash checks,
  exit 2 interpretation, configuration history/restart, pre-publication cancellation,
  child-environment isolation and installed data/resource paths.
- Real Windows subprocess tests confirmed cancellation and an abrupt worker exit
  terminate both a contained native fixture and its descendant. A forced crash of
  the full interactive GUI during real CAD processing remains a separate acceptance test.
- A frozen GUI with an invalid explicit FreeCAD path still launched and displayed
  the installation URL and portable-runtime guidance. No generation was claimed.
- Fresh CPython/Poppler extraction and a new build environment were bootstrapped
  offline from the verified cached archives/wheels in `build/bootstrap-clean`.
  The already-tested Inno compiler was reused for that probe. A fresh checkout
  and GitHub-hosted workflow run were not performed.
- Python compilation, PowerShell parsing and `git diff --check` passed. Git's
  LF/CRLF notices are line-ending warnings, not failed checks.

Issues found during actual freezing were fixed: an entry-point filename shadowed
the GUI package, ambient developer PATH supplied incompatible DLLs, and native
dimension settling tried to write a scratch SVG under the application directory.
Build guards now check the required module graph and reject unpinned binary origins.
Windows PowerShell's `.nupkg` extraction restriction is handled through ZipFile.

## Two-model native/PDF/GUI regression

The frozen GUI harness ran with PATH restricted to Windows System32 and no
development Python overrides. It imported copies from arbitrary paths containing
spaces, `Ω` and `&`, used actual QProcess workers and retained source hashes.

| Supplied model | Analysis candidates | Basic dimensions | Comprehensive dimensions | Custom dimensions |
| --- | ---: | ---: | ---: | ---: |
| FC00AAB09748 rivet nut | 24 | 6 | 11 | 1 explicit selection |
| FC00AAB13125 spring nut | 53 | 7 | 23 | 1 explicit selection |

All **six** modes completed with **exit 2**, correctly treated as published
preliminary drawings requiring engineering review. Each passed native saved-project
reopen/reference/measurement checks, PDF normalization/label checks, one-page
vector-only audit, zero Poppler diagnostics and Poppler/PDFium comparison. Qt PDF
loaded/rendered each sheet; PDF and FCStd export copies matched published hashes.

Both source-bound Custom policies survived window restart and fresh analysis.
For each model, cancellation during native dimension/export work returned 3,
cleared the preview, removed the generation lock and preserved the prior manifest.
An invalid native executable returned 1 with the same preservation guarantees.
The original supplied STEP hashes remained unchanged.

Evidence: `artifacts/verification/frozen-regression.json` and retained per-run
reports under `artifacts/vdata/drawings/`. The six generation checks also passed
using the installed worker and installed Poppler while writes to the installation
were denied by an inherited ACL. Qt preview screenshots are retained as
`artifacts/verification/0-*.png` and `1-*.png`; the rivet Basic and spring
Comprehensive screenshots were visually inspected and contained the actual sheets.

## Installer lifecycle validation

The disposable target was `artifacts/Install Ω & Space`, with real per-user Inno
registration and shortcuts. The script first refused to overwrite any existing
NutCase registration. Actual installed GUI launch, name/version, Start Menu and
optional desktop shortcut targets passed. A write probe confirmed that the ACL
really blocked installation writes; installed startup and all six native modes
then worked with that restriction.

The full installed run in `installed-regression.json` records six successful
generations, both restart/cancellation/failure checks and original STEP integrity,
but its overall status is **failed** because the subsequent external FreeCAD launch
hit a Boolean-versus-tuple Qt API mismatch. That defect was fixed and the candidate
rebuilt. A targeted rerun, `external-opening.json`, passed using the installed
worker: Windows accepted the PDF association request and FreeCAD accepted detached
launch of the retained FCStd. Viewer rendering and interactive CAD inspection are
not claimed. The CAD/PDF pipeline did not change after its six-mode installed run.
Test FreeCAD instances were closed after dispatch checks so the console-driven
lifecycle harness could continue.

The corrected candidate's `installer-lifecycle.json` is **passed**. Same-version
update, uninstall, reinstall/startup and final uninstall each preserved the SHA-256
of **663 user files** (144.4 MiB of drawings, policies/history, exports, input copies
and diagnostic results; disposable cache/log files excluded). Final uninstall
removed the registration, application executable and tested shortcuts. No recursive
user-data deletion is authored. A genuine old-version-to-new-version upgrade is
still a human acceptance item.

One verification-tool issue was also corrected: WScript.Shell's ANSI shortcut
reader converted `Ω` to `O`. The Unicode `System.Link.TargetParsingPath` property
showed that the actual installer shortcuts were correct.

The default-path startup reported `%LOCALAPPDATA%\NutCase` and its drawings
default correctly. Its temporary diagnostic settings folder resolved under this
host's Codex MSIX LocalCache, consistent with Windows AppData virtualization.
That check establishes the path policy, not ordinary Explorer-launched storage
behavior. The native and lifecycle tests used an explicit workspace data root.
Clean-machine Start Menu launch and default-data persistence remain acceptance
items. See [Microsoft's AppData virtualization description](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes).

## Licensing and public-release gates

The owner explicitly selected **GPL-3.0-or-later**; root `LICENSE` and documentation
record it. Full supplied runtime-wheel notices, PSF/Inno licenses, GPL/LGPL texts,
metadata, Poppler data notices and file hashes accompany the candidate.

`docs/LICENSING_AUDIT.md` identifies exact Qt/PySide/Qt PDF corresponding-source,
copyright and third-party-notice work, Poppler Windows recipes/builds/DLL notices
and Microsoft runtime redistribution review still required. The inspected Qt
wheels' commercial-only notice files are not treated as proof that open-source
license alternatives in their metadata are unavailable. Merely bundling generic
GPL text or linking an upstream homepage is not claimed to satisfy source obligations.

The tag/manual GitHub Actions workflow builds and uploads candidates with read-only
repository permissions. It has no release publication step or signing secrets.
The installer is unsigned; SmartScreen and enterprise application-control behavior
require acceptance testing. Bit-for-bit reproducibility is not claimed.

## Limits and handoff

- No clean Windows VM or separate Windows installation was available. PATH
  isolation on this development host is not equivalent to clean-machine validation.
- Historical native/PDF/GUI regression suites and synthetic fixtures were already
  absent from the supplied tree. They could not be rerun; new tests and real
  generation gates do not establish equivalent historical coverage.
- Automatic renderer agreement is not engineering approval. Existing source
  Boolean/section limitations and manual visual review requirements remain.
- Physical preview controls, DPI/multi-monitor behavior, interactive installer
  choices, real version upgrades, external viewer rendering and interactive native
  FreeCAD inspection require human acceptance.

Use `docs/RELEASE_READINESS.md` for the remaining acceptance/publication gates.
