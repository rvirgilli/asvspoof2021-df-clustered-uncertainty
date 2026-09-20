"""FIX5 deterministic speaker deletions for the three printed SSL pairs.

Run: uv run --frozen python code/influence_trial_id.py
Inputs: the public files in ABLATION-RESULTS.json, relative to M1_INPUT_ROOT.
Output: regenerated/influence-trial-id.json (refuses overwrite).
The only non-standard dependency is NumPy, pinned by uv.lock. Historical
strategy_influence.py and evidence/influence.json remain reproducible as released.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'regenerated/influence-trial-id.json')
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    inputs = json.loads((ROOT/'ABLATION-RESULTS.json').read_text())['inputs']
    expected = json.loads((ROOT/'evidence/ABLATION-RESULTS.json').read_text())['inputs']['sha256']
    assert inputs['sha256'] == expected
    base = Path(os.environ.get('M1_INPUT_ROOT', ROOT))
    paths = {name: base/relative for name, relative in inputs['paths'].items()}
    for name, path in paths.items():
        assert sha(path) == expected[name], name
    metadata = {p[1]: p for line in paths['protocol_key'].read_text().splitlines()
                if (p := line.split())[7] == 'eval'}
    trials = sorted(metadata)
    labels = np.array([metadata[t][5] == 'bonafide' for t in trials])
    speakers = np.array([metadata[t][0] for t in trials])
    groups = np.unique(speakers)
    assert len(trials) == 533928 and len(groups) == 93
    names = inputs['systems'][:4]
    orders = []
    for name in names:
        scores = {p[0]: float(p[1]) for line in paths[name].read_text().splitlines()
                  if (p := line.split())}
        values = np.array([scores[t] for t in trials])
        assert np.isfinite(values).all()
        # Stable sorting preserves the ascending trial-ID order within equal scores.
        orders.append(np.argsort(values, kind='stable'))

    def refit(keep):
        result = []
        for order in orders:
            lab = labels[order]
            weights = keep[order]
            bona = np.cumsum(weights * lab, dtype=np.float64)
            spoof = np.cumsum(weights * ~lab, dtype=np.float64)
            frr, far = bona/bona[-1], 1-spoof/spoof[-1]
            first = np.argmin(np.abs(frr-far))
            result.append(50 * (frr[first]+far[first]))
        return np.array(result)

    full = refit(np.ones(len(trials), dtype=bool))
    deletions = np.array([refit(speakers != group) for group in groups])
    results = {}
    for i, j in [(0, 2), (1, 2), (2, 3)]:
        gaps = deletions[:, i]-deletions[:, j]
        square = (gaps-gaps.mean())**2
        shares = square/square.sum()
        order = np.argsort(-shares, kind='stable')
        results[f'{names[i]} vs {names[j]}'] = {
            'full_gap': float(full[i]-full[j]),
            'top_one_ss_share': float(shares[order[0]]),
            'top_five_ss_share': float(shares[order[:5]].sum()),
            'top_groups': [{'speaker_label': str(groups[k]), 'ss_share': float(shares[k]),
                            'deletion_gap': float(gaps[k])} for k in order[:5]],
        }
    output = {'status': 'FIX5 tie-order repair; exploratory speaker-deletion influence',
              'tie_order': 'ascending score, then ascending trial ID',
              'group_count': len(groups), 'inputs_sha256': expected,
              'driver_sha256': sha(Path(__file__)), 'numpy_version': np.__version__,
              'pairs': results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
