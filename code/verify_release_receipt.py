#!/usr/bin/env python3
"""Verify the successor M1 receipt and its change ledger against release bytes."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_release import release_files

RECEIPT = 'paper/RELEASE-RECEIPT-REWRITE-FINAL.json'

def binding(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

def main():
    receipt = json.loads((ROOT/RECEIPT).read_text())
    assert receipt['schema'] == 'm1-republication-receipt-v1'
    members = receipt['release_members']
    assert set(members) == release_files() - {RECEIPT}, 'payload membership differs'
    for name, value in members.items():
        assert binding(ROOT/name) == value, name
    previous_path = receipt['predecessor']['path']
    assert binding(ROOT/previous_path) == receipt['predecessor']['binding']
    previous = json.loads((ROOT/previous_path).read_text())['release_members']
    expected_changes = {}
    unchanged = 0
    for name, value in previous.items():
        old = {k:value[k] for k in ('sha256','bytes')}
        new = members.get(name)
        if old != new:
            expected_changes[name] = (old, new)
        else:
            unchanged += 1
    changes = receipt['changes_from_predecessor']
    assert set(changes) == set(expected_changes)
    for name, (old, new) in expected_changes.items():
        assert changes[name]['previous'] == old and changes[name]['current'] == new, name
        assert changes[name]['why'].strip(), name
    added = set(members) - set(previous)
    assert set(receipt['added_members']) == added
    dispositions = receipt['member_disposition']
    assert set(dispositions) == set(members) | {RECEIPT, 'MANIFEST.json'}
    findings = set(receipt['findings_record']['findings'])
    for name, item in dispositions.items():
        assert item['why'].strip(), name
        if item['status'] == 'unchanged':
            assert item['baseline'] == members[name], name
            assert name in previous and members[name] == {
                k:previous[name][k] for k in ('sha256','bytes')}, name
        else:
            assert item['status'] in ('changed', 'added'), name
            assert item['findings'] and set(item['findings']) <= findings, name
            assert item['status'] == ('added' if name in added else 'changed'), name
    for name, item in changes.items():
        assert item['why'] == dispositions[name]['why'], name
        assert item['findings'] == dispositions[name]['findings'], name
    assert receipt['audit']['identified_pdf_sha256'] == members['paper/main.pdf']['sha256']
    assert receipt['counts'] == {'payload_members': len(members),
        'previous_payload_members': len(previous), 'changed_previous_bindings': len(changes),
        'unchanged_previous_bindings': unchanged, 'added_members': len(added),
        'removed_members': len(set(previous)-set(members))}
    print(f'PASS — successor receipt: {len(members)} payload bindings, 0 mismatches; '
          f'{len(changes)} changed, {unchanged} unchanged, {len(added)} added, '
          f'{len(set(previous)-set(members))} removed.')
    print(f'PASS — {len(dispositions)} release members have baseline or finding-linked dispositions; PDF matches the supplied-revision binding.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
