"""EXP-101: coverage certification on the REAL speaker x attack incidence.

The released certification (EXP-009) generated a fully crossed, balanced design
(every speaker x every attack, NC trials per cell). The real 21DF eval set is
sparse and unbalanced, and a balanced design certifies the estimator for our
generative model rather than for the actual sampling design. Here the cluster
effects and residuals are still drawn from the fitted random-effects model, but
they are placed on the *real* trial index arrays, so the incidence pattern,
per-cell counts and class balance are exactly those of ASVspoof 2021 DF.

Calibrated to the organizer-era pair (RawNet2 vs LFCC-LCNN), the regime in
which the DGP reproduces real interval widths. The low-EER calibration is not
certified here: the correctness audit showed that fit is mis-specified
(population EER 0.274% for systems at 1.88%), and no claim in the paper now
rests on it.

Variants: i.i.d. percentile, two-way clustered percentile, two-way jackknife
(certified set), plus wild-cluster reported as tested. The pigeonhole variant
is withdrawn (it is not the Owen correction).
"""

import json
import time
from math import sqrt
from pathlib import Path

import numpy as np

import power_curves as pc
from m1_contingency import wild_ci

R = int(__import__("os").environ.get("R_REPS", 200))
SEED = 20260818
TARGET_DELTA = 0.5


def gen_on_real_index(rng, cal, shift, labels, spk_idx, att_idx):
    """Scores from the fitted model, placed on the real trial incidence."""
    b, s = cal["bona"], cal["spoof"]
    n_spk = spk_idx.max() + 1
    n_att = att_idx.max() + 1
    bona = labels == 1
    ub1, ub2 = pc.bivariate(rng, b["sd_grp0"], b["sd_grp1"], b["rho_grp"], (n_spk,))
    us1, us2 = pc.bivariate(rng, s["sd_spk0"], s["sd_spk1"], s["rho_spk"], (n_spk,))
    va1, va2 = pc.bivariate(rng, s["sd_att0"], s["sd_att1"], s["rho_att"], (n_att,))
    eb1, eb2 = pc.bivariate(rng, b["sd_res0"], b["sd_res1"], b["rho_res"], (int(bona.sum()),))
    es1, es2 = pc.bivariate(rng, s["sd_res0"], s["sd_res1"], s["rho_res"], (int((~bona).sum()),))
    s1 = np.empty(len(labels))
    s2 = np.empty(len(labels))
    s1[bona] = b["mu0"] + ub1[spk_idx[bona]] + eb1
    s2[bona] = b["mu1"] + ub2[spk_idx[bona]] + eb2
    s1[~bona] = s["mu0"] + us1[spk_idx[~bona]] + va1[att_idx[~bona]] + es1
    s2[~bona] = s["mu1"] + shift + us2[spk_idx[~bona]] + va2[att_idx[~bona]] + es2
    return s1, s2


def mc_population_delta(rng, cal, shift, n=2_000_000):
    """Population Delta-EER under the fitted DGP, fresh clusters for every trial."""
    b, s = cal["bona"], cal["spoof"]
    nb = n // 4
    ub1, ub2 = pc.bivariate(rng, b["sd_grp0"], b["sd_grp1"], b["rho_grp"], (nb,))
    eb1, eb2 = pc.bivariate(rng, b["sd_res0"], b["sd_res1"], b["rho_res"], (nb,))
    us1, us2 = pc.bivariate(rng, s["sd_spk0"], s["sd_spk1"], s["rho_spk"], (n,))
    va1, va2 = pc.bivariate(rng, s["sd_att0"], s["sd_att1"], s["rho_att"], (n,))
    es1, es2 = pc.bivariate(rng, s["sd_res0"], s["sd_res1"], s["rho_res"], (n,))
    labels = np.concatenate([np.ones(nb, int), np.zeros(n, int)])
    ones = np.ones(len(labels))
    out = []
    for k, (ub, eb, us, va, es) in enumerate(((ub1, eb1, us1, va1, es1),
                                              (ub2, eb2, us2, va2, es2))):
        sc = np.concatenate([b[f"mu{k}"] + ub + eb,
                             s[f"mu{k}"] + (shift if k == 1 else 0.0) + us + va + es])
        out.append(pc.weighted_eer(np.argsort(sc), labels, ones))
    return 100 * (out[0] - out[1])


def cis_all(rng, s1, s2, labels, spk_idx, att_idx):
    n, n_spk, n_att = len(s1), spk_idx.max() + 1, att_idx.max() + 1
    is_spoof = labels == 0
    # Resample the 110 real attack levels, not the 111 index levels: the extra
    # level is the placeholder carried by bona fide trials and belongs to no
    # attack. (Matches m1_campaign/exp101_selection/exp101_widths.)
    spoof_atts = np.unique(att_idx[is_spoof])
    o1, o2 = np.argsort(s1), np.argsort(s2)

    def delta(w):
        return 100 * (pc.weighted_eer(o1, labels, w) - pc.weighted_eer(o2, labels, w))

    d_hat = delta(np.ones(n))
    ds_two, ds_nv = np.empty(pc.B), np.empty(pc.B)
    for i in range(pc.B):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        w = cs[spk_idx].astype(np.float64)
        drawn = rng.choice(spoof_atts, size=len(spoof_atts), replace=True)
        ca = np.bincount(drawn, minlength=n_att)
        w[is_spoof] *= ca[att_idx[is_spoof]]
        ds_two[i] = delta(w)
        wn = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64)
        ds_nv[i] = delta(wn)
    v_naive = float(np.var(ds_nv))
    jack_spk = np.empty(n_spk)
    for k in range(n_spk):
        w = np.ones(n)
        w[spk_idx == k] = 0.0
        jack_spk[k] = delta(w)
    jack_att = np.empty(len(spoof_atts))
    for j, k in enumerate(spoof_atts):
        w = np.ones(n)
        w[is_spoof & (att_idx == k)] = 0.0
        jack_att[j] = delta(w)
    v_spk = (n_spk - 1) / n_spk * float(np.sum((jack_spk - jack_spk.mean()) ** 2))
    na = len(spoof_atts)
    v_att = (na - 1) / na * float(np.sum((jack_att - jack_att.mean()) ** 2))
    v_jack = max(v_spk + v_att - v_naive, max(v_spk, v_att))
    return {
        "iid": [float(np.percentile(ds_nv, 2.5)), float(np.percentile(ds_nv, 97.5))],
        "twoway": [float(np.percentile(ds_two, 2.5)), float(np.percentile(ds_two, 97.5))],
        "jackknife": [d_hat - pc.Z95 * sqrt(v_jack), d_hat + pc.Z95 * sqrt(v_jack)],
        "wild": wild_ci(rng, d_hat, jack_spk, jack_att, v_naive),
    }


def main():
    t0 = time.time()
    utt2meta = {}
    for line in pc.KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk_idx = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    att_idx = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    spoof = labels == 0
    cells = len(np.unique(spk_idx[spoof] * 1000 + att_idx[spoof]))
    print(f"real incidence: {len(labels)} trials, {labels.sum()} bona, "
          f"{spk_idx.max()+1} spk, {att_idx.max()+1} att, {cells} occupied spk-att cells "
          f"of {(spk_idx.max()+1)*(att_idx.max()+1)} possible", flush=True)

    cal, _ = pc.calibrate(pc.PAIRS["high_icc_organizer"])
    shift, true_d = pc.solve_shift(cal, TARGET_DELTA)
    # Guard against the silent-fallback bug the audit found (a row labelled
    # Delta=0.5 that actually ran Delta=-0.5): verify the achieved population
    # delta by Monte Carlo under the same DGP before using it as truth.
    # Population-level MC: every trial gets *fresh* cluster effects, so this
    # estimates the same superpopulation quantity as the analytic marginals
    # (a few finite-cluster replicates would be far too noisy to check against).
    rng = np.random.default_rng(SEED)
    mc_delta = mc_population_delta(rng, cal, shift)
    print(f"target Delta={TARGET_DELTA}; analytic true Delta={true_d:.4f}; "
          f"population-MC check={mc_delta:.4f}", flush=True)
    assert abs(mc_delta - true_d) < 0.05, "population MC disagrees with the analytic truth"
    assert abs(true_d - TARGET_DELTA) < 0.05, f"solve_shift returned {true_d}, not {TARGET_DELTA}"
    assert np.sign(mc_delta) == np.sign(true_d), "MC and analytic truth disagree in sign"

    cov = {v: 0 for v in ("iid", "twoway", "jackknife", "wild")}
    widths = {v: [] for v in cov}
    for r in range(R):
        s1, s2 = gen_on_real_index(rng, cal, shift, labels, spk_idx, att_idx)
        cis = cis_all(rng, s1, s2, labels, spk_idx, att_idx)
        for v, (lo, hi) in cis.items():
            cov[v] += int(lo <= true_d <= hi)
            widths[v].append(hi - lo)
        if r in (0, 4, 24, 49, 99, 199):
            done = r + 1
            print(f"  {done}/{R} replicates, {(time.time()-t0)/60:.1f} min, "
                  + " ".join(f"{v}={cov[v]/done:.3f}" for v in cov), flush=True)

    results = {
        "design": "real 21DF incidence (unbalanced, sparse), organizer-era calibration",
        "calibration_pair": "RawNet2 vs LFCC-LCNN", "R": R, "B": pc.B, "seed": SEED,
        "true_delta_pts": round(float(true_d), 4),
        "n_trials": int(len(labels)), "n_spk": int(spk_idx.max() + 1),
        "n_att": int(att_idx.max() + 1), "occupied_cells": int(cells),
        **{v: {"coverage": round(cov[v] / R, 4),
               "mean_width": round(float(np.mean(widths[v])), 3)} for v in cov},
    }
    print(json.dumps({k: v for k, v in results.items() if k in cov or k == "true_delta_pts"},
                     indent=1), flush=True)
    out = Path(__file__).parent.parent / "derived" / "results_coverage_real.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out} in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
