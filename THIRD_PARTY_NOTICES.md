# NutCase 0.6.0 third-party notices

NutCase application code is **GPL-3.0-or-later**. That declaration does not
relicense its dependencies. They retain their individual terms, copyrights,
conditions, disclaimers and exceptions. This candidate has unresolved release
obligations listed in `docs/LICENSING_AUDIT.md`.

The installed `licenses/index.html` opens the complete supplied and acquired
notice files. The installer adds a **NutCase â†’ Licenses** Start Menu entry.
The files are readable directly from the application directory without launching
NutCase. `licenses/audit/NOTICE_INDEX.json` maps flattened notice filenames to
the original source/package paths. Full dependency sources/build evidence are
provided separately; see `docs/SOURCE_AVAILABILITY.md`.

| Redistributed component | Individual terms and exact notice location |
|---|---|
| CPython 3.13.16 | Full PSF/Python historical license stack in `licenses/CPython-LICENSE.txt`; source notices and external-library notices in `licenses/audit/`. |
| PySide6/shiboken6 6.12.0 | LGPL-3.0-only selected for the open-source option, subject to the documented upstream wheel/source clarification. Preserve wheel metadata/commercial reference files as evidence and acquired source notices. Generic LGPL/GPL texts in `licenses/open-source/`. |
| Qt 6.12 libraries/plugins and Qt PDF/PdfWidgets 6.140.0 | LGPLv3 option selected for applicable modules, with exact native SDK section/source/build-SBOM correspondence established in current candidate. Copyright (C) The Qt Company Ltd. and other contributors. Full acquired source license/attribution records in `licenses/audit/`; the complete source archive contains per-file copyright statements. Qt's embedded PDFium/Chromium notices remain separate from pypdfium2's PDFium notices. |
| Qt-supplied `opengl32sw.dll` | Binary maps to Essentials; banners identify Mesa 11.2.2/LLVM 3.6.2 and nominal sources are acquired. Executable/data sections match the official Qt Mesa archives. Nominal Mesa/LLVM notices and Qt llvmpipe attribution are retained; compiled auxiliary notice closure remains BLOCKED. MIT/Boost/NCSA source materials are separate from Qt LGPL terms. No generic Qt license is assigned to this DLL. |
| Poppler 26.09.0 | GPL-2.0-or-later. Copyright 2005-2026 The Poppler Developers; Copyright 1996-2011, 2022 Glyph & Cog, LLC. Full COPYING and conda recipe notices are retained in `licenses/audit/`; complete source, patches and build recipe are separate release assets. |
| Poppler dependent libraries | Per-package MIT, FTL, IJG/BSD/Zlib, Apache-2.0, curl, 0BSD, PNG, HPND and other exact terms in the reviewed component matrix and verbatim conda license files under `licenses/audit/`. FreeType uses the FTL alternative: this product uses FreeType software; its full project notice/copyright is preserved. Do not apply Poppler's GPL to every dependent DLL. |
| Poppler 0.4.12 encoding/CMap data | Mixed Adobe/BSD/GPL terms. Preserve `vendor/poppler/share/poppler/COPYING`, `COPYING.adobe`, `COPYING.gpl2` and per-file CMap notices. Full data source archive accompanies the dependency source package. No font files were found in the original payload. |
| pypdf 6.10.0 | BSD-3-Clause; exact copyright, conditions and disclaimer at `licenses/pypdf-6.10.0/pypdf-6.10.0.dist-info/licenses/LICENSE`. |
| pypdfium2 5.14.0 and its PDFium 156.0.8076.0 | Binding offers Apache-2.0 OR BSD-3-Clause. Preserve all `licenses/pypdfium2-5.14.0/` files, including PDFium Authors' copyright and every `BUILD_LICENSES` dependency notice. The PDFium DLL matches the upstream `chromium/8076` binary distribution. Exact source commit remains a review item. |
| Pillow 12.3.0 | MIT-CMU plus compiled-library terms; complete combined copyright/conditions/disclaimers at `licenses/pillow-12.3.0/pillow-12.3.0.dist-info/licenses/LICENSE`. Upstream SBOM and source are retained; shipped codec versions are measured. Added AOM 3.14.1 LICENSE/PATENTS, full dav1d 1.5.3 COPYING and recipe-selected libyuv notices under licenses/audit/. Secondary static closure remains a review item. |
| PyInstaller runtime 6.22.3 | GPL-2.0-or-later with its bootloader distribution exception; some runtime files are Apache-2.0. Preserve exact exception and notices at `licenses/pyinstaller-6.22.3/`. Compiler/hooks are build tools; bootloader/import/runtime-hook code is embedded in executables. |
| Inno Setup 7.1.0 runtime | Individual Inno Setup terms, retained copyrights and upstream URLs; full text in `licenses/Inno-Setup-LICENSE.txt` and source evidence. Compiler is not installed with NutCase. Installer/uninstaller runtime is redistributed. |
| Microsoft MSVC/UCRT DLLs | Microsoft proprietary terms, versions and origins per `binary-inventory.csv`. Exact conda license/EULA material is retained. Owner redistribution authorization and SDK conditions remain subject to human/legal review; package inclusion is not proof of permission. |

FreeCAD, OCCT and other separately installed FreeCAD dependencies are not
redistributed by this installer. Users must obtain FreeCAD separately.
WebEngine browser libraries, Nuitka and WiX are not in the installed payload.
Build-only tools are listed in `packaging/licensing/embedded-python.json` and
the retained pinned build lock; do not confuse their presence in the build
environment with runtime redistribution.

For exact copyright statements use the preserved verbatim component notice files,
not the short summaries above. Conservative source-tree notice collection can
include software not compiled into NutCase; it is evidence awaiting build-specific
closure review, not a declaration that every Qt/Chromium source dependency ships.

The inspected candidate supplies the four official configured Qt SDK SBOMs under `licenses/audit/Qt-SDK-*`; these preserve complete copyright/notice text and include SDK build-only or unshipped targets, which are distinguished in the audit. Translation catalogs are excluded by the English-only packaging policy.
