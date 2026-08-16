"""EXP-101: what the fitted Gaussian DGP reproduces, in each regime.

The paper's choice of certification regime rests on which fit reproduces the real
error rates. Those fitted population EERs were computed but never released: the
organizer-era pair's 22.8% appeared in the paper and resolved to no key in any
artifact, which is precisely the "cite the artifact or label it unverified" failure.
This records them.

It also records what the fit does NOT reproduce. At organizer-era rates the fitted
population EERs are the right scale but their DIFFERENCE (4.68 pts) is far from the
real gap (1.09 pts). That does not invalidate the coverage check, which asks whether
an interval covers the DGP's own population Delta-EER -- computed by Monte Carlo, not
assumed equal to the real one -- but it is a limitation of the model and belongs in
the record rather than in a reader's inference from a number we printed.

No resampling, no simulation: a closed-form EER under the fitted normals.
Writes results_dgp_fit.json. Modifies nothing.
"""

import json
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, KEY, plain_eer
from power_curves import PAIRS, calibrate, gauss_eer

REAL_PAIRS = {"high_icc_organizer": ("RawNet2", "LFCC-LCNN"),
              "low_eer_sota": ("XLSR-Mamba", "XLS-R+SLS")}


def real_eers(names):
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    out = []
    for m in names:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        out.append(100 * plain_eer(np.array([float(d[u]) for u in utts]), labels))
    return out


def main():
    results = {
        "estimator": "population EER under the fitted bivariate Gaussian random-effects "
                     "model: bona fide N(mu, sd_grp (+) sd_res), spoof N(mu, sd_spk (+) "
                     "sd_att (+) sd_res); closed form, no simulation",
        "why": "the paper cites the fitted population EERs to justify certifying coverage "
               "at organizer-era rates and not in the low-EER regime",
        "regimes": {},
    }
    for tag, paths in PAIRS.items():
        cal, _ = calibrate(paths)
        b, s = cal["bona"], cal["spoof"]
        fitted = []
        for i in (0, 1):
            sd_b = float(np.hypot(b[f"sd_grp{i}"], b[f"sd_res{i}"]))
            sd_s = float(np.sqrt(s[f"sd_spk{i}"] ** 2 + s[f"sd_att{i}"] ** 2
                                 + s[f"sd_res{i}"] ** 2))
            fitted.append(100 * gauss_eer(b[f"mu{i}"], sd_b, s[f"mu{i}"], sd_s))
        names = REAL_PAIRS[tag]
        real = real_eers(names)
        results["regimes"][tag] = {
            "systems": list(names),
            "fitted_population_eer_pct": [round(x, 2) for x in fitted],
            "real_pooled_eer_pct": [round(x, 2) for x in real],
            "ratio_fitted_over_real": [round(f / r, 3) for f, r in zip(fitted, real)],
            "fitted_delta_pts": round(fitted[1] - fitted[0], 3),
            "real_delta_pts": round(real[1] - real[0], 3),
        }
        r = results["regimes"][tag]
        print(f"{tag:<20} fitted {r['fitted_population_eer_pct']} vs real "
              f"{r['real_pooled_eer_pct']}  (ratios {r['ratio_fitted_over_real']}); "
              f"delta fitted {r['fitted_delta_pts']} vs real {r['real_delta_pts']}",
              flush=True)

    org, low = results["regimes"]["high_icc_organizer"], results["regimes"]["low_eer_sota"]
    results["summary"] = {
        "organizer_era_reproduces_rate_scale": True,
        "low_eer_ratio_fitted_over_real": low["ratio_fitted_over_real"],
        "note": "the organizer-era fit lands within a factor of 1.3 of the real rates "
                "while the low-EER fit is out by factors of ~7 and ~30, which is why the "
                "coverage check is certified in the former regime. Neither fit reproduces "
                "the GAP: organizer-era fitted delta "
                f"{org['fitted_delta_pts']} against a real {org['real_delta_pts']}. "
                "Coverage is therefore assessed against the model's own population "
                "Delta-EER (Monte Carlo), never against the real one.",
    }
    out = Path(__file__).parent / "results_dgp_fit.json"
    out.write_text(json.dumps(results, indent=2))
    print("\nsummary:", json.dumps(results["summary"], indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
