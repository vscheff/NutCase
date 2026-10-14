# NutCase release-readiness checklist

The current package is a local candidate. Check boxes reflect the retained automated evidence; exact Phase 6.3 outcomes are recorded in release-adjacent PHASE6_3_REVIEW.md and verification reports. Historical Phase 6/6.2 results remain available separately.

## Build and automated checks

- [x] Pinned Windows x64 toolchain bootstrap and candidate builds complete.
- [ ] Repeat the full build from a fresh checkout and run the GitHub-hosted workflow.
- [x] Installer, exact application source archive and SHA256SUMS are retained.
- [x] Frozen GUI and worker run without development Python/PATH.
- [x] Missing FreeCAD gives usable installation guidance; version/architecture probes are active.
- [x] Both supplied models analyze and generate Basic/Comprehensive/Custom.
- [x] Native reopen, references, measurements, normalized PDF and both renderers pass.
- [x] Qt preview and PDF/FCStd export hashes pass.
- [x] Source-bound settings/configuration survive application restart.
- [x] Cancellation and failure preserve the previous complete release/source.
- [x] Windows cancellation/abrupt worker-exit tests kill native fixtures and descendants.
- [ ] Force a full interactive GUI crash during real CAD generation and verify cleanup.
- [x] Read-only installation and spaces/Unicode/ampersands work.
- [x] Scripted install, shortcuts, same-version update, uninstall and reinstall preserve user files (exact count in the Phase 6.3 lifecycle report).
- [x] Corrected installed PDF association and detached FreeCAD launch requests pass.

## Final human acceptance

- [ ] Test on a clean Windows VM/installation with no developer Python or package tools.
- [ ] Test normal interactive installer, first Start Menu launch and optional desktop shortcut.
- [ ] Inspect Basic/Comprehensive/Custom drawings from both supplied models.
- [ ] Confirm normal PDF zoom/page controls and external viewer rendering.
- [ ] Open editable FCStd in the real FreeCAD GUI and inspect the native dimensions.
- [ ] Exercise cancellation during native processing and a real failed generation.
- [ ] Confirm logs/data locations and uninstall/reinstall without loss.
- [ ] Test a real version upgrade, including settings and existing release history.
- [x] Inspect actual installer payload, licensed resources and embedded Python.
- [x] Acquire versioned source, immutable conda recipes/patches and notice evidence.
- [x] Prepare SPDX inventory, source-delivery assets and fail-closed licensing checks.
- [ ] Resolve binding wheel source/build/notices and Mesa compiled notice closure. Native Qt SDK correspondence is established; translation catalogs are excluded.
- [ ] Review Microsoft authorization, Pillow/PDFium notice coverage, LGPL replacement and source-delivery decisions.
- [ ] Achieve release_ready=true in the exact candidate compliance report before publication.
- [ ] Confirm rights to application assets and supplied STEP files.
- [ ] Decide whether to sign; test SmartScreen/application-control behavior.
- [ ] Review release notes, prerequisites, checksums and source artifacts.
- [ ] Explicitly approve first public GitHub release. No automatic publication occurs.

See PHASE6_REVIEW.md for historical packaging results and TEST_COVERAGE_RECOVERY.md
for the restored Phase 6.1 suites (166 distinct methods). PHASE6_2_LICENSING_REVIEW.md
records the historical licensing candidate. PHASE6_3_REVIEW.md records the current trimmed candidate and checks. Development-host automated
tests do not erase remaining clean-machine or interactive acceptance requirements.

- [x] Explicit Qt plugin/catalog exclusions and frozen locale/PDF/software-context probes.
- [x] Retained native Qt section/source/build-SBOM correspondence.
- [ ] RDP/VM/low-capability graphics acceptance; Mesa remains available.
- [ ] Independently rebuilt modified LGPL library (existing compiler toolchain absent).
