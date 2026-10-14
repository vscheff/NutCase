# NutCase component evidence matrix

VERIFIED describes the recorded technical evidence, not global legal certification. Exact per-file origins/hashes remain in `inventory.json` inside `reference-inventory.zip`; source/SBOM references remain in `source-manifest.json`.

| Component | Version | Selected terms | Files | Status | Evidence / remaining requirement |
|---|---|---|---:|---|---|
| icu | 78.3 h5112557_2 | MIT | 2 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| lcms2 | 2.19.1 hf2c6c5f_3 | MIT | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| lerc | 4.2.0 hd936e49_0 | Apache-2.0 | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libcurl | 8.22.0 hdb0ef4a_0 | curl | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libdeflate | 1.25 h1a1d4e4_1 | MIT | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libfreetype6 | 2.14.3 hdbac1cb_2 | FTL | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libjpeg-turbo | 3.2.0 hfd05255_1 | IJG AND BSD-3-Clause AND Zlib | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| liblzma | 5.8.3 hfd05255_1 | 0BSD | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libpng | 1.6.58 hdc8cecf_1 | zlib-acknowledgement | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libpsl | 0.23.1 h9b16d47_1 | MIT | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libssh2 | 1.11.1 h734d217_1 | BSD-3-Clause | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libtiff | 4.7.2 h8f73337_1 | HPND | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| libzlib | 1.3.2 hfd05255_3 | Zlib | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| openjpeg | 2.5.4 h90fa87c_2 | BSD-2-Clause | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| openssl | 3.6.4 hf411b9b_0 | Apache-2.0 | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| poppler | 26.09.0 h924501e_0 | GPL-2.0-or-later | 14 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| poppler-data | 0.4.12  | BSD-3-Clause AND (GPL-2.0-only OR GPL-3.0-only) | 271 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| zstd | 1.5.7 h534d264_7 | BSD-3-Clause | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| CPython / Python standard library and native extensions | 3.13.16 | Python-2.0 | 17 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| PSF-distributed libffi | 3.4.4 | MIT | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| PSF-distributed OpenSSL | 3.5.9 | Apache-2.0 | 2 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| Inno Setup installer/uninstaller runtime | 7.1.0 | LicenseRef-Inno-Setup | 0 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| Microsoft C++ runtime / Windows UCRT API-set DLLs | See each PE version | NOASSERTION | 24 | REQUIRES HUMAN/LEGAL REVIEW | Source-package origin and SDK/runtime terms preserved. Owner must establish applicable redistribution authorization; SDK open-source restrictions need review. Supported alternative: official x64 VC runtime prerequisite plus Windows 10/11 UCRT; rebuild/retest if removing app-local DLLs. |
| Preserved third-party licensing evidence | audit 2026-10-13 | NOASSERTION | 2665 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| NutCase/PyInstaller embedded runtime | 0.6.0 / 6.22.3 | GPL-3.0-or-later | 2 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| NutCase source and documentation | 0.6.0 | GPL-3.0-or-later | 90 | REQUIRES HUMAN/LEGAL REVIEW | Owner must confirm code/documentation/asset ownership. Model assets are excluded. |
| Pillow image extensions | 12.3.0 | MIT-CMU | 6 | REQUIRES HUMAN/LEGAL REVIEW | Actual frozen codec selection measured; missing AOM license/patent text and full dav1d/recipe-selected libyuv notices added. Confirm secondary static closure (libyuv/libsharpyuv, TIFF/lzma) and residual attribution. FreeType extension absent; Tk adapter physically shipped but tkinter absent. |
| pypdf | 6.10.0 | BSD-3-Clause | 2 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| pypdfium2 binding | 5.14.0 | Apache-2.0 OR BSD-3-Clause | 1 | VERIFIED | Existing technical provenance/source/notices preserved; global human decisions still apply. |
| pypdfium2 PDFium build | 156.0.8076.0 | BSD-3-Clause | 2 | REQUIRES HUMAN/LEGAL REVIEW | Exact binary-release, actual GN arguments, successful Windows builder job and 14 build-derived notices established; all notice bytes installed. Exact PDFium checkout unrecorded; source delivery not automatically required under BSD. Review sufficiency or obtain narrow maintainer confirmation of commit/unhandled notice warnings. |
| PySide6 bindings | 6.12.0; Pdf wrappers 6.12.0.140 | LGPL-3.0-only | 7 | BLOCKED | Exact binding-wheel revisions, patches/configuration and binding-specific compiled notices remain unresolved, including PySide6_Pdf 6.12.0.140. Native Qt SDK correspondence is established separately; commercial reference does not imply commercial-only rights. |
| Qt libraries and plugins | 6.12.0 | LGPL-3.0-only | 18 | VERIFIED | Native source/configured notice correspondence established: all retained SDK sections match, source tags and source-file checks match (EOL/tag/Git metadata differences recorded), official configured SDK notice SBOMs installed. Binding build correlation remains a separate blocker. |
| Qt-supplied OpenGL software renderer | Banners: Mesa 11.2.2 / LLVM 3.6.2; exact build unresolved | NOASSERTION | 1 | BLOCKED | Code/data sections match official Qt Mesa variants and software context loads this DLL. Nominal Mesa 11.2.2/LLVM 3.6.2 notices plus Qt attribution retained; confirm compiled LLVM/auxiliary notice closure. Full-file differences are not a source-compliance requirement under known permissive terms. |
| Qt PDF / PdfWidgets with embedded PDFium | 6.140.0 (wheel 6.12.0.140) | LGPL-3.0-only | 2 | VERIFIED | Qt PDF/PdfWidgets sections match the standalone official 6.140.0 SDK. Source tag d505fc23640d2bd6345e6483eb73daf4e19f5829 matches the acquired full source; 1,771 source files match raw hashes. Actual configured Chromium-PDF notice SBOM installed. This does not approve the PySide Pdf binding build. |
| Qt translation catalogs | 6.12.0 / Pdf 6.140.0 | NOASSERTION | 0 | NOT APPLICABLE | All 99 catalogs excluded before COLLECT. No application translator loading; explicit Qt translator semantics and four frozen locale tests establish English source fallback. Native Windows dialogs may use OS localization. |
| shiboken6 bindings | 6.12.0 | LGPL-3.0-only | 2 | BLOCKED | Official 6.12 source retained; exact binding wheel revision/configuration/patch and compiled notice correspondence still need upstream evidence. |
