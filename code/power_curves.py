"""EXP-101 cells 5-6: DGP-robustness + cluster-count power curves.

Cell 6: P(two-way clustered 95% percentile CI excludes 0) vs cluster counts
A in {5,10,20,40,80,110} x S in {12,25,50,93}, true delta in {0.2,0.5,1.0} pts,
via the EXP-009 calibrated simulator. ICC-conditioned bands: the sweep runs at
two calibrations spanning the observed ICC range — high-ICC organizer pair
(RawNet2 vs LFCC-LCNN) and low-EER SOTA pair (XLSR-Mamba vs XLS-R+SLS).
No claims beyond observed cluster counts (max A=110, S=93).

Cell 5: DGP-robustness — coverage at Delta=0.5, 21DF-like counts, replicates
built by resampling REAL per-cluster residual pools (semi-synthetic) instead of
Gaussian draws; cluster effects still redrawn per replicate (generalization
estimand). PASS mirror of EXP-009: certified-trio coverage in [90, 99].
"""

import json
import time
from math import erf, sqrt
import os
from pathlib import Path

import numpy as np

DATA = Path(os.environ.get("M1_DATA_ROOT",
                           Path.home() / "data/corpora/anti-spoofing"))
KEY = DATA / "DF-keys-full/keys/DF/CM/trial_metadata.txt"
OFF = DATA / "official-scores"
PAIRS = {
    "high_icc_organizer": {
        "sys1": DATA / "DF-keys-full/keys/DF/CM/RawNet2/score.txt",
        "sys2": DATA / "DF-keys-full/keys/DF/CM/LFCC-LCNN/score.txt",
    },
    "low_eer_sota": {
        "sys1": OFF / "xlsr-mamba/Bmamba3_LA_WCE_1e-06_ES144_NE12.txt",
        "sys2": OFF / "xlsr-sls/scores_DF.txt",
    },
}
A_GRID = [5, 10, 20, 40, 80, 110]
S_GRID = [12, 25, 50, 93]
DELTAS = [0.0, 0.2, 0.5, 1.0]  # 0.0 = size row: exclusion rate is type-I error, not power
R_POWER = 200
R_ROBUST = 400
B = 300
SEED = 20260815
Z95 = 1.959963984540054


def norm_cdf(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def gauss_eer(mu_b, sd_b, mu_s, sd_s):
    lo = min(mu_s - 10 * sd_s, mu_b - 10 * sd_b)
    hi = max(mu_b + 10 * sd_b, mu_s + 10 * sd_s)
    for _ in range(200):
        t = (lo + hi) / 2
        if norm_cdf((t - mu_b) / sd_b) < 1.0 - norm_cdf((t - mu_s) / sd_s):
            lo = t
        else:
            hi = t
    return norm_cdf((t - mu_b) / sd_b)


def weighted_eer(sort_idx, labels, weights):
    l = labels[sort_idx]
    w = weights[sort_idx].astype(np.float64)
    cb = np.cumsum(w * l)
    cs = np.cumsum(w * (1 - l))
    frr = cb / cb[-1]
    far = 1.0 - cs / cs[-1]
    i = np.argmin(np.abs(frr - far))
    return float((frr[i] + far[i]) / 2)


def oneway(s1, s2, grp):
    ng = grp.max() + 1
    cnt = np.bincount(grp, minlength=ng)
    out, effs = {}, []
    for k, s in enumerate((s1, s2)):
        mu = s.mean()
        eff = np.bincount(grp, weights=s - mu, minlength=ng) / cnt
        res = s - mu - eff[grp]
        out[f"mu{k}"], out[f"sd_grp{k}"], out[f"sd_res{k}"] = mu, float(eff.std()), float(res.std())
        effs.append((eff, res))
    out["rho_grp"] = float(np.corrcoef(effs[0][0], effs[1][0])[0, 1])
    out["rho_res"] = float(np.corrcoef(effs[0][1], effs[1][1])[0, 1])
    return out, effs


def twoway(s1, s2, spk, att, iters=5):
    nspk, natt = spk.max() + 1, att.max() + 1
    cs, ca = np.bincount(spk, minlength=nspk), np.bincount(att, minlength=natt)
    out, effs = {}, []
    for k, s in enumerate((s1, s2)):
        mu = s.mean()
        r = s - mu
        spk_eff, att_eff = np.zeros(nspk), np.zeros(natt)
        for _ in range(iters):
            att_eff = np.bincount(att, weights=r - spk_eff[spk], minlength=natt) / ca
            att_eff -= att_eff.mean()
            spk_eff = np.bincount(spk, weights=r - att_eff[att], minlength=nspk) / cs
            spk_eff -= spk_eff.mean()
        res = r - spk_eff[spk] - att_eff[att]
        out[f"mu{k}"], out[f"sd_spk{k}"], out[f"sd_att{k}"], out[f"sd_res{k}"] = \
            mu, float(spk_eff.std()), float(att_eff.std()), float(res.std())
        effs.append((spk_eff, att_eff, res))
    out["rho_spk"] = float(np.corrcoef(effs[0][0], effs[1][0])[0, 1])
    out["rho_att"] = float(np.corrcoef(effs[0][1], effs[1][1])[0, 1])
    out["rho_res"] = float(np.corrcoef(effs[0][2], effs[1][2])[0, 1])
    return out, effs


def bivariate(rng, sd1, sd2, rho, shape):
    z = rng.standard_normal(shape + (2,))
    return sd1 * z[..., 0], sd2 * (rho * z[..., 0] + sqrt(max(1 - rho**2, 0)) * z[..., 1])


def marginals(cal, shift):
    b, s = cal["bona"], cal["spoof"]
    return ((b["mu0"], sqrt(b["sd_grp0"]**2 + b["sd_res0"]**2),
             s["mu0"], sqrt(s["sd_spk0"]**2 + s["sd_att0"]**2 + s["sd_res0"]**2)),
            (b["mu1"], sqrt(b["sd_grp1"]**2 + b["sd_res1"]**2),
             s["mu1"] + shift, sqrt(s["sd_spk1"]**2 + s["sd_att1"]**2 + s["sd_res1"]**2)))


def solve_shift(cal, target_pts):
    """Shift system-2 spoof mean to |EER1 - EER2| = target_pts; direction picked
    so the target EER2 stays in (0, 0.5) — power is symmetric in the sign."""
    eer1 = gauss_eer(*marginals(cal, 0.0)[0])
    target = eer1 - target_pts / 100.0
    if target <= 0.0005:
        target = eer1 + target_pts / 100.0
    assert 0.0005 < target < 0.5, f"target EER2 {target} out of range"
    sd = marginals(cal, 0.0)[1][3]
    lo, hi = -20 * sd, 20 * sd
    for _ in range(100):
        mid = (lo + hi) / 2
        if gauss_eer(*marginals(cal, mid)[1]) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, 100 * (eer1 - gauss_eer(*marginals(cal, (lo + hi) / 2)[1]))


def gen(rng, cal, S, A, shift, NB=30, NC=3, res_pools=None):
    """One replicate; res_pools=(bona_res_2col, spoof_res_2col) => semi-synthetic."""
    b, s = cal["bona"], cal["spoof"]
    ub1, ub2 = bivariate(rng, b["sd_grp0"], b["sd_grp1"], b["rho_grp"], (S,))
    us1, us2 = bivariate(rng, s["sd_spk0"], s["sd_spk1"], s["rho_spk"], (S,))
    va1, va2 = bivariate(rng, s["sd_att0"], s["sd_att1"], s["rho_att"], (A,))
    spk_b = np.repeat(np.arange(S), NB)
    spk_s = np.repeat(np.arange(S), A * NC)
    att_s = np.tile(np.repeat(np.arange(A), NC), S)
    if res_pools is None:
        eb1, eb2 = bivariate(rng, b["sd_res0"], b["sd_res1"], b["rho_res"], (S * NB,))
        es1, es2 = bivariate(rng, s["sd_res0"], s["sd_res1"], s["rho_res"], (S * A * NC,))
    else:
        rb = res_pools[0][rng.integers(0, len(res_pools[0]), S * NB)]
        rs = res_pools[1][rng.integers(0, len(res_pools[1]), S * A * NC)]
        eb1, eb2 = rb[:, 0], rb[:, 1]
        es1, es2 = rs[:, 0], rs[:, 1]
    s1 = np.concatenate([b["mu0"] + ub1[spk_b] + eb1, s["mu0"] + us1[spk_s] + va1[att_s] + es1])
    s2 = np.concatenate([b["mu1"] + ub2[spk_b] + eb2,
                         s["mu1"] + shift + us2[spk_s] + va2[att_s] + es2])
    labels = np.concatenate([np.ones(S * NB, int), np.zeros(S * A * NC, int)])
    spk_idx = np.concatenate([spk_b, spk_s])
    att_idx = np.concatenate([np.full(S * NB, -1), att_s])
    return s1, s2, labels, spk_idx, att_idx


def twoway_ci(rng, s1, s2, labels, spk_idx, att_idx, also_variants=False):
    n, n_spk, n_att = len(s1), spk_idx.max() + 1, att_idx.max() + 1
    is_spoof = labels == 0
    o1, o2 = np.argsort(s1), np.argsort(s2)

    def delta(w):
        return 100 * (weighted_eer(o1, labels, w) - weighted_eer(o2, labels, w))

    ds_two, ds_nv = np.empty(B), np.empty(B)
    for i in range(B):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        w = cs[spk_idx].astype(np.float64)
        ca = np.bincount(rng.integers(0, n_att, n_att), minlength=n_att)
        w[is_spoof] *= ca[att_idx[is_spoof]]
        ds_two[i] = delta(w)
        if also_variants:
            wn = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64)
            ds_nv[i] = delta(wn)
    ci_two = [float(np.percentile(ds_two, 2.5)), float(np.percentile(ds_two, 97.5))]
    if not also_variants:
        return {"twoway": ci_two}
    d_hat = delta(np.ones(n))
    v_pig = max(float(np.var(ds_two)) - float(np.var(ds_nv)), float(np.var(ds_nv)))
    jack_spk = np.empty(n_spk)
    for k in range(n_spk):
        w = np.ones(n)
        w[spk_idx == k] = 0.0
        jack_spk[k] = delta(w)
    v_spk = (n_spk - 1) / n_spk * float(np.sum((jack_spk - jack_spk.mean()) ** 2))
    jack_att = np.empty(n_att)
    for k in range(n_att):
        w = np.ones(n)
        w[is_spoof & (att_idx == k)] = 0.0
        jack_att[k] = delta(w)
    v_att = (n_att - 1) / n_att * float(np.sum((jack_att - jack_att.mean()) ** 2))
    v_jack = max(v_spk + v_att - float(np.var(ds_nv)), max(v_spk, v_att))
    return {"twoway": ci_two,
            "pigeonhole": [d_hat - Z95 * sqrt(v_pig), d_hat + Z95 * sqrt(v_pig)],
            "jackknife": [d_hat - Z95 * sqrt(v_jack), d_hat + Z95 * sqrt(v_jack)]}


def calibrate(paths):
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    bona = np.array([utt2meta[u][2] == "bonafide" for u in utts])
    spk = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    att = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    ss = []
    for path in (paths["sys1"], paths["sys2"]):
        d = dict(l.split()[:2] for l in path.read_text().splitlines())
        ss.append(np.array([float(d[u]) for u in utts]))
    s1, s2 = ss
    cal_b, effs_b = oneway(s1[bona], s2[bona], np.unique(spk[bona], return_inverse=True)[1])
    cal_s, effs_s = twoway(s1[~bona], s2[~bona],
                           np.unique(spk[~bona], return_inverse=True)[1],
                           np.unique(att[~bona], return_inverse=True)[1])
    res_b = np.stack([effs_b[0][1], effs_b[1][1]], 1)
    res_s = np.stack([effs_s[0][2], effs_s[1][2]], 1)
    return {"bona": cal_b, "spoof": cal_s}, (res_b, res_s)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    results = {}

    for tag, paths in PAIRS.items():
        cal, res_pools = calibrate(paths)
        results[tag] = {"calibration": cal, "power": {}}
        for target in DELTAS:
            shift, true_d = solve_shift(cal, target)
            grid = {}
            for S in S_GRID:
                for A in A_GRID:
                    hits = 0
                    for _ in range(R_POWER):
                        s1, s2, labels, spk_idx, att_idx = gen(rng, cal, S, A, shift)
                        lo, hi = twoway_ci(rng, s1, s2, labels, spk_idx, att_idx)["twoway"]
                        hits += int(not (lo <= 0 <= hi))
                    grid[f"S{S}_A{A}"] = round(hits / R_POWER, 3)
            results[tag]["power"][f"delta_{target}"] = {"true_delta": round(true_d, 3), **grid}
            print(f"[{tag}] Δ={target}: " + " ".join(
                f"{k}={v}" for k, v in grid.items() if k.startswith("S93")), flush=True)

    # Cell 5: DGP-robustness (semi-synthetic residuals), organizer pair, Δ=0.5.
    cal, res_pools = calibrate(PAIRS["high_icc_organizer"])
    shift, true_d = solve_shift(cal, 0.5)
    cov = {"twoway": 0, "pigeonhole": 0, "jackknife": 0}
    for _ in range(R_ROBUST):
        s1, s2, labels, spk_idx, att_idx = gen(rng, cal, 93, 110, shift, res_pools=res_pools)
        cis = twoway_ci(rng, s1, s2, labels, spk_idx, att_idx, also_variants=True)
        for v, (lo, hi) in cis.items():
            cov[v] += int(lo <= true_d <= hi)
    results["dgp_robustness"] = {
        "true_delta": round(true_d, 3), "R": R_ROBUST,
        **{v: round(c / R_ROBUST, 4) for v, c in cov.items()},
    }
    print(f"DGP-robustness: {results['dgp_robustness']}", flush=True)

    out = Path(__file__).parent / "results_power.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out} in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
