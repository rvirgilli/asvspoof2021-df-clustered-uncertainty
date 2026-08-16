"""EXP-101 spec-gate contingencies C1-C3 (PREREG addendum 2026-08-14).

C1: coverage replicate calibrated to the low-EER SOTA pair (XLSR-Mamba vs
    XLS-R+SLS) at true Δ=0.2 pts, S=93, A=110, R=400 — certified trio + C3.
C3: wild-cluster-style variant — two-way wild bootstrap on jackknife influence
    deviations (Rademacher weights per speaker and per attack), total variance
    shrunk to the inclusion-exclusion V_spk + V_att − V_naive; percentile CI.
C2: attack-family (vocoder type, metadata col 9) and codec (col 3) ICC
    diagnostic on 21DF for all pool systems.
"""

import json
from math import sqrt
from pathlib import Path

import numpy as np

import power_curves as pc

R = 400
B_WILD = 399
SEED = 20260816


def wild_ci(rng, d_hat, jack_spk_d, jack_att_d, v_naive):
    """C3 variant. jack_*_d = per-deleted-cluster delta arrays (pts)."""
    e_s = (jack_spk_d - jack_spk_d.mean()) * sqrt((len(jack_spk_d) - 1) / len(jack_spk_d))
    e_a = (jack_att_d - jack_att_d.mean()) * sqrt((len(jack_att_d) - 1) / len(jack_att_d))
    v_spk, v_att = float(np.sum(e_s**2)), float(np.sum(e_a**2))
    shrink = sqrt(max(v_spk + v_att - v_naive, 0.25 * (v_spk + v_att)) / (v_spk + v_att))
    draws = d_hat + shrink * (
        rng.choice([-1.0, 1.0], (B_WILD, len(e_s))) @ e_s
        + rng.choice([-1.0, 1.0], (B_WILD, len(e_a))) @ e_a)
    return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]


def cis_with_wild(rng, s1, s2, labels, spk_idx, att_idx):
    n, n_spk, n_att = len(s1), spk_idx.max() + 1, att_idx.max() + 1
    is_spoof = labels == 0
    o1, o2 = np.argsort(s1), np.argsort(s2)

    def delta(w):
        return 100 * (pc.weighted_eer(o1, labels, w) - pc.weighted_eer(o2, labels, w))

    d_hat = delta(np.ones(n))
    ds_two, ds_nv = np.empty(pc.B), np.empty(pc.B)
    for i in range(pc.B):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        w = cs[spk_idx].astype(np.float64)
        ca = np.bincount(rng.integers(0, n_att, n_att), minlength=n_att)
        w[is_spoof] *= ca[att_idx[is_spoof]]
        ds_two[i] = delta(w)
        wn = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64)
        ds_nv[i] = delta(wn)
    v_naive, v_two = float(np.var(ds_nv)), float(np.var(ds_two))
    jack_spk = np.empty(n_spk)
    for k in range(n_spk):
        w = np.ones(n)
        w[spk_idx == k] = 0.0
        jack_spk[k] = delta(w)
    jack_att = np.empty(n_att)
    for k in range(n_att):
        w = np.ones(n)
        w[is_spoof & (att_idx == k)] = 0.0
        jack_att[k] = delta(w)
    v_spk = (n_spk - 1) / n_spk * float(np.sum((jack_spk - jack_spk.mean()) ** 2))
    v_att = (n_att - 1) / n_att * float(np.sum((jack_att - jack_att.mean()) ** 2))
    v_pig = max(v_two - v_naive, v_naive)
    v_jack = max(v_spk + v_att - v_naive, max(v_spk, v_att))
    return {
        "twoway": [float(np.percentile(ds_two, 2.5)), float(np.percentile(ds_two, 97.5))],
        "pigeonhole": [d_hat - pc.Z95 * sqrt(v_pig), d_hat + pc.Z95 * sqrt(v_pig)],
        "jackknife": [d_hat - pc.Z95 * sqrt(v_jack), d_hat + pc.Z95 * sqrt(v_jack)],
        "wild": wild_ci(rng, d_hat, jack_spk, jack_att, v_naive),
    }


def c2_grouped_icc():
    """Spoof-only, size-weighted between-group variance share per grouping."""
    utt2meta = {}
    for line in pc.KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval" and p[5] == "spoof":
            utt2meta[p[1]] = (p[2], p[8])  # codec, vocoder family
    from m1_campaign import DF_SCORES
    utts = sorted(utt2meta)
    codec = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)
    fam = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)
    out = {"codec_levels": codec[0].tolist(), "family_levels": fam[0].tolist(), "systems": {}}
    for m, path in DF_SCORES.items():
        d = dict(l.split()[:2] for l in path.read_text().splitlines())
        s = np.array([float(d[u]) for u in utts])
        tot = float(s.var())
        entry = {}
        for name, idx in (("codec", codec[1]), ("family", fam[1])):
            cnt = np.bincount(idx)
            means = np.bincount(idx, weights=s) / cnt
            between = float(np.sum(cnt * (means - s.mean()) ** 2) / len(s))
            entry[f"icc_{name}"] = round(between / tot, 3)
        out["systems"][m] = entry
    return out


def mc_true_delta(rng, cal, shift, pools, n=2_000_000):
    """Population ΔEER under the semi-synthetic DGP (real residual pools):
    the Gaussian-analytic truth is biased there, so integrate by Monte Carlo
    with fresh cluster effects per sample and residuals drawn from the pools."""
    b, s = cal["bona"], cal["spoof"]
    nb = n // 4
    ub1, ub2 = pc.bivariate(rng, b["sd_grp0"], b["sd_grp1"], b["rho_grp"], (nb,))
    us1, us2 = pc.bivariate(rng, s["sd_spk0"], s["sd_spk1"], s["rho_spk"], (n,))
    va1, va2 = pc.bivariate(rng, s["sd_att0"], s["sd_att1"], s["rho_att"], (n,))
    rb = pools[0][rng.integers(0, len(pools[0]), nb)]
    rs = pools[1][rng.integers(0, len(pools[1]), n)]
    deltas = []
    for k, (ub, us, va) in enumerate(((ub1, us1, va1), (ub2, us2, va2))):
        bona = b[f"mu{k}"] + ub + rb[:, k]
        spoof = s[f"mu{k}"] + (shift if k == 1 else 0.0) + us + va + rs[:, k]
        scores = np.concatenate([bona, spoof])
        labels = np.concatenate([np.ones(nb, int), np.zeros(n, int)])
        deltas.append(pc.weighted_eer(np.argsort(scores), labels, np.ones(len(scores))))
    return 100 * (deltas[0] - deltas[1])


def coverage_run(rng, tag, pair, delta, R_run, NB, NC, semisynthetic):
    cal, res_pools = pc.calibrate(pc.PAIRS[pair])
    shift, true_d = pc.solve_shift(cal, delta)
    pools = res_pools if semisynthetic else None
    if semisynthetic:
        true_d = mc_true_delta(rng, cal, shift, res_pools)
        print(f"{tag}: MC truth under semi-synthetic DGP = {true_d:.4f} "
              f"(Gaussian-analytic was {delta})", flush=True)
    cov = {v: 0 for v in ("twoway", "pigeonhole", "jackknife", "wild")}
    widths = {v: [] for v in cov}
    for r in range(R_run):
        s1, s2, labels, spk_idx, att_idx = pc.gen(rng, cal, 93, 110, shift,
                                                  NB=NB, NC=NC, res_pools=pools)
        cis = cis_with_wild(rng, s1, s2, labels, spk_idx, att_idx)
        for v, (lo, hi) in cis.items():
            cov[v] += int(lo <= true_d <= hi)
            widths[v].append(hi - lo)
    entry = {"pair": pair, "true_delta_pts": round(true_d, 4), "R": R_run,
             "NB": NB, "NC": NC, "semisynthetic": semisynthetic,
             **{v: {"coverage": round(c / R_run, 4),
                    "mean_width": round(float(np.mean(widths[v])), 3)}
                for v, c in cov.items()}}
    print(tag, entry, flush=True)
    return entry


def main():
    rng = np.random.default_rng(SEED)
    results = {"C2_grouped_icc": c2_grouped_icc()}
    print(json.dumps(results["C2_grouped_icc"]["systems"], indent=1), flush=True)

    # Rerun of the two semi-synthetic cells with the MC truth reference
    # (first pass used the Gaussian-analytic truth — biased under real
    # residual pools; C1 gaussian and C3 results from the first pass stand).
    results["C1b_low_eer_semisynth_mctruth"] = coverage_run(
        rng, "C1b-mc", "low_eer_sota", 0.2, 200, 100, 10, True)
    results["cell5_dgp_robustness_mctruth"] = coverage_run(
        rng, "cell5-mc", "high_icc_organizer", 0.5, 400, 30, 3, True)

    out = Path(__file__).parent / "results_contingency.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
