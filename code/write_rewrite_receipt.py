"""Assemble a successor payload receipt without changing historical receipts.

Run after all stage-specific files and validation outputs have been written,
then run build_manifest.py and verify_release_receipt.py.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_release import release_files


def binding(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('artifact', 'submission'))
    parser.add_argument('--artifact-commit')
    args = parser.parse_args()
    final = args.stage == 'submission'
    receipt = 'paper/RELEASE-RECEIPT-REWRITE-' + ('FINAL' if final else 'ARTIFACT') + '.json'
    predecessor = ('paper/RELEASE-RECEIPT-REWRITE-ARTIFACT.json' if final
                   else 'paper/RELEASE-RECEIPT-REVISION-FINAL.json')
    previous = json.loads((ROOT / predecessor).read_text())['release_members']
    members = {name: binding(ROOT / name) for name in sorted(release_files() - {receipt})}
    added = sorted(set(members) - set(previous))
    changed = {}
    dispositions = {}
    unchanged = 0
    reasons = {
        'paper/main.tex': 'Concentration frame, complete primary evidence and bounded controls; submission stage pins the artifact hash.',
        'paper/main.pdf': 'Final PDF rebuilt only after the new artifact hash was committed and inserted.',
        'paper/semantic_obligations.json': 'Retain every inherited obligation and deletion-test all new PDF claims and table rows.',
        'code/check_numbers.py': 'Checker changes forced by replaced tables and relocated simulation summaries; all scientific obligations retained.',
        'SUPPLEMENT.md': 'Retain the broader artifact and explicitly archive superseded manuscript obligations.',
        'paper/SUPPLEMENT.md': 'Byte-identical copy of the root supplement.',
        'paper/refs.bib': 'Remove the now-uncited Arena entry; preserve it separately in the artifact.',
    }
    for name in sorted(set(members) | {receipt, 'MANIFEST.json'}):
        current = members.get(name)
        before = previous.get(name)
        if before is not None:
            before = {key: before[key] for key in ('sha256', 'bytes')}
        if current is not None and before == current:
            unchanged += 1
            dispositions[name] = {'status': 'unchanged', 'baseline': current,
                                  'why': 'Retain predecessor payload bytes.'}
        else:
            why = reasons.get(name, 'Concentration rewrite assembly, stage-specific verification or provenance record.')
            dispositions[name] = {'status': 'added' if name in added else 'changed',
                                  'findings': ['concentration_rewrite'], 'why': why}
            if name in previous:
                changed[name] = {'previous': before, 'current': current,
                                 'findings': ['concentration_rewrite'], 'why': why}
    result = {
        'schema': 'm1-republication-receipt-v1',
        'stage': args.stage,
        'stage_note': ('The PDF is rebuilt from the pinned artifact source plus its final locator.' if final else
                       'The revised source and evidence are final; paper/main.pdf is inherited from 8276097 and is not this source rendering.'),
        'baseline_submission_commit': '8276097',
        'artifact_commit': args.artifact_commit,
        'predecessor': {'path': predecessor, 'binding': binding(ROOT / predecessor)},
        'release_members': members,
        'changes_from_predecessor': changed,
        'added_members': added,
        'member_disposition': dispositions,
        'findings_record': {'findings': {'concentration_rewrite':
                            'Implement the bounded JUDGEMENT-3 frame and PDF-only evidence requirement.'}},
        'audit': {'identified_pdf_sha256': members['paper/main.pdf']['sha256'],
                  'scope': 'Local assembly and byte binding; no new external acceptance review is claimed.'},
        'counts': {'payload_members': len(members), 'previous_payload_members': len(previous),
                   'changed_previous_bindings': len(changed), 'unchanged_previous_bindings': unchanged,
                   'added_members': len(added), 'removed_members': len(set(previous) - set(members))},
    }
    assert not (set(previous) - set(members)), 'The rewrite must not remove artifact members.'
    (ROOT / receipt).write_text(json.dumps(result, indent=2) + '\n')
    print(f'Wrote {receipt}: {len(members)} payload members; {len(changed)} changed, {len(added)} added; none removed.')


if __name__ == '__main__':
    main()
