# Mocked GUI test data

`synthetic_source.json` is newly constructed from a hollow cylinder with known
18 mm length, 10 mm external diameter and 4 mm bore. Regenerate it with FreeCAD's
bundled Python using `tests_support/build_gui_fixture.py`. The earlier
`recorded_source.json` was not recovered; no supplied model data is redistributed.
The unsupported candidate, Boolean warning and drawing verification flags are
explicitly MOCK data for testing UI branches, never engineering evidence.

`../fixture.py` constructs an isolated manifest/history and a blank PDF plus
placeholder FCStd bytes for fast widget, path and export-checksum tests. Its
verification flags are mocked test inputs, not fresh CAD/PDF verification.
These files must never be used as engineering deliverables. Real FreeCAD and
PDF behavior is covered separately by the existing native/PDF suites and the
nine-case `tests_gui/test_cad_workflow.py` matrix when optional local samples are
enabled (three cases with the independent synthetic source alone).

The fast GUI suite does not depend on prior generated drawing files.
