"""Fetch the two F3 paths read from an immutable artifact commit, in memory.

Run from the repository root with the artifact commit as the sole argument.
No score files are retained or redistributed.
"""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request


artifact = subprocess.check_output(
    ['git', 'rev-parse', sys.argv[1] + '^{commit}'], text=True).strip()


def committed(path):
    return subprocess.check_output(['git', 'show', f'{artifact}:{path}'])


guide = committed('data/README.md')
provenance = json.loads(committed('audit/audit.json'))['provenance']['scores']


def fetch(system):
    row = next(line for line in guide.decode().splitlines()
               if line.startswith(f'| {system} |'))
    cells = [cell.strip() for cell in row.split('|')[1:-1]]
    repository = re.search(r'\((https://github.com/[^)]+)\)', cells[1]).group(1)
    path = cells[2].strip('`')
    expected = provenance[system]
    assert cells[3].strip('`') == expected['sha256_16']
    assert int(cells[4].replace(',', '')) == expected['bytes']
    assert int(cells[5].replace(',', '')) == expected['lines']
    upstream_commit = subprocess.check_output(
        ['git', 'ls-remote', repository, 'HEAD'], text=True, timeout=60).split()[0]
    slug = repository.removeprefix('https://github.com/')
    url = f'https://raw.githubusercontent.com/{slug}/{upstream_commit}/{path}'
    request = urllib.request.Request(url, headers={'User-Agent': 'M1-F3-path-verification'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
        status = response.status
        final_url = response.url
    observed = {'sha256': hashlib.sha256(data).hexdigest(),
                'bytes': len(data), 'lines': len(data.splitlines())}
    assert status == 200
    assert observed == {key: expected[key] for key in observed}, (system, observed)
    return {'system': system, 'documented_repository': repository,
            'documented_path': path, 'upstream_commit': upstream_commit,
            'requested_url': url, 'final_url': final_url, 'http_status': status,
            'observed': observed, 'full_hash_bytes_lines_match': True}


with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(fetch, ['XLSR-Mamba', 'XLSR-Conformer']))
report = {'artifact_commit': artifact,
          'guide_git_blob': subprocess.check_output(
              ['git', 'rev-parse', f'{artifact}:data/README.md'], text=True).strip(),
          'guide_sha256': hashlib.sha256(guide).hexdigest(),
          'fetched_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'method': 'Read paths and provenance with git show; resolve upstream HEAD; '
                    'HTTP GET complete immutable raw files into memory; compare full SHA-256, bytes and lines.',
          'fetches': results}
Path('paper/f3-validation/score-fetch.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
