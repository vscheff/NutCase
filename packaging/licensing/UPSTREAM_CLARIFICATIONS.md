# Ready-to-send upstream clarification requests

None have been sent. Attach the exact affected file/wheel rows from inventory.json, plus the named evidence extracts. Do not attach the full source archive.

## Qt for Python maintainers

Channel: [Qt for Python issue tracker](https://bugreports.qt.io/projects/PYSIDE) or the official [PySide mailing list](https://lists.qt-project.org/listinfo/pyside).

Subject: Windows community PySide6/shiboken6 6.12.0 and PySide6_Pdf 6.12.0.140 binding build/notice information

We distribute the public PyPI Windows x64 wheels pyside6 6.12.0, pyside6_essentials 6.12.0, pyside6_addons 6.12.0, shiboken6 6.12.0 and pyside6_pdf 6.12.0.140 with GPL-3.0-or-later NutCase, selecting the applicable LGPLv3 option. Their metadata declares LGPL/GPL alternatives, while the dist-info license directories supply only LicenseRef-Qt-Commercial.txt. Your community documentation confirms public PyPI open-source use; we are asking for missing artifact-specific notices, not assuming commercial-only licensing.

We have correlated all 20 retained native Qt libraries/plugins, including Qt PDF 6.140.0, with the official MSVC SDK sections, source commits and configured SBOMs. Full official sources and their notices are retained. Translation catalogs and optional image/platform plugins have been excluded; those questions no longer apply.

1. What source revisions, patches and wheel-specific build recipes/configurations produced the PySide and shiboken native binding libraries and the Pdf wrapper modules? Does pyside-setup 6.12.0 contain every binding modification used for PySide6_Pdf 6.12.0.140?
2. Please provide the applicable open-source copyright/third-party notice manifest for these binding binaries, and correct or explain the missing open-source license files in their wheel license directories.
3. For opengl32sw.dll SHA256 18aedc7a4b610f53bcc7b7a5c5ed9293c7e86f030e3273ad54ed3bb1ebd36702: executable/data sections match all three official Mesa 11.2.2 Qt archives. Banners identify LLVM 3.6.2. Does the preserved Qt llvmpipe attribution plus Mesa/LLVM source notices cover every compiled auxiliary component? Please identify any additional notice or distribution-specific attribution. A build recipe would help provenance, but we are not treating whole-file signature/hash differences as a source-compliance failure.

These details determine the binding source/build and configured-notice evidence required for our LGPL redistribution review. Native Qt SDK correspondence, translation provenance and bit-for-bit rebuild hashes are no longer open questions.

## Pillow Windows wheel maintainers

Channel: [Pillow issues](https://github.com/python-pillow/Pillow/issues).

Subject: Static AVIF dependency notices in pillow-12.3.0-cp313-cp313-win_amd64.whl

Our exact shipped extension probes report libavif 1.4.2, dav1d 1.5.3 and AOM 3.14.1. The 12.3.0 Windows recipe enables local AOM, dav1d, libyuv and libsharpyuv. libavif 1.4.2 selects the same codec versions and libyuv 644251f25. The wheel's combined LICENSE includes libavif and the dav1d-derived src/obu.c notice but has no AOM license/patent text or libyuv section. We added AOM's full LICENSE/PATENTS, dav1d's full COPYING, and recipe-selected libyuv LICENSE/PATENTS/AUTHORS to our distribution.

Please confirm the exact secondary static closure of _avif and _imaging for this Windows wheel, especially libyuv/libsharpyuv and TIFF/lzma, and identify any additional attribution missing from the combined LICENSE. A binary-specific manifest or linked-object/build record is sufficient. We do not need an inventory of optional dependencies: _imagingft is absent from our payload; _imagingtk is physically present but tkinter is absent. Other codec versions and PE import tables are already measured.

The purpose is to close actual binary-notice coverage, not to request sources for every permissive optional source-tree dependency.

## pdfium-binaries maintainer (pypdfium2 only)

Channel: [pdfium-binaries issues](https://github.com/bblanchon/pdfium-binaries/issues); involve [pypdfium2](https://github.com/pypdfium2-team/pypdfium2/issues) if needed.

Subject: Exact PDFium checkout for chromium/8076 Windows x64 release

The PDFium 156.0.8076.0 DLL in pypdfium2 5.14.0 matches chromium/8076's pdfium-win-x64.tgz byte for byte (SHA256 69f1e860f6742fbaafcc4db80e785eec9a4ee0da36ea6d1dc0867ea0f18baea6). We retain the release args.gn, all 14 release notices and builder revision f2e9a1c45bb17b85b540abf1af30146ef65416ac. All 14 notices are delivered identically with our installer. Windows x64 job 109383352997 in run 36410865276 succeeded; the license step derives its list from build.ninja.

1. What exact PDFium commit did that Windows x64 job check out? version.json records a null source hash. Current chromium/8076 head 8ca5b735df4263f43c830479b78213854a392c22 predates the build but is only an inference; public log download returns 403.
2. Did the license collection step emit any unhandled-library warnings, and does the archive's notice set cover the compiled Windows x64 DLL?

The recipe, patches, configuration and installed notice match are already retained. Exact source identity is useful provenance; whether that unresolved identity blocks permissive redistribution remains a separate reviewer decision. This request does not concern Qt PDF's different Chromium 140/PDFium build.

## Owner / qualified reviewer

Resolve applicable Microsoft runtime/SDK authorization for the 24 exact copies (MICROSOFT_RUNTIME_DECISION.md); choose app-local rights evidence or a separately tested official-prerequisite candidate. Review binding/Mesa/Pillow/PDFium notice sufficiency, LGPL replacement/debugging and installation-information applicability, source access/retention responsibilities, and ownership of application code/docs/assets. Supplied models remain excluded. Final decisions must identify the reviewed installer/inventory hashes. Clean-machine and interactive acceptance remain separate engineering gates.
