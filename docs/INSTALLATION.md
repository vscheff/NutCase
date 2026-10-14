# Install and use NutCase

This is a candidate for acceptance testing, not an official published release.

1. Use 64-bit Windows 10 1809 or newer, or Windows 11.
2. Install the **64-bit FreeCAD 1.1.x desktop application** from
   [FreeCAD's official downloads](https://www.freecad.org/downloads.php). NutCase
   was tested with 1.1.4. FreeCAD is a separate prerequisite.
3. Obtain `NutCase-0.6.0-windows-x64-setup.exe` and compare its SHA-256 with the
   accompanying `SHA256SUMS.txt`. For the first candidate these are local files;
   future approved releases will be on [GitHub Releases](https://github.com/vscheff/NutCase/releases).
4. Run the installer, accept the GPL license, choose a destination and optionally
   select a desktop shortcut. The default is `%LOCALAPPDATA%\Programs\NutCase`.
5. Start **NutCase** from the Start Menu. Browse any `.stp` or `.step` file,
   analyze, choose Basic/Comprehensive/Custom, generate, and review the warnings.

Python, pip, environment variables and PowerShell are unnecessary for users.
The application includes its Python runtime, Qt PDF preview, PDF normalization,
PDFium and Poppler. Do not move just `NutCase.exe` out of its installation folder.

## Data, updates and uninstall

| Location | Contents |
| --- | --- |
| `%LOCALAPPDATA%\NutCase\gui-state` | Settings, source-bound configurations and policy history |
| `%LOCALAPPDATA%\NutCase\drawings` | Complete releases, current manifests, worker requests and per-run logs/diagnostics |
| `%LOCALAPPDATA%\NutCase\logs` | Rotating application logs and windowed-console diagnostics |
| `%LOCALAPPDATA%\NutCase\cache` | Isolated batch FreeCAD preferences, disposable temporary/startup files |

Use Settings to choose a different drawing directory, including a path with
spaces or Unicode. Keep source models in their original locations; NutCase does
not modify them. Save PDF As / Save Project As writes checked copies wherever
you choose. The complete retained release includes engineering-review evidence.

An update uses the same application identity and replaces application files.
Exit NutCase and finish/cancel work before updating. Do not use the application
installation folder as an output directory. Source/development settings remain
in `output/gui-state`; installed NutCase starts separately. Existing JSON
policies remain compatible: analyze the same source and use Load JSON to import
one. Retain the `source_binding` block. Old drawing directories can be selected
in Settings; files/manifests are never rewritten to migrate them automatically.

Uninstall through Windows Settings → Apps → NutCase, or the Start Menu uninstall
shortcut. Drawings, configurations, logs, caches and exported copies are
preserved. Reinstallation by the same Windows user restores the same settings.
Back up the data directory and external drawing directories. Removing user data
is a deliberate manual action, separate from uninstall.

## Troubleshooting

- **FreeCAD not found:** install 64-bit FreeCAD 1.1.x and restart. NutCase probes
  PATH, uninstall registry entries and normal installation folders. For a portable
  installation choose its `bin/python.exe` in Settings. NutCase checks the native
  version, architecture and Part/TechDraw/GUI imports. It does not install FreeCAD.
- **PDF renderer missing:** repair/reinstall NutCase. Bundled Poppler is the normal
  default; a custom renderer is an advanced override.
- **Drawing requires review / exit 2:** generation completed. Geometry or dimension
  limitations still require engineering review. This is not a process failure.
- **Failure/cancellation:** the previous manifest/release remains intact. Inspect
  Show Logs and the retained run. Open Current Release or a previous release to
  explicitly load it again. Never mistake a failed preview for a newly approved
  drawing.
- **Stale `.generation.lock`:** verify that its recorded process is no longer
  running before removing that one lock. The app never steals an active lock.
- **Output path too long:** the native Windows pipeline retains its explicit
  260-character guard. Choose a shorter drawing directory or shorter source
  filename; spaces and special characters do not themselves cause failure.
- **Windows blocks an unsigned file:** this candidate is unsigned. SmartScreen or
  local application-control policies may warn or block it. Verify provenance and
  checksum and follow your organization's approval process; do not disable
  security protections globally. Code signing can be added before public release.

Every drawing is preliminary. NutCase assigns no manufacturing approval, nominal
dimensions, tolerances, material, thread specifications or GD&T automatically.
