"""EXP-101: sampling uncertainty of the finite-A speaker component.

The width 2*z_.975*sqrt(V_spk) is a point estimate: V_spk is computed from the 93
speakers we happen to have at the observed A=110 attacks. Because this component
also contains speaker-by-attack interaction divided by A, it is not an estimate
of an A-to-infinity floor. The paper's descriptive count -- eight of the ten
unresolved pairs have gaps below half this finite-A component -- has boundary
sensitivity, and two pairs sit within ~8% of the threshold. This script measures
that sampling sensitivity without making an attack-budget extrapolation.

Method: the delete-one-speaker jackknife gives 93 per-speaker deviations of the
paired Delta-EER. Each bootstrap replicate draws one shared sample of 93 speakers,
which is then applied to every pair. Recomputing V_spk gives the sampling
distribution of each component width while the shared draw preserves the cross-pair
covariance needed for the joint count. The gap is held at its point estimate (its
own interval is reported separately in the paper).

Reports per pair: component-width CI and P(gap < half-component). Reports overall:
the distribution of this descriptive count across shared-speaker resamples. No
quantity reported here identifies what happens under a counterfactual attack set.

Writes results_floor_ci.json. Modifies nothing.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, KEY, weighted_eer

B = 4000
SEED = 20260820
Z95 = 1.959963984540054
SSL_ERA = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
BASELINE = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]


def main():
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk_idx = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    n, n_spk = len(labels), spk_idx.max() + 1

    names = SSL_ERA + BASELINE
    orders = {}
    for m in names:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        orders[m] = np.argsort(np.array([float(d[u]) for u in utts]))

    def eers(w):
        return np.array([100 * weighted_eer(orders[m], labels, w) for m in names])

    print(f"delete-one-speaker jackknife over {n_spk} speakers", flush=True)
    jack = np.empty((n_spk, len(names)))
    for k in range(n_spk):
        w = np.ones(n)
        w[spk_idx == k] = 0.0
        jack[k] = eers(w)
    point = eers(np.ones(n))

    rng = np.random.default_rng(SEED)
    derived = Path(__file__).parent.parent / "derived"
    fl_path = derived / "results_floor.json"
    fl = json.load(open(fl_path))["pairs"]
    results = {
        "B_bootstrap": B, "seed": SEED, "n_speakers": int(n_spk),
        "method": "resample the 93 delete-one-speaker deviations with replacement; "
                  "recompute the finite-A component width = 2*z*sqrt(V_spk); "
                  "gap held at its point estimate; no A-to-infinity interpretation",
        "_input_provenance_sha256": {
            "results_floor.json": hashlib.sha256(fl_path.read_bytes()).hexdigest()[:16]},
        "pairs": {},
    }
    unresolved_keys = [k for k, v in fl.items() if not v["resolved_simultaneous"]]
    never_counts = np.zeros(B, int)
    # A count replicate must describe one possible speaker sample for the entire
    # leaderboard. Drawing independently inside the pair loop would add indicators
    # from incompatible samples and destroy their covariance.
    shared_idx = rng.integers(0, n_spk, (B, n_spk))

    for key, v in fl.items():
        a, b = key.split(" vs ")
        ia, ib = names.index(a), names.index(b)
        d = jack[:, ia] - jack[:, ib]
        e = d - d.mean()
        boot = e[shared_idx]
        v_spk = (n_spk - 1) / n_spk * np.sum((boot - boot.mean(axis=1, keepdims=True)) ** 2, axis=1)
        component = 2 * Z95 * np.sqrt(v_spk)
        gap = abs(float(point[ia] - point[ib]))
        below = gap < component / 2
        results["pairs"][key] = {
            "block": v["block"],
            "gap": round(gap, 3),
            "finite_A_component_point": v["finite_A_speaker_component_width_pts"],
            "finite_A_component_ci95": [
                round(float(np.percentile(component, 2.5)), 3),
                round(float(np.percentile(component, 97.5)), 3)],
            "half_finite_A_component_point": round(
                v["finite_A_speaker_component_width_pts"] / 2, 3),
            "p_gap_below_half_finite_A_component": round(float(below.mean()), 3),
            "resolved_simultaneous": v["resolved_simultaneous"],
        }
        if key in unresolved_keys:
            never_counts += below
        r = results["pairs"][key]
        print(f"  {key:<34} gap={gap:6.3f} "
              f"component={v['finite_A_speaker_component_width_pts']:6.3f} "
              f"CI={r['finite_A_component_ci95']}  "
              f"P(gap < half component)={r['p_gap_below_half_finite_A_component']:.3f}",
              flush=True)

    counts = np.bincount(never_counts, minlength=len(unresolved_keys) + 1)
    results["summary"] = {
        "n_unresolved_pairs": len(unresolved_keys),
        "point_estimate_count_below_half_finite_A_component": int(
            sum(results["pairs"][k]["gap"] <
                results["pairs"][k]["half_finite_A_component_point"]
                for k in unresolved_keys)),
        "bootstrap_count_median": int(np.median(never_counts)),
        "bootstrap_count_ci95": [int(np.percentile(never_counts, 2.5)),
                                 int(np.percentile(never_counts, 97.5))],
        "p_at_least_8_of_10": round(float((never_counts >= 8).mean()), 3),
        "p_at_least_6_of_10": round(float((never_counts >= 6).mean()), 3),
        "p_at_least_5_of_10": round(float((never_counts >= 5).mean()), 3),
        "count_distribution": {int(i): int(c) for i, c in enumerate(counts) if c},
    }
    print("\nsummary:", json.dumps(results["summary"], indent=1), flush=True)
    out = derived / "results_floor_ci.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
