"""Read-only recovery from Codex patch records; never changes recovery sources.

Writes exact patch inputs and replayed files only into a new evidence directory.
Use --session PATH --output PATH. Does not overwrite an existing evidence run.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def relevant(path):
    return any(part in path.replace('\\', '/').split('/') for part in
               ('tests', 'tests_pdf', 'tests_gui', 'tests_launchers')) or any(
        name in path for name in ('build_fixtures', 'validate_phase', 'fixture'))


def apply_hunk(lines, hunk, cursor):
    old = [s[1:] for s in hunk if s.startswith((' ', '-'))]
    new = [s[1:] for s in hunk if s.startswith((' ', '+'))]
    matches = [i for i in range(cursor, len(lines)-len(old)+1) if lines[i:i+len(old)] == old]
    if not matches:
        raise ValueError('Historical patch context is absent after the previous hunk')
    i = matches[0]
    return lines[:i] + new + lines[i+len(old):], i+len(new)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--session', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--through-line', type=int, help='Bound recovery to a historical session prefix')
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    files, provenance, failures, patches = {}, {}, [], []
    for number, line in enumerate(args.session.open(encoding='utf-8'), 1):
        if args.through_line is not None and number > args.through_line:
            break
        payload = json.loads(line).get('payload', {})
        if payload.get('type') != 'custom_tool_call':
            continue
        code = payload.get('input', '')
        if payload.get('name') == 'apply_patch':
            inputs = [code]
        else:
            inputs = [json.loads(m.group(1)) for m in re.finditer(
                r'tools\.apply_patch\(("(?:\\.|[^"\\])*")\)', code)]
        for patch in inputs:
            if '*** Begin Patch' not in patch:
                continue
            sections = re.split(r'^\*\*\* (Add|Update|Delete) File: (.+)\n', patch, flags=re.M)
            if not any(relevant(sections[i+1]) for i in range(1, len(sections), 3)):
                continue
            index = len(patches)
            (args.output/f'patch-{index:03}.txt').write_text(patch, encoding='utf-8')
            patches.append({'session_line': number, 'call_id': payload.get('call_id'), 'file': f'patch-{index:03}.txt'})
            for i in range(1, len(sections), 3):
                action, original, body = sections[i:i+3]
                if not relevant(original):
                    continue
                name = original.replace('\\', '/').split('FastenerDrawing/')[-1].split('NutCase/')[-1]
                if name.startswith('C:') or '..' in Path(name).parts:
                    failures.append({'path': original, 'line': number, 'error': 'Unexpected recovery path'})
                    continue
                body = body.split('*** End Patch')[0].split('*** Move to:')[0]
                rows = body.rstrip('\n').splitlines()
                try:
                    if action == 'Add':
                        if name in files:
                            raise ValueError('Duplicate historical add')
                        files[name] = [s[1:] for s in rows if s.startswith('+')]
                    elif action == 'Update':
                        if name not in files:
                            raise ValueError('Update without recovered base')
                        hunks = re.split(r'^@@([^\n]*)\n', body, flags=re.M)[1:]
                        cursor = 0
                        updated = list(files[name])
                        for j in range(0, len(hunks), 2):
                            anchor, h = hunks[j:j+2]
                            if anchor.strip():
                                found = [n for n in range(cursor, len(updated)) if updated[n].strip() == anchor.strip()]
                                if not found:
                                    raise ValueError('Missing historical jump anchor')
                                cursor = found[0]+1
                            updated, cursor = apply_hunk(updated, [s for s in h.rstrip('\n').splitlines()
                                                                  if s and s[0] in ' +-'], cursor)
                        files[name] = updated
                    # Retain last available contents even for a historical deletion.
                    provenance.setdefault(name, []).append({'action': action, 'session_line': number, 'patch': index})
                except ValueError as exc:
                    failures.append({'path': name, 'line': number, 'error': str(exc)})
    rows = []
    for name, lines in files.items():
        target = args.output/'original'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
        rows.append({'path': name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                     'events': provenance.get(name, [])})
    result = {'session': str(args.session), 'session_sha256': hashlib.sha256(args.session.read_bytes()).hexdigest(),
              'method': 'Exact JSON-decoded patch inputs; sequential contextual replay; failures retained explicitly',
              'files': rows, 'patches': patches, 'replay_failures': failures}
    (args.output/'provenance.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'recovered_files': len(rows), 'replay_failures': failures, 'paths': [r['path'] for r in rows]}, indent=2))


if __name__ == '__main__':
    main()
