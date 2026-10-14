# Windows redistribution evidence workflow

This directory contains the reviewed inventory and independent fail-closed checker.
It is a technical dossier with explicit unresolved decisions, not legal certification.
Do not regenerate `inventory.json` to make a changed release pass.

## Current reviewed scope

Phase 6.3 has a rebuilt, trimmed frozen payload and an explicit independent audit; exact installer binding and acceptance are recorded in its release reports. The historical Phase 6.2 installer, sources and evidence remain untouched. See PHASE6_3_REVIEW.md for the completed technical review and remaining human/upstream decisions. The reviewed candidate is artifacts/phase6_3/candidate-20261014; artifacts/phase6_3/baseline preserves the original 110-native/21-finding starting point. Source ZIPs exclude supplied models.

`inventory.json` to make a changed release pass.

## Current reviewed scope

The original installer was actually installed to
`artifacts/phase6_2/original-installed`, with a guard against an existing NutCase
registration. Original installer/source/checksums and its installed inventory remain
at `artifacts/phase6_2/original/`. The new candidate only changes licensing/docs and
adds a Start Menu Licenses shortcut. Application EXEs, DLLs, extensions, renderers
and source code remain byte-identical. Source ZIPs exclude supplied STEP models.

`inventory.json` lists every payload file, content hashes, originating wheel/NuGet/
Poppler ZIP/package member, PE metadata, license selection, notice/source/build
references and unresolved questions. `embedded-python.json` inventories actual
EXE bytecode and standard-library ZIP members. `binary-inventory.csv` is the short
native-file view. `NutCase-0.6.0.spdx.json` is SPDX 2.3; NOASSERTION deliberately
preserves uncertainty instead of inventing license conclusions.

`notices/NOTICE_INDEX.json` maps verbatim acquired notice/attribution records back
to upstream source/package paths. These include conservative source-tree evidence;
do not interpret this as a compiled third-party inventory. Full source archives
retain their original per-file copyrights. `source-manifest.json` records all
source and local binary-provenance evidence, clearly distinguishing public source
delivery from packages kept locally for binary hash comparison.

## Run checks (PowerShell, repository root)

```powershell
& .venv-build/Scripts/python.exe packaging/licensing/verify.py `
  --bundle artifacts/phase6_3/candidate-20261014 `
  --review packaging/licensing/inventory.json `
  --materials artifacts/phase6_2 `
  --supplemental-materials artifacts/phase6_3/research `
  --report artifacts/phase6_3/checkpoint-compliance.json
& .venv-build/Scripts/python.exe -m unittest discover -s tests -p test_licensing.py -v
```

Exit 0 means recorded technical checks/decisions passed. Exit 2 means public
release remains blocked, including unresolved human decisions. JSON and Markdown
reports are written even on failure. New/missing/changed files, installer hashes,
required notices, missing/corrupt/changed source, known source/build members and
unsupported verification decisions fail. Files are not accepted just because
they have a LICENSE/README name. Every file is checked, including data and Python
archives. The review is a trusted input that requires human review; the checker
cannot prove the truth of a legal decision or analyze arbitrary source completeness.

`scripts/build-windows.ps1` checks this inventory by default and fails for unresolved
licensing. `-AllowUnresolvedLicensing` may retain a local acceptance candidate only
when findings are already recorded component/obligation decisions; it cannot bypass
unexpected files, hash mismatches, missing sources or invalid notice/source checks.
The GitHub workflow runs the default strict mode, retains reports on failure and
has no publication or signing step.

## Evidence acquisition and a new review

These are audit operations, not an automatic license approver:

```powershell
& .venv-build/Scripts/python.exe packaging/licensing/research.py
& .venv-build/Scripts/python.exe packaging/licensing/extra_research.py
& .venv-build/Scripts/python.exe packaging/licensing/inspect_archives.py
& .venv-build/Scripts/python.exe packaging/licensing/conda_audit.py
& .venv-build/Scripts/python.exe packaging/licensing/acquire_recipe_sources.py
& .venv-build/Scripts/python.exe packaging/licensing/inspect_frozen.py
& .venv-build/Scripts/python.exe packaging/licensing/assemble.py
```

Archive inspection needs isolated `zstandard==0.25.0` and `PyYAML==6.0.3` under
`artifacts/phase6_2/audit-tools`; these are audit-only, never runtime dependencies.
The conda audit initially tests Poppler's recorded build-environment packages.
It does **not** prove runtime versions when the repackager used newer dependencies;
the measured later lcms2 match must be retained explicitly. Acquisition records
failed requests, checks source checksums where supplied and never executes downloads.
See the retained primary-reference manifests for exact URLs and outcomes.

`fetch_reviewed.py` retrieves only already-reviewed URLs and verifies recorded SHA256.
`package_review.py` assembles downloadable application/source-evidence assets; it
never updates hashes or turns a blocker into VERIFIED. Original releases, binaries,
test-recovery artifacts and source archives must be retained.

Packaging requires retained primary-reference and conda file-match/recipe metadata
as well as upstream archives. A fresh machine must acquire/inspect that evidence
for its new review; the packager rejects missing audit metadata instead of silently
building a smaller source package. Audit readers/validators are isolated tools,
not application or release dependencies.

`scripts/verify-installer.ps1 -BindLicensingReview` performs an actual isolated
installation, checks every file against the separately recorded review, and binds
the exact installer hash and generated Inno runtime hashes. It cannot approve
changed payload bytes. `installed-inventory.json` and
`installed-NutCase-0.6.0.spdx.json` retain the generated uninstaller alongside all
installed resources; the staged bundle SBOM excludes those generated files.
Generated uninstall data is installation-specific; its recorded hash identifies
the inspected installation, not a universal file expected on every user's machine.

After confirming no real NutCase installation is registered, the final candidate
can be inspected using an explicitly disposable workspace path:

```powershell
& scripts/verify-installer.ps1 `
  -Installer (Resolve-Path artifacts/phase6_3/release/NutCase-0.6.0-windows-x64-setup.exe).Path `
  -Installation (Join-Path (Get-Location) 'artifacts\Licenses Inspection Î© & Test') `
  -Evidence (Join-Path (Get-Location) 'artifacts\phase6_3\new-installed-check') `
  -DataHome (Join-Path (Get-Location) 'artifacts\new-licensing-data') `
  -BindLicensingReview -VerifyLibraryReplacement
```

Binding requires every payload file to match the independent review. The optional
replacement probe changes one PE checksum-header bit in four native libraries,
launches the frozen GUI and restores their original bytes. It exercises modified
byte loading without altering executable code, not an independently rebuilt Qt
library or a legal conclusion. The lifecycle test uninstalls its disposable app.

## Remaining final review

`obligations.json` and `UPSTREAM_CLARIFICATIONS.md` specify exact outstanding
evidence/decisions. No upstream emails/issues were sent. Final publication requires
their resolution, a new hash-bound review if binaries change, clean-machine and
interactive acceptance, and explicit owner approval.

## Phase 6.3 audit and supplemental evidence

review_phase6_3.py is an explicitly invoked audit, never a build/gate step. It preserves baseline origin records, rejects new/changed dependency binaries and unexpected removals, and records the specific decisions supported by SDK source/section/SBOM correlation. inspect_frozen.py --bundle dist/NutCase inventories the newly built GUI/worker and base ZIP; --include-verifier is optional because NutCaseVerify.exe is a noninstalled tool.

The verifier requires an explicit --supplemental-materials root when the independent review lists supplemental materials. Missing/changed evidence still fails closed. Source packaging checks each supplemental hash and excludes SDK binary archives/DLLs. Build outputs can be directed to a separate directory with build-windows.ps1 -ArtifactDirectory. Existing candidate history protection remains. A changed build still requires a new audit and actual installer binding; AllowUnresolvedLicensing cannot bypass integrity failures.
