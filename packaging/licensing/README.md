# Windows redistribution evidence workflow

Public distribution remains blocked. This directory retains acquisition, inspection,
verification and source-packaging tools, exact upstream notices, source manifests,
component decisions and outstanding obligations. Technical integrity is separate
from legal adequacy and publication approval.

## Immutable reference evidence

`reference-inventory.zip` contains the exact inspected candidate inventory and
SPDX document. Its original file hashes and unresolved decisions are unchanged.
The verifier reads that archive directly. A new explicit `inventory.json`, when
present, takes precedence in the build workflow; installer binding requires such
a working review and cannot modify the archived reference.

`artifacts/licensing-history.zip` retains the original installers, candidate
payloads, source archives, source/build receipts, baseline metadata, installed
inventories, acceptance reports, frozen verifier and test-recovery provenance.
Its SHA-256 is in `artifacts/licensing-history.sha256`. Historical identifiers
inside these immutable records are preserved as evidence, not current project
organization. The archive is local, ignored by Git, and must be backed up with
the source materials before any approved distribution.

Restore reference material only when needed, using disposable ignored directories:

```powershell
& .venv-build/Scripts/python.exe packaging/licensing/restore_reference.py --scope materials
& .venv-build/Scripts/python.exe packaging/licensing/restore_reference.py --scope candidate
& .venv-build/Scripts/python.exe packaging/licensing/restore_reference.py --scope frozen
```

These restore to `artifacts/licensing-materials`, `artifacts/licensing-candidate`
and `dist/NutCase`. The original names and bytes inside restored reference
payloads are necessary for historical hash checks. Restoration rejects traversal
and refuses to overwrite differing existing evidence. `--destination` can select
another disposable directory inside this workspace. `--scope baseline` restores
the original baseline payload for origin matching and historical audit reproduction.

## Verify the inspected candidate

After restoring materials and candidate evidence:

```powershell
& .venv-build/Scripts/python.exe packaging/licensing/verify.py `
  --bundle artifacts/licensing-candidate/candidate-final `
  --review packaging/licensing/reference-inventory.zip `
  --materials artifacts/licensing-materials `
  --supplemental-materials artifacts/licensing-candidate/research `
  --installer artifacts/licensing-candidate/release/NutCase-0.6.0-windows-x64-setup.exe `
  --report build/licensing-reference-check.json
& .venv-build/Scripts/python.exe scripts/run-tests.py --suite packaging
```

Exit 2 preserves the recorded unresolved licensing/acceptance findings. Integrity
checks must still pass: every payload file, generated installer resource, source
material, source/build archive member and installer hash is checked independently.
Unexpected, missing or changed evidence fails closed. A LICENSE/README filename
does not establish source completeness or redistribution rights.

The cleanup changed active source, report terminology and documentation. The
archived review describes its original candidate; a new build requires a new
explicit payload review and actual installer binding. Do not refresh hashes just
to silence failures. `-AllowUnresolvedLicensing` permits already-recorded review
findings for a local candidate only; it cannot bypass integrity failures.

## Continue the licensing task

`OUTSTANDING_OBLIGATIONS.md`, `obligations.json`, `UPSTREAM_CLARIFICATIONS.md` and
`MICROSOFT_RUNTIME_DECISION.md` retain the unresolved decisions and prepared
upstream requests. No request has been sent and no release has been published.

Native Qt SDK correspondence is established. Remaining work includes exact
PySide/shiboken/PDF binding build and notice evidence, Mesa/LLVM compiled notice
closure, Pillow/PDFium attribution review, Microsoft redistribution authorization,
LGPL replacement/source-delivery adequacy, ownership and final human acceptance.

The acquisition scripts (`research.py`, `extra_research.py`, `inspect_archives.py`,
`conda_audit.py`, `acquire_recipe_sources.py`) retain original source/provenance
workflows. Restore materials before using them to avoid redundant downloads.
Audit-only zstandard/PyYAML dependencies restore under the materials' `audit-tools`
directory and do not belong to the application runtime.

`review_candidate.py` performs an explicitly invoked candidate audit; build and
release gates never call it automatically. It rejects unreviewed dependency
changes. Authored documentation removals require explicit
`--allow-removed-resource` entries. `inspect_frozen.py` inventories current frozen
Python; `bind_installer.py` compares an actual isolated installation with a
separately recorded working review. `package_review.py` checks source/supplemental
hashes, excludes local binary evidence, and creates adjacent source assets without
approving unresolved findings.

Retain all immutable source archives and build/interface/patch metadata. Resolve
the remaining decisions, complete clean-machine/interactive/real-upgrade acceptance,
then obtain explicit approval for the exact release. The GitHub workflow has no
automatic publication or signing step.
