# Windows packaging and build

NutCase 0.6.0 targets x64 Windows 10 1809+ and Windows 11. The release candidate
uses CPython 3.13.16, PySide6/Qt 6.12.0 (Qt PDF wheel 6.12.0.140), pypdf 6.10.0,
pypdfium2 5.14.0 and Pillow 12.3.0. The validated native prerequisite is the
separately installed 64-bit FreeCAD 1.1.x desktop application; 1.1.4 is tested.
Other FreeCAD branches require renewed native/geometry validation.
The Windows baseline follows [Qt 6.12's supported platforms](https://doc.qt.io/qt-6.12/supported-platforms.html).

## Architecture choice

| Option | Assessment |
| --- | --- |
| PyInstaller directory bundle | Chosen: mature Windows/PySide hooks, includes CPython and dependencies, readily inspected DLLs, short startup, source still available to FreeCAD. No runtime extraction lifecycle to interfere with cancellation. |
| PyInstaller single file | Deferred: extraction and parent/child lifetime add complexity to an application with nested native processes. Little benefit inside an installer. |
| Nuitka standalone | Viable alternative with an official PySide plugin. Adds a C compiler/toolchain and compile time; no CAD benefit because the heavy work remains external. Still requires explicit worker dispatch and DLL isolation. |
| Inno Setup | Chosen: a small script supplies per-user installation, shortcuts, version metadata, upgrades and uninstall. No MSI-specific enterprise requirement currently exists. |
| WiX | Suitable for managed MSI deployment, repair and enterprise policy. More installer/component authoring and a .NET build dependency; reconsider for enterprise deployment. Current revenue-generating-use maintenance terms also need review. |

`NutCase.exe` is a windowed GUI. `NutCaseWorker.exe` is a console worker whose
stdout is captured by QProcess; users do not see a console. Explicit `gui-job`,
`pipeline`, `open-file` and `diagnose` dispatch replaces interpreter/script
assumptions. The GUI does not launch another GUI with Python arguments.

The worker contains PDF processing and its Python dependencies. It launches the
separately installed FreeCAD `bin/python.exe` against `native-src/entrypoints/`.
All application `.py` sources are present, retaining the bootstrap, relative
modules and native finishing process. FreeCAD, Part and TechDraw are excluded
from the frozen worker; native CAD stays in the prerequisite's own interpreter.

Windows job objects retain the GUI → worker → native descendant containment.
Cooperative cancellation still precedes atomic publication. Exit 2 remains a
complete preliminary drawing requiring review. Packaging preserves
manifest hashes, source binding, PDF normalization, native reopen/measurement
checks, source integrity or previous-release preservation.

PyInstaller's DLL search directory is reset around external process creation,
then restored. Child environments remove Python/Qt overrides and bundled PATH
entries. This avoids mixing NutCase's Qt with FreeCAD's Qt or Poppler's DLLs.
Poppler's `pdftoppm.exe` and recursive PE import closure live in an independent
`vendor/poppler` directory. Runtime Qt/CPython DLLs remain separate and
replaceable. Qt WebEngine/QML are not application features and are excluded.

`NutCaseVerify.exe` is a separately frozen regression harness sharing the bundle.
The installer excludes it. It drives the actual GUI controllers, workers and
preview without a development interpreter, and can target an installed worker.

## Repeatable build

On a Windows x64 build machine, from the repository:

```powershell
.\scripts\build-windows.ps1 -Bootstrap
```

This is a maintainer command, never an end-user installation step. Bootstrap
downloads PSF's NuGet CPython build runtime, Inno Setup 7.1.0 and Poppler
26.09.0-0 into `.build-tools`, verifies committed SHA-256 pins, creates
`.venv-build` and installs the exact wheel hashes in `packaging/windows.lock`.
It does not use the Codex runtime or modify FreeCAD. Internet access is needed
on first bootstrap. Inno compiler setup registers its own per-user uninstall
entry; this compiler is a build-machine tool, not part of the NutCase installer.

Subsequent offline builds can use `scripts/build-windows.ps1` once all inputs
are cached. `requirements-build.txt` records versions; `windows.lock` pins the
exact Windows/CPython wheels. Review and update pins deliberately with
`packaging/lock_wheels.py`, never automatically during a release build.

The build checks versions/input hashes, runs packaging regressions, freezes
the executables, stages immutable sources/resources/notices, records a file
hash inventory, and compiles Inno Setup. Outputs:

- `dist/NutCase/NutCase.exe` with the entire adjacent directory required.
- `artifacts/NutCase-0.6.0-windows-x64-setup.exe`.
- `artifacts/NutCase-0.6.0-source.zip`, containing the actual working source built.
- `artifacts/SHA256SUMS.txt` and `artifacts/nutcase-build.json`.

The procedure is repeatable; PE timestamps and installer metadata mean builds
are not claimed to be bit-for-bit reproducible. The source archive is application
source, **not** complete corresponding source for every bundled dependency.

## Candidate verification

```powershell
.\scripts\verify-windows.ps1
```

This runs the frozen GUI/worker, both supplied models in Basic/Comprehensive/
Custom modes, source-bound save/restart, Qt PDF rendering, checked exports,
cancellation and failure preservation. It uses an isolated `artifacts` data
directory, a PATH without development Python and a Unicode/space/ampersand
import/export path. Evidence is retained in `artifacts/verification/`.

Installer lifecycle testing is separate:

```powershell
.\scripts\verify-installer.ps1 -NativeRegression
```

It refuses to overwrite an existing NutCase registration, installs into a
dedicated workspace directory, verifies the installed GUI and shortcuts, denies
installation writes, exercises generation, tests a same-version update, uninstalls,
reinstalls and uninstalls again while checking retained data. `-OpenExternal`
additionally opens the final PDF and FCStd; close the test viewers when finished.
`-OpenExisting` checks external dispatch against retained results without
regenerating them. The tests create real per-user Windows registration/shortcuts
and use an isolated data directory. See the archived packaging evidence for measured results
and this host's AppData virtualization limitation. A developer-machine test is
not a clean-VM test.

The GitHub Actions workflow builds candidates on matching version tags or manual
dispatch and uploads workflow artifacts. It has no release publication step,
release-write permission or signing credentials. Native FreeCAD regression
requires the local harness or a dedicated runner with FreeCAD. Workflow success
alone is not final release acceptance.

Primary references: [PyInstaller operation](https://pyinstaller.org/en/stable/operating-mode.html),
[external process pitfalls](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html),
[Nuitka manual](https://nuitka.net/user-documentation/user-manual.html),
[Inno Setup](https://jrsoftware.org/isinfo.php), [WiX](https://docs.firegiant.com/wix/).
