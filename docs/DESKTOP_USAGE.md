# Windows desktop workflow

Installed NutCase users should start with [installation and troubleshooting](INSTALLATION.md).
The steps below describe the retained source launcher. Installed settings and
drawings use `%LOCALAPPDATA%\NutCase` instead of the repository's `output` folder.

Run **NutCase.cmd** from the project folder after preparing the external `.venv-gui` environment. The launcher discovers and probes FreeCAD through `scripts/analyze-step.ps1`. The GUI remembers runtime/output settings and recent STEP locations.

1. **Browse** any `.step` or `.stp` file, then **Analyze Geometry**. Review the source validation summary. Files do not need to be in `input/`.
2. Choose **Basic**, **Comprehensive**, or **Custom**. Select sheet size, scale, optional views and title-block metadata.
3. In **Custom**, use the **Dimensions** tab. Values are measured, read-only source geometry. Select a row to read its full description, supporting evidence or unresolved reason. A checked unsupported candidate still requires backend verification and can remain unresolved.
4. **Generate Drawing** runs analysis, native associative dimensioning, PDF normalization, independent PDF verification and atomic publication. The stage indicator has no invented percentage. **Show Logs** exposes errors and processing messages.
5. The final normalized PDF appears after the current manifest and all recorded artifact hashes pass validation. Use zoom, fit and page controls. **Engineering Review** separates source problems, unresolved recognition, dimension verification and engineering approval.
6. **Save PDF As** and **Save Project As** copy and verify finished files. **Open PDF** dispatches to the Windows default viewer in a bounded external helper; a stuck association cannot freeze the utility. **Open In FreeCAD** opens the editable project. Use FreeCAD Save As for edits rather than overwriting a published release.

**Save Configuration** persists the versioned drawing-policy JSON in `output/gui-state/configurations/`. Generation also saves the selected policy. **Load JSON** imports an existing policy after analysis. Changing dimensioning mode clears explicit inclusions/exclusions, as stated beside the control. Compatible saved selections restore only after fresh native analysis. An incompatible source binding blocks generation; **Start New Configuration** explicitly starts fresh, and saving archives the previous policy, including corrupt old JSON bytes.

A failed or cancelled generation clears the preview. The previous valid release remains on disk and is available only through explicit **Open Current Release** or **Open Previous Release**. Historical previews display their run ID and drawing mode; they do not change your editing configuration.

**Cancel Processing** requests a safe stop. Closing a busy window first requests cancellation. Native workers and their descendants are contained by Windows job objects. Cancellation is checked before publication; a request after the atomic commit can correctly finish as a completed release. PDF normalization/verification check cancellation between stages rather than inside every operation. After an abnormal process exit, a stale `.generation.lock` may remain: inspect its recorded PID and retained run before removing it. The program never steals a lock.

The two supplied models still fail extended Boolean validation. Completed drawings therefore report engineering review required. A verified PDF, verified CAD references and a source-measured value do not establish nominal specifications or manufacturing approval.

## External runtime setup

Use a regular external 64-bit Windows CPython installation. Source checks have used Python 3.12 and the build/test environment uses Python 3.13. Keep FreeCAD's bundled Python unchanged. For example:

```powershell
py -3.12 -m venv .venv-gui
.\.venv-gui\Scripts\python.exe -m pip install -r requirements-gui.txt
```

`requirements-gui.txt` pins PySide6 6.12.0 and the separate PySide6_Pdf 6.12.0.140 wheel, with pypdf 6.10.0, pypdfium2 5.14.0 and Pillow 12.3.0 through the pipeline requirements. The application uses Qt PDF directly. The frozen bundle excludes Qt WebEngine/QML and unused translation catalogs/plugins; see [packaging](WINDOWS_PACKAGING.md) and [licensing review](LICENSING_AUDIT.md).

If a prepared environment lacks pip, a base Python installation with pip can populate or update it using `--python`:

```powershell
py -3.12 -m pip --python .venv-gui\Scripts\python.exe install -r requirements-gui.txt
```

Provide Poppler on PATH or set `FASTENER_POPPLER` to `pdftoppm.exe`. Alternatively:

```powershell
.\scripts\launch-gui.ps1 -InputFile 'C:\models\part.step' `
  -Poppler 'C:\tools\poppler\Library\bin\pdftoppm.exe'
```

The launcher accepts `-FreeCADHome`, `-GuiPython` (or `FASTENER_GUI_PYTHON`) and `-OutputDirectory`. FreeCAD's install location is discovered rather than assumed. You can also run the portable external-Python entry point:

```powershell
.\.venv-gui\Scripts\python.exe src\entrypoints\fastener_gui.py 'C:\models\part.step' `
  --freecad-python 'C:\path\to\FreeCAD\bin\python.exe' `
  --poppler 'C:\path\to\pdftoppm.exe' --output-dir output\gui
```

The gear button at the upper right opens **Settings**. Under **Appearance**, choose **Light Mode**, **Dark Mode**, or **System Default**. System Default is the initial setting and follows the Windows app-color preference, including changes while NutCase is open. Theme changes preview immediately; **OK** saves the preference and **Cancel** restores the previous theme.

Runtime and output paths are editable in the separate **Runtime And Output** section of Settings. Missing or invalid paths produce diagnostic errors without publishing a defective release. Runtime and source paths may contain spaces. A long filename is visible through the source field tooltip.

For a repeatable startup diagnostic, run `& '.\NutCase.cmd' -StartupCheck`. It imports the external dependencies, discovers/probes native FreeCAD, initializes the actual Qt window and event loop, prints `GUI_STARTUP_OK`, and exits. It uses disposable settings without altering your saved GUI state or generating a drawing. The shell probes use `src/entrypoints/probe_runtime.py`, avoiding embedded Python quoting differences between Windows PowerShell 5.1 and PowerShell 7.

## Runtime verification

Run `& '.\NutCase.cmd' -StartupCheck` to verify dependencies, native FreeCAD discovery and actual Qt initialization without generation or saved-settings changes. To inspect native capabilities, run `scripts/analyze-step.ps1 -InspectEnvironment`. Full drawing generation automatically verifies geometry references, measurements, native reopen, normalized PDF content and independent renderer output before publication.

All Python application packages, command-line entry points and internal workers live under `src/`. Windows PowerShell launchers remain in `scripts/`, with the double-click launcher at the project root. Development regression suites and independent fixtures are retained in the test directories listed in the [README](../README.md). The pipeline's automatic verification gates remain active.
