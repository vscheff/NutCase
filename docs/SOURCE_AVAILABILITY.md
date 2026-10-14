# NutCase 0.6.0 source availability

The chosen delivery plan is a **co-located binary and source release**, not a
written offer. Do not publish the installer while the licensing report has
BLOCKED or REQUIRES HUMAN/LEGAL REVIEW findings.

After final approval, attach the exact Windows installer, refreshed application
source, dependency source/evidence ZIP, SPDX inventory, reviewed inventory,
source manifest, compliance reports and SHA256SUMS to the same GitHub Release.
Downloads must be free and directly accessible without an account. Release notes
must link directly to each source artifact next to the installer download.
A generic repository homepage or current HEAD is insufficient.

Prepared local files are under `artifacts/phase6_3/release/`:

- `NutCase-0.6.0-windows-x64-setup.exe`: trimmed local candidate.
- `NutCase-0.6.0-source.zip`: application source, build/install scripts, recovered
  tests and current audit documents. Original historical archive remains preserved.
- `NutCase-0.6.0-dependency-source-evidence.zip`: versioned upstream archives,
  immutable conda recipe/patch metadata, upstream references, source manifest,
  build/replacement instructions and recorded unresolved gaps.
- `inventory.json`, `NutCase-0.6.0.spdx.json`, `source-manifest.json`,
  `compliance-report.json`/`.md` and `SHA256SUMS.txt` bind the evidence to this
  exact candidate. The source evidence archive is **not asserted complete** while
  PySide/shiboken binding source/build and Mesa notice closure remain blocked.

Downloaded conda binary packages, PDFium DLL archives and Qt SDK/Mesa binary archives
remain local provenance evidence. They are excluded from the public source ZIP
to avoid introducing additional binary redistribution obligations.

`packaging/licensing/source-manifest.json` records per-archive SHA256, upstream
URL, known source/build entry points and status. Retrieved sources are retained
at `artifacts/phase6_2/sources/`. Sources are independently versioned; two PDFium
builds must not share an invented common snapshot. The Qt PDF source is the full
6.140.0 extension archive, including Chromium's PDFium tree; pypdfium2's PDFium
DLL separately matches `pdfium-binaries` chromium/8076.

## Legal choices for final review

The intended provisions are GPLv2 section 3(a) (complete corresponding source
accompanying binary distribution), GPLv3 section 6(d) (equivalent source access
from the designated binary-download location), and applicable LGPLv3 section 4
conditions for shared libraries and installation information. This plan remains
subject to qualified review; it is not a compliance certification.

Preserve the complete build/interface/patch information, not only LICENSE files.
Poppler's exact Windows recipe, four patches and build/host pins are retained.
Qt/PySide sources and build scripts are acquired; native Qt SDK source/build correspondence is established; binding-specific build/patch
confirmation and Mesa/LLVM configured notice closure remain open. Source retrieval URLs are
provenance evidence and backup retrieval instructions, not a substitute for the
release's source assets. A SHA256 verifies integrity against a reviewed manifest;
it does not prove license rights or source completeness.

Before publication the owner must confirm source access and responsibility for
preserving it. Retain immutable release assets and a project-controlled backup
for as long as binaries remain available; never remove/repoint sources while
serving the matching installer. Obtain review of any additional retention duties
if using another GPL source-delivery provision. No written offer or three-year
offer shortcut is used here. GitHub Actions' 30-day artifact retention does not
fulfill this public-release delivery plan.

## Reproduce the technical audit

See `packaging/licensing/README.md` for acquisition and verification commands.
Acquisition scripts never approve a component; failed requests and unresolved
obligations remain explicit. `BUILD_AND_REPLACEMENT.md` gives the supported
library layout, compatible replacement procedure and NutCase rebuild path.

FreeCAD remains a separate prerequisite. Supplied STEP files are excluded from
both installer and application source pending owner rights review. Only the documented unused Qt catalogs/plugins are excluded; required Qt PDF and software rendering remain. Historical Phase 6.2 artifacts are retained unchanged.

Phase 6.3 supplemental evidence is separately hash-bound in source-manifest.json and included under `phase6_3-research/` in the dependency evidence ZIP. The Qt SDK binary archives stay local; their build/source SBOMs, per-section comparisons and metadata are included.
