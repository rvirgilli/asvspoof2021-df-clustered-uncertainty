"""EXP-101: measured CI width vs attack-cluster count, on real scores.

Replaces the withdrawn simulator-derived power prescription. The Gaussian
random-effects DGP was mis-specified in the low-EER regime (correctness audit:
population EER 0.274% when fitted to systems at 1.88%; intervals 2.3-3.1x
narrower than real data), so no prescription is derived from it. Instead we
measure the quantity directly: subsample attack clusters from the real 21DF
eval set and record the clustered CI width of the paired Delta-EER.

Reported per (pair, A): mean width across independent attack subsamples, and
the half-width, which is the benchmark's resolution limit at that cluster count
(a gap smaller than the half-width cannot be resolved). A=110 is the full set
and needs no subsampling. Also reports the simulator's width at matched counts,
so the discrepancy that invalidated the prescription is documented, not hidden.
"""

import json
import time
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, KEY, plain_eer, weighted_eer

B = 1000
REPS = 10
A_GRID = [10, 20, 40, 80, 110]
SEED = 20260817
PAIRS = [
    ("XLSR-Conformer", "SSL-AASIST", "ssl-era"),
    ("XLS-R+SLS", "XLSR-Conformer", "ssl-era"),
    ("RawNet2", "LFCC-LCNN", "organizer-era"),
]


def clustered_ci(rng, s1, s2, labels, spk_idx, att_idx):
    n, n_spk = len(labels), spk_idx.max() + 1
    is_spoof = labels == 0
    spoof_atts = np.unique(att_idx[is_spoof])
    n_att = att_idx.max() + 1
    o1, o2 = np.argsort(s1), np.argsort(s2)
    d = np.empty(B)
    for i in range(B):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        w = cs[spk_idx].astype(np.float64)
        drawn = rng.choice(spoof_atts, size=len(spoof_atts), replace=True)
        ca = np.bincount(drawn, minlength=n_att)
        w[is_spoof] *= ca[att_idx[is_spoof]]
        d[i] = 100 * (weighted_eer(o1, labels, w) - weighted_eer(o2, labels, w))
    d = d[np.isfinite(d)]
    lo, hi = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
    return lo, hi


def main():
    t0 = time.time()
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk_idx = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    att_idx = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    scores = {}
    for m in {n for p in PAIRS for n in p[:2]}:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        scores[m] = np.array([float(d[u]) for u in utts])
    spoof_atts = np.unique(att_idx[labels == 0])

    results = {"B": B, "reps": REPS, "seed": SEED, "n_attacks_full": int(len(spoof_atts)),
               "note": "measured on real 21DF scores; no simulator involved", "pairs": {}}
    for a, b, era in PAIRS:
        key = f"{a} vs {b}"
        delta_full = 100 * (plain_eer(scores[a], labels) - plain_eer(scores[b], labels))
        entry = {"era": era, "delta_full": round(delta_full, 3), "by_A": {}}
        for A in A_GRID:
            rng = np.random.default_rng(SEED + A)
            widths, hws = [], []
            reps = 1 if A >= len(spoof_atts) else REPS
            for _ in range(reps):
                if A >= len(spoof_atts):
                    sub = np.arange(len(labels))
                else:
                    keep = rng.choice(spoof_atts, A, replace=False)
                    sub = np.where((labels == 1) | np.isin(att_idx, keep))[0]
                l = labels[sub]
                si = np.unique(spk_idx[sub], return_inverse=True)[1]
                ai = np.unique(att_idx[sub], return_inverse=True)[1]
                lo, hi = clustered_ci(rng, scores[a][sub], scores[b][sub], l, si, ai)
                widths.append(hi - lo)
                hws.append((hi - lo) / 2)
            entry["by_A"][A] = {
                "n_reps": reps, "n_trials": int(len(sub)),
                "mean_width_pts": round(float(np.mean(widths)), 3),
                "mean_half_width_pts": round(float(np.mean(hws)), 3),
                "width_sd": round(float(np.std(widths)), 3) if reps > 1 else None,
            }
            print(f"[{key}] A={A:3d} width {np.mean(widths):6.3f} "
                  f"(half {np.mean(hws):5.3f}) n={len(sub)} reps={reps} "
                  f"[{time.time()-t0:.0f}s]", flush=True)
        results["pairs"][key] = entry

    # Descriptive scaling exponent on the real curve (no extrapolation claimed).
    for key, entry in results["pairs"].items():
        A = np.array([a for a in A_GRID], float)
        w = np.array([entry["by_A"][a]["mean_width_pts"] for a in A_GRID])
        gamma = float(-np.polyfit(np.log(A), np.log(w), 1)[0])
        entry["width_scaling_exponent"] = round(gamma, 3)
        print(f"[{key}] width ~ A^-{gamma:.2f} over the observed range", flush=True)

    out = Path(__file__).parent / "results_widths.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out} in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
