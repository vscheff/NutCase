# NutCase 0.6.0 — Windows packaging candidate

NutCase can now be installed as a conventional per-user Windows application.
The installer includes Python, GUI/PDF dependencies and the Poppler renderer,
creates a Start Menu shortcut, offers a desktop shortcut and supplies uninstall.
64-bit FreeCAD 1.1.x remains a separate prerequisite and is automatically probed.

Settings, source-bound configurations, drawings and diagnostics are stored in
user application data and preserved during update/uninstall. The frozen worker
retains native process isolation, Windows job containment, cancellation,
normalized independently checked PDFs and atomic verified release publication.
Executable/installer metadata consistently identifies NutCase 0.6.0. The standard
temporary icon remains pending an approved design asset.

This is an unsigned local candidate for final human acceptance. It has not been
tested on a clean Windows VM. Dependency corresponding-source/notices review
remains a public-release gate. No official GitHub release has been published.
Drawings remain preliminary and require engineering verification.
