# NutCase 0.6.0 Phase 6.2 licensing review

**Ready for final human review; public redistribution remains blocked.** No release
was published. This is a technical evidence dossier, not legal certification.

## What remains before public distribution

1. **BLOCKED — Qt wheel correspondence and configured notices.** Obtain Qt's
   community-wheel build configuration, patch declarations and binary SBOM for
   PySide/shiboken/Qt 6.12.0 and Qt PDF/PdfWidgets **6.140.0**, including the actual
   PDFium dependency closure and all 99 translation catalogs. Complete official
   source archives are acquired, but their presence does not prove build correspondence.
2. **BLOCKED — Mesa software rasterizer.** The shipped `opengl32sw.dll` is traced
   to its PySide wheel. Banners indicate Mesa 11.2.2 / LLVM 3.6.2, whose sources
   are acquired. Three official Qt Mesa binary variants do not match its hash.
   Exact patches/configuration/source and compiled notices are still missing.
3. **REQUIRES HUMAN/LEGAL REVIEW — Qt notice discrepancy.** Community wheel
   metadata declares LGPL/GPL alternatives; supplied license files reference a
   commercial license. This is not proof that community wheels require commercial
   licensing. Request confirmation and the applicable missing notices.
4. **REQUIRES HUMAN/LEGAL REVIEW — Microsoft authorization.** Confirm the owner's
   rights under applicable Visual Studio/runtime and Windows SDK terms for the
   24 copied DLLs. Third-party package inclusion is not authorization. The supported
   fallback is a user-installed official x64 VC runtime plus Windows UCRT; removing
   local DLLs requires a separate rebuilt/retested candidate and prerequisite review.
5. **REQUIRES HUMAN/LEGAL REVIEW — Pillow and pypdfium2 PDFium.** Resolve configured
   static codec/notice coverage in Pillow's extensions. The PDFium DLL exactly
   matches `pdfium-binaries` chromium/8076 and complete binary notices are retained,
   but its recorded source hash is null. Obtain the precise source/build record,
   or review whether the existing permissive-license evidence is sufficient.
6. **REQUIRES HUMAN/LEGAL REVIEW — LGPL and source delivery.** Review the replacement/
   rebuild instructions, LGPLv3 section 4 and applicable installation information.
   Approve installer-adjacent source delivery, immutable retention and backup
   responsibility; resolve the source gaps above before claiming completeness.
7. **REQUIRES HUMAN/LEGAL REVIEW — ownership and release acceptance.** Confirm
   NutCase code/document/asset authority. STEP models remain excluded. Complete
   clean-Windows and normal interactive acceptance in `docs/RELEASE_READINESS.md`,
   then explicitly approve publication of the exact reviewed assets.

Draft upstream questions are in `packaging/licensing/UPSTREAM_CLARIFICATIONS.md`.
None were sent. The complete requirement checklist is
`packaging/licensing/OUTSTANDING_OBLIGATIONS.md`; machine-readable decisions are
`packaging/licensing/obligations.json` and the inventory. FreeCAD/OCCT are
**NOT APPLICABLE** to this redistribution: neither is in the actual payload.

## Exact candidates and evidence

Historical installer/source and original installed inventory are preserved in
`artifacts/phase6_2/original/`; a complete installed-payload snapshot is retained
in `artifacts/phase6_2/original-payload/`. Existing root release artifacts and
Phase 6.1 recovered tests/artifacts were preserved.

| Artifact | SHA-256 |
|---|---|
| Historical installer | `e5b5b5431bf40c8f729d31a0b3e982390d45fa8b758dacf255ac4bd19c3c8cac` |
| Historical application source ZIP | `8a723c894e6b1f28bfb3cc24b25f90a903d5db746d5d91d64923084993b8c9b3` |
| Phase 6.2 final installer | `97841d9430eff7176ac53236dbf533089ab8a0f588b4d968bb8bc2be4906aba6` |

The final installer is
`artifacts/phase6_2/release/NutCase-0.6.0-windows-x64-setup.exe`.
The original installation had 613 files: 80 DLLs, 27 Python extensions and four
EXEs, including Inno's generated uninstaller. No `.ttf`/`.otf` font files ship.
The final staged payload has **3,226 files**; its actual installation has **3,228**,
including generated `unins000.exe`/`.dat`. All 110 staged native application and
renderer files remain byte-identical to the original. Only licensing/documentation
contents and the installer envelope changed. Application EXEs were not rebuilt.

- `packaging/licensing/inventory.json`: every staged path/hash, PE version,
  archive-member provenance, selected license, notices, source/build references,
  review status and unresolved issue. It contains 36 component groups: 26 technical
  VERIFIED, six BLOCKED and four REQUIRES HUMAN/LEGAL REVIEW. Global decisions remain.
- `artifacts/phase6_2/release/installed-inventory.json`: actual installed inventory,
  including generated runtime hashes bound to this installer.
- `NutCase-0.6.0.spdx.json` and `installed-NutCase-0.6.0.spdx.json` in the release
  directory: staged and installed SPDX 2.3 inventories. Both pass the official
  SPDX 2.3 JSON schema; NOASSERTION preserves undecided licensing conclusions.
- `packaging/licensing/COMPONENT_MATRIX.md` and `binary-inventory.csv`: component
  and native-file views. `embedded-python.json` decodes both actual EXE/PYZ
  archives and the standard-library ZIP; runtime hooks are distinguished from
  build-only packages. Raw PyInstaller TOCs are retained as build evidence.
- `artifacts/phase6_2/research/`: PE metadata, exact package/file matches, upstream
  responses, source/recipe retrieval receipts, schema validation and binary
  preservation checks. Failed/ambiguous retrievals are evidence, not approval.

## Materials acquired and implemented

Versioned application and dependency source/evidence assets are assembled under
`artifacts/phase6_2/release/`, with manifests and `SHA256SUMS.txt`. There are 88
acquired archive records: 62 public source/build archives and 26 local-only binary
provenance archives. Local conda binary packages, Mesa binaries and PDFium DLL
archives are excluded from the public source ZIP. They remain retained locally.
The source dossier is explicitly incomplete while Qt/Mesa correspondence is blocked.

The complete Qt PDF 6.140.0 source archive includes Chromium/PDFium; its SHA-256 is
`9a4d5de7056464d50991d0acaabdee28984b18dfbc492865ea76e5ae281f3ff3`.
This differs from pypdfium2's PDFium 156.0.8076.0; their source/notices are separate.
The latter DLL SHA-256 is
`69f1e860f6742fbaafcc4db80e785eec9a4ee0da36ea6d1dc0867ea0f18baea6`.

Poppler matches conda-forge `poppler-26.09.0-h924501e_0.conda`, feedstock
`13d784d77510e73d6066a75a79cd8e6040a6a261`. Full corresponding source, four
applied patches, immutable Windows recipes, host/build pins, each dependent
package's source/recipe/license and poppler-data 0.4.12 are retained. The actual
lcms DLL matches **2.19.1-hf2c6c5f_3**, despite an older build-environment pin and
stale PE version. This was resolved by exact content matching.

Full CPython 3.13.16 and PSF external sources, pypdf/Pillow/pypdfium2/PyInstaller
sources, Inno sources/license, FreeType acknowledgment, Microsoft terms, and
verbatim wheel notices are preserved. `source-manifest.json` contains individual
source hashes and exact retrieval URLs. Complete archives retain original
copyrights, build/interface files and patches.

The installer adds **NutCase → Licenses** in the Start Menu, opening
`licenses/index.html`. It exposes supplied license files and 2,609 conservatively
acquired source/package notice/attribution records with their provenance index.
Source-tree notices are not a claim that all source-tree code was compiled.
An About redesign was unnecessary; licensing remains accessible without running
the drawing application. `THIRD_PARTY_NOTICES.md` distinguishes individual
dependency terms from NutCase's GPL declaration.

The default Windows packaging gate compares against a separately recorded review
and fails for unknown/changed files, missing notices, source hash changes, invalid
source/build contents, stale embedded-code evidence or unresolved decisions.
It cannot approve a build by regenerating its own inventory. The local-candidate
override permits only existing human/component decisions, never integrity failures.
The GitHub workflow retains failure reports and has no publication step.

## Executed validation

| Category | Result and evidence |
|---|---|
| Recovered native suite | 78 run, 74 passed, four optional sample tests skipped; `build/test-results/phase6_2/native.json` |
| Recovered GUI suite | 48 passed; `build/test-results/phase6_2/gui.json` |
| Recovered PDF suite | 24 run, 23 passed, one optional sample test skipped; `build/test-results/phase6_2-pdf-final/pdf.json` |
| Recovered launcher suite | Three passed; `build/test-results/phase6_2/launchers.json` |
| Packaging and licensing suite | 26 passed, including 13 adversarial licensing tests; `build/test-results/phase6_2-packaging-final/packaging.json` |
| Installed CAD regression | Two supplied models × Basic/Comprehensive/Custom, all six passed; Qt preview, both independent renderers, drawing/export/native checks; `artifacts/phase6_2/verification/installed-regression.json` |
| Installer lifecycle | Unicode/space/ampersand path, registration, shortcuts, licensing index, default/isolated data, actual read-only ACL, same-version update, uninstall/reinstall and data preservation passed; `verification/installer-lifecycle.json` and `verification-final/installer-lifecycle.json` |
| Final installed payload | Every one of 3,226 reviewed files compared independently; two generated Inno hashes retained; final lifecycle passed, `verification-final/installer-lifecycle.json` |
| Compatible modification/replacement probe | Four installed Qt/PySide/shiboken native files had one PE checksum-header bit changed, loaded in the actual frozen GUI, then were restored; lifecycle passed, `verification-replacement/library-replacement.json` and `installer-lifecycle.json` |
| SPDX schema | Both staged/installed inventories passed official schema; `research/spdx-validation.json` |
| Release gate | Technical integrity passes; public release fails with 21 component/obligation findings; `release/compliance-report.json` and `.md` |

There are **179 distinct test cases** across the final suite results: 174 passed,
five skipped. The initial full dispatch's PDF suite hit sandbox temporary-directory
permission errors; that failed report remains retained. Its focused rerun used a
workspace temporary directory and the native Unicode control and passed. No
recovered test was removed or weakened. Six installed CAD runs used the preceding
licensing candidate; the final candidate's native application files are identical,
and its installer lifecycle/full payload comparison were repeated after notice fixes.

The replacement probe changes headers, not executable code. It demonstrates
compatible modified-byte loading without application hash enforcement; it does
not establish every LGPL interpretation or successful independently rebuilt
modified-library operation. This was a development host, not a clean VM. Normal
interactive/SmartScreen and remaining acceptance items are still pending.

## Verification commands

From the repository root, PowerShell:

```powershell
& .venv-build/Scripts/python.exe packaging/licensing/verify.py `
  --bundle artifacts/phase6_2/candidate-bundle `
  --review packaging/licensing/inventory.json --materials artifacts/phase6_2 `
  --installer artifacts/phase6_2/release/NutCase-0.6.0-windows-x64-setup.exe `
  --report artifacts/phase6_2/release/compliance-report.json
# Expected exit 2 until the documented decisions/evidence gaps are resolved.
& .venv-build/Scripts/python.exe -m unittest discover -s tests -p test_licensing.py -v
& .venv-build/Scripts/python.exe packaging/licensing/package_review.py
```

Full acquisition, installed comparison and replacement commands are documented in
`packaging/licensing/README.md`. Before publication, resolve the checklist, review
the exact inventories/assets, rerun the gate to `release_ready=true`, complete
acceptance and obtain explicit owner authorization. A new binary always needs a
new reviewed inventory and appropriate engineering validation.
