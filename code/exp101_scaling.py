"""EXP-101: speaker scaling (measured, not assumed) + i.i.d. baselines over all 28 pairs.

Three things the review asked for that the existing artifacts cannot answer:

1. SPEAKER SCALING. The floor argument says attack conditions cannot shrink the
   speaker component. The obvious next question is how many speakers would. That
   needs V_spk(S), and assuming V_spk proportional to 1/S would be exactly the kind
   of unverified extrapolation this paper withdrew a power law over. So we measure
   it the same way we measured the attack curve: subsample speakers and record the
   clustered width. Bona fide and spoof trials of a dropped speaker both go.

2. I.I.D. WIDTH RATIO OVER ALL 28 PAIRS. The released 3.7-11.2x range was computed
   over the seven adjacency-selected pairs -- the selection this paper criticises.
   Recomputed here over the full family.

3. I.I.D. RESOLVED COUNT over all 28 pairs, so the fixed-set concession in the paper
   cites a computed number instead of a hand-assembly across two artifacts.

Writes results_scaling.json. Modifies nothing.
"""

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, KEY, plain_eer, weighted_eer

B = 1000
REPS = 8
S_GRID = [12, 25, 50, 93]
SEED = 20260819
Z95 = 1.959963984540054
SSL_ERA = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
BASELINE = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]
PAIRS_S = [("XLSR-Conformer", "SSL-AASIST"), ("XLS-R+SLS", "XLSR-Conformer"),
           ("RawNet2", "LFCC-LCNN")]


def clustered_width(rng, s1, s2, labels, spk_idx, att_idx, b=B):
    n, n_spk = len(labels), spk_idx.max() + 1
    is_spoof = labels == 0
    spoof_atts = np.unique(att_idx[is_spoof])
    n_att = att_idx.max() + 1
    o1, o2 = np.argsort(s1), np.argsort(s2)
    d = np.empty(b)
    for i in range(b):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        w = cs[spk_idx].astype(np.float64)
        drawn = rng.choice(spoof_atts, size=len(spoof_atts), replace=True)
        ca = np.bincount(drawn, minlength=n_att)
        w[is_spoof] *= ca[att_idx[is_spoof]]
        d[i] = 100 * (weighted_eer(o1, labels, w) - weighted_eer(o2, labels, w))
    d = d[np.isfinite(d)]
    return float(np.percentile(d, 97.5) - np.percentile(d, 2.5))


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
    n, n_spk = len(labels), spk_idx.max() + 1
    names = SSL_ERA + BASELINE
    scores = {}
    for m in names:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        scores[m] = np.array([float(d[u]) for u in utts])
    results = {"B": B, "reps": REPS, "seed": SEED, "n_speakers_full": int(n_spk),
               "speaker_scaling": {}, "iid_over_all_pairs": {}}

    # --- 1. speaker sweep -------------------------------------------------
    all_spk = np.arange(n_spk)
    for a, b_ in PAIRS_S:
        key = f"{a} vs {b_}"
        results["speaker_scaling"][key] = {}
        for S in S_GRID:
            rng = np.random.default_rng(SEED + S)
            reps = 1 if S >= n_spk else REPS
            ws = []
            for _ in range(reps):
                keep = all_spk if S >= n_spk else rng.choice(all_spk, S, replace=False)
                sub = np.where(np.isin(spk_idx, keep))[0]
                si = np.unique(spk_idx[sub], return_inverse=True)[1]
                ai = np.unique(att_idx[sub], return_inverse=True)[1]
                ws.append(clustered_width(rng, scores[a][sub], scores[b_][sub],
                                          labels[sub], si, ai))
            results["speaker_scaling"][key][S] = {
                "mean_width_pts": round(float(np.mean(ws)), 3),
                "width_sd": round(float(np.std(ws)), 3) if reps > 1 else None,
                "n_reps": reps, "n_trials": int(len(sub))}
            print(f"[{key}] S={S:3d} width {np.mean(ws):6.3f} "
                  f"({len(sub)} trials) [{time.time()-t0:.0f}s]", flush=True)
        w = np.array([results["speaker_scaling"][key][S]["mean_width_pts"] for S in S_GRID])
        gamma = float(-np.polyfit(np.log(S_GRID), np.log(w), 1)[0])
        results["speaker_scaling"][key]["fitted_exponent"] = round(gamma, 3)
        print(f"[{key}] width ~ S^-{gamma:.2f} (S^-1/2 would be 0.50)", flush=True)

    # --- 2/3. i.i.d. bootstrap over all 28 pairs ---------------------------
    rng = np.random.default_rng(SEED)
    orders = {m: np.argsort(scores[m]) for m in names}
    boot = np.empty((B, len(names)))
    for i in range(B):
        w = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64)
        for k, m in enumerate(names):
            boot[i, k] = 100 * weighted_eer(orders[m], labels, w)
    derived = Path(__file__).parent.parent / "derived"
    sel_path = derived / "results_selection.json"
    sel = json.load(open(sel_path))["21df"]["pairs"]
    ratios, n_iid_res = [], 0
    for i, a in enumerate(names):
        for b_ in names[i + 1:]:
            d = boot[:, names.index(a)] - boot[:, names.index(b_)]
            lo, hi = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
            res = bool(not (lo <= 0 <= hi))
            n_iid_res += res
            hit = sel.get(f"{a} vs {b_}") or sel.get(f"{b_} vs {a}")
            cw = hit["ci_pointwise"][1] - hit["ci_pointwise"][0]
            ratios.append(cw / (hi - lo))
            results["iid_over_all_pairs"][f"{a} vs {b_}"] = {
                "ci_iid": [round(lo, 3), round(hi, 3)],
                "resolved_iid": res,
                "width_ratio_clustered_over_iid": round(cw / (hi - lo), 2)}
    results["summary"] = {
        "n_pairs": len(ratios),
        "n_resolved_iid": int(n_iid_res),
        "width_ratio_all_28": [round(min(ratios), 1), round(max(ratios), 1)],
        "width_ratio_median": round(float(np.median(ratios)), 1),
    }
    results["_input_provenance_sha256"] = {
        "results_selection.json": hashlib.sha256(sel_path.read_bytes()).hexdigest()[:16]}
    print("\nsummary:", json.dumps(results["summary"]), flush=True)
    out = derived / "results_scaling.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out} in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
