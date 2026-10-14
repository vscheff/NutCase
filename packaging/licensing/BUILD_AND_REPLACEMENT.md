# Build and library replacement information

NutCase 0.6.0 remains a Windows x64 directory bundle. NutCase is
GPL-3.0-or-later; dependencies retain their own licenses. No application terms
restrict modification or reverse engineering needed to debug library changes.
The release compliance verifier is a distributor check, not a runtime restriction.

## Replace compatible LGPL libraries

1. Close NutCase and its workers. Make a backup of the installed application
   directory, normally `%LOCALAPPDATA%\Programs\NutCase`. Keep user data intact
   at `%LOCALAPPDATA%\NutCase`.
2. Build compatible Windows x64 libraries from the exact versioned sources in
   the source manifest. Match the Python 3.13 interpreter ABI, PySide/shiboken
   6.12 ABI and Qt 6.12 module interfaces; Qt PDF/PdfWidgets is **6.140.0**.
   The binding wheel names use `cp310-abi3`; this is the minimum stable ABI,
   not the shipped interpreter version.
3. Replace DLLs and `.pyd` modules under `_internal\PySide6` and
   `_internal\shiboken6`. Preserve names/layout and replace a consistent
   dependency set. Qt plugins are separate DLLs under `_internal\PySide6\plugins`;
   keep Qt/PySide/plugin versions compatible. Replace Qt PDF's native DLLs and
   wrapper modules together when interface changes require it.
4. Launch `NutCase.exe` and exercise preview and drawing generation. Restore
   the backup if the modified build is incompatible. There is no signature,
   activation, installation-directory integrity or library-hash check at startup.
   Installer upgrades may replace local modifications; retain backups.
5. PySide Python support modules are also present inside the executable's
   PyInstaller archive. Changes to those modules, or ABI-breaking library changes,
   can require rebuilding NutCase from its accompanying application source.
   `scripts/bootstrap-build.ps1` and `scripts/build-windows.ps1` contain the
   Windows build/install recipe; `packaging/NutCase.spec` describes packaging.
   Build version/hash pinning is for official builds and can be adapted in a
   modified build. FreeCAD remains separately installed and process-isolated.

These instructions establish the available layout and rebuild path. An actual
independently modified Qt/PySide build has not been exercised. No claim is made
that an arbitrary Qt version is drop-in compatible. Assess applicable LGPLv3
section 4 requirements and User Product installation information during review.

## Source and build evidence

- Native Qt: official Qtbase/SVG 6.12.0 and Qt PDF 6.140.0 source archives match the configured SDK build evidence described below. Qtimageformats/qttranslations sources remain preserved historical evidence; their excluded plugin/catalog content is not needed by this payload.
- PySide/shiboken: official `pyside-setup-everywhere-src-6.12.0.tar.xz`, including
  `setup.py`, binding generator/type-system/interface files and `coin` recipes.
  See its README and the official Windows Qt build documentation preserved in
  the evidence package. Exact wheel configuration/patch correlation remains open.
- Qt PDF: official extension source archive
  `6.12.0-0-202609281005qtwebengine-everywhere-src-6.140.0.zip` contains
  `src/pdf`, `src/pdfwidgets` and embedded Chromium/PDFium. Chromium version is
  140.0.7339.225; Chromium DEPS records PDFium revision
  `1afaa1a380fcd06cec420f3e5b6ec1d2ccb920dc` before Qt modifications.
  Do not substitute Qt 6.12 or pypdfium2's Chromium/8076 sources for this archive.
- Poppler: exact package `poppler-26.09.0-h924501e_0.conda`, feedstock
  `13d784d77510e73d6066a75a79cd8e6040a6a261`, complete Poppler source and all four
  recipe patches (`disable-libtiff-win32-io`, `exportsymbols`,
  `includesystembeforejpeg`, `windows-data`). The package retains rendered
  build/host pins, `bld.bat`, `install.bat`, source checksum and conda variants.
  Rebuild in a licensed Windows MSVC/conda-forge environment using that recipe
  revision and recorded dependencies; apply patches through conda-build rather
  than manually guessing CMake flags. Binary reproducibility is not asserted.
- Poppler dependent DLLs: each matched package's immutable recipe/source
  records are retained, including later lcms2 `2.19.1-hf2c6c5f_3`. Its PE resource
  says 2.19.0; package/hash evidence takes precedence over that stale resource.
- CPython: full 3.13.16 source, PSF NuGet archive hash and `PCbuild` build scripts;
  referenced bzip2, libffi, OpenSSL, mpdecimal, xz and zlib source archives retained.
- pypdfium2 PDFium: exact upstream `pdfium-win-x64.tgz` from `chromium/8076`
  matches the shipped DLL. `pdfium-binaries-build.tar.gz` is pinned to build
  repository `f2e9a1c45bb17b85b540abf1af30146ef65416ac`, including build steps,
  GN configuration and patches. Exact PDFium source commit remains a review item.
- PyInstaller 6.22.3: source archive includes bootloader/runtime code and license
  exception. Build-only packages are listed separately from embedded runtime code.
- Inno Setup 7.1.0: compiler download hash, source/runtime license and exact
  `NutCase.iss` install/uninstall recipe are retained. Generated installer/runtime
  is redistributed; compiler and its own dependencies are not installed with NutCase.

## Microsoft alternative, if authorization remains unresolved

Use the official Microsoft x64 Visual C++ Redistributable as a user-installed
prerequisite at a version at least as new as the newest shipped runtime (14.51.36247).
Windows 10/11 already supplies UCRT; this installer requires Windows 10 build 17763
or later. Remove app-local MSVC/UCRT API-set DLLs only in a dedicated candidate,
validate dependency loading for the GUI, worker and Poppler, and rerun installer
and end-to-end checks. Do not merely delete DLLs in the reviewed payload.
The runtime prerequisite normally needs elevation; NutCase's per-user installer
currently does not. That installation change requires explicit acceptance review.

## Native Qt configuration and replacement-test limits

All 20 retained native Qt libraries/plugins correlate section for section to the official MSVC 2022 SDKs. Source tags are Qtbase 025bdad181de241e81bf853c8a2d7bf3d19261a9, SVG 883a58532078d003cefef0a549bfe9f885ce41f5 and PDF d505fc23640d2bd6345e6483eb73daf4e19f5829. Their SDK SBOMs preserve full build arguments and feature/module selection. Source checks match 23,105 Qtbase, 632 SVG and 1,771 PDF files directly or after Windows/Unix EOL conversion; remaining .tag and Git metadata differences are recorded. Whole-file signature/header differences do not require bit-for-bit reproducible builds. Binding wheel-specific source/build correlation remains open.

No installed MSVC C++ compiler component was found by vswhere, and CMake is unavailable. An independently rebuilt modified library was therefore not feasible using the existing toolchain. The four original modified-header load/restoration results remain valid only for replacement mechanics. No new test claims modified executable code, and no build tools were installed. LGPL section 4 review must separately assess actual replacement/debugging freedom and any installation information. This ordinary writable per-user directory bundle supplies no device signing/activation key; installer upgrades replace local library edits. That technical description does not settle User Product applicability.

Catalogs are excluded by the explicit English-only policy; unused image/platform/UIO plugins are excluded before PyInstaller COLLECT. Qt PDF and Mesa remain. The software-context probe actually loads Mesa; desktop and offscreen evidence do not establish RDP/VM coverage.
