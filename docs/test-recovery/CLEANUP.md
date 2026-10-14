# Runtime directory cleanup

Performed on 2026-10-12 at the user's request to retain the program and its documentation.

## Removed

- Historical generation archives, duplicate exports, experimental drawings, renderer contact sheets and development logs.
- Development regression suites (`tests`, `tests_gui`, `tests_pdf`, `tests_launchers`), synthetic input fixtures and their generated artifacts.
- Phase-specific validation, evidence-recording, API probing, section investigation and PDF experiment scripts that are not called by the running program.
- Temporary work, project bytecode caches and the empty `FileOpen` directory.

The initial removal covered **2,613 files, approximately 349 MiB**. Temporary files created for the post-cleanup verification were subsequently removed as well. This is a runtime-focused working directory; development regression suites are no longer included.

## Preserved

- All three application packages, fourteen runtime entry-point/worker/probe scripts, and the Windows launcher.
- The complete installed `.venv-gui` environment and all dependency requirement files. Installed third-party libraries were not selectively trimmed.
- Both original supplied STEP files and configuration examples.
- Existing GUI settings, current custom selections and saved configuration history, without changing their bytes.
- Both current drawing manifests and every checksummed artifact in their releases, at their original paths. Their two pipeline runs, including native PDFs and CAD export diagnostics, remain available for troubleshooting.
- README, desktop usage instructions, screenshots and phase review documents. Historical reviews are marked to distinguish earlier execution evidence from files retained after cleanup.

The retained current run IDs at cleanup were `20261012T175632-fbfeaacaa3` and `20261012T191457-5ead65f4a6`. Existing user output/settings paths were not relocated.

## Post-cleanup checks actually executed

- The actual Windows batch launcher passed `-StartupCheck`, including external GUI/PDF imports, native FreeCAD discovery and Qt window/event-loop initialization.
- SHA-256 checks confirmed unchanged original STEP files, all saved GUI state/configuration files and both current manifests. Both complete current releases passed the program's artifact checksum and report-validation gates before and after validation generation.
- A fresh comprehensive generation of FC00AAB09748 ran in a separate disposable output directory after the old temporary FreeCAD preferences were removed. The native geometry analysis, TechDraw dimensions, FCStd save/reopen, native PDF export, external PDF normalization, independent PDF verification and atomic publication completed.
- That generation produced **11 dimensions**, with exit **2** for the retained source-geometry review requirement. Its PDF verification passed: one ANSI B page, all eleven expected dimension labels, no identified remaining export defects, no Poppler warnings, vector content, and no unmatched ink beyond the renderer comparison's two-pixel allowance.
- Existing current releases were not replaced by this verification generation. Its temporary deliverables and logs were removed after their results were inspected.
- Active README and desktop-guide hyperlinks were checked. Instructions invoking removed development tools were removed from the active guides.

No new interactive desktop workflow, Nitro rendering check or visual engineering approval was claimed during cleanup. The removed historical regression suites were not rerun. The engineering limitations and preliminary-drawing warnings remain in the program and documentation.

## Regenerated working files

The program recreates `tmp/`, Python bytecode caches, launcher environment reports and new pipeline diagnostics when needed. These files appearing again is normal. Keep native exports and run diagnostics while investigating a generation failure. Do not remove an active `.generation.lock` or files belonging to a running job.
