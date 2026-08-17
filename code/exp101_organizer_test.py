"""EXP-101: reconstruct both cited significance-test variants on four DF baselines.

Why: ASVspoof 2021's overview (Yamagishi et al., ASVspoof Workshop 2021, Fig. 4c)
publishes a Holm-corrected pairwise significance matrix for the DF task whose axis
includes all four organizer baselines B01-B04 -- i.e. four of the eight systems in
our available-score pool, on the same evaluation set. That makes the six
baseline-vs-baseline pairs a like-for-like comparison against a published verdict.

The overview says only that Fig. 4c was estimated according to Bengio & Mariethoz
(Odyssey 2004); it does not disclose which of that paper's independent and
dependent variants generated the figure. The verdict must therefore not be
attributed by reading cell colours off a greyscale figure. We reconstruct both
variants on the released scores and compare them with our clustered result.

Estimator (i.i.d. binomial, the assumption under test):
    at the EER point FAR = FRR = e, and for HTER = (FAR+FRR)/2,
        Var(e) = [ e(1-e)/n_spoof + e(1-e)/n_bona ] / 4
    two systems, unpaired:  z = (e1 - e2) / sqrt(Var(e1) + Var(e2))
This is the "independent" form. For the dependent form, each system gets its own
non-interpolated EER operating point and we estimate the variance of the paired
error-rate difference from the systems' discordant decisions, separately for bona
fide and spoof trials. The EER thresholds are selected on this same evaluation set,
whereas Bengio & Mariethoz assume a fixed model and threshold, so both results are
explicitly labelled reconstructions of the overview's adaptation rather than exact
finite-sample tests or claims about the unpublished cells in Fig. 4c.

Outputs results_organizer_test.json. Writes no existing artifact.
"""

import json
from math import erf, log, sqrt
from pathlib import Path

import numpy as np

from exp101_floor import input_provenance
from m1_campaign import DF_SCORES, KEY, plain_eer

BASELINES = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]
# ASVspoof 2021 baseline numbering (overview paper §5): B01 CQCC-GMM, B02 LFCC-GMM,
# B03 LFCC-LCNN, B04 RawNet2.
BXX = {"CQCC-GMM": "B01", "LFCC-GMM": "B02", "LFCC-LCNN": "B03", "RawNet2": "B04"}
PUBLISHED_EER = {"RawNet2": 22.38, "LFCC-LCNN": 23.48, "LFCC-GMM": 25.25, "CQCC-GMM": 25.56}
# Family sizes for Holm: 6 = the baseline pairs alone; 253 = all pairs among the 23
# systems visible on the Fig. 4c axis; 561 = all pairs among 34 (30 submissions + 4
# baselines), an upper bound. A larger family is a STRICTER correction.
FAMILY_SIZES = [6, 253, 561]


def norm_sf2(z):
    """Two-sided normal tail probability (0.0 when it underflows float64)."""
    return 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))


def log10_p_asymptotic(z):
    """log10 of the two-sided tail, for |z| large enough that norm_sf2 underflows.

    2*(1-Phi(z)) ~ 2*phi(z)/z, so log10 p ~ -z^2/(2 ln10) - log10(z*sqrt(pi/2)).
    Reported instead of a bare 0.0 so the artifact does not claim p is exactly zero.
    """
    from math import log10, pi
    z = abs(z)
    return -z * z / (2 * log(10)) - log10(z * sqrt(pi / 2))


def var_eer(e, n_spoof, n_bona):
    return (e * (1 - e) / n_spoof + e * (1 - e) / n_bona) / 4


def eer_and_errors(scores, labels):
    """Non-interpolated EER and the trial errors at that system-specific point.

    This reproduces ``plain_eer`` exactly, including its stable discrete threshold
    rule, while retaining the decisions needed by the dependent reconstruction.
    Scores above the selected position are classified bona fide.
    """
    order = np.argsort(scores)
    lab = labels[order]
    cb = np.cumsum(lab)
    cs = np.cumsum(1 - lab)
    frr = cb / cb[-1]
    far = 1.0 - cs / cs[-1]
    cut = int(np.argmin(np.abs(frr - far)))
    err_sorted = np.where(lab == 1, np.arange(len(lab)) <= cut,
                          np.arange(len(lab)) > cut)
    errors = np.empty(len(lab), dtype=bool)
    errors[order] = err_sorted
    return float((frr[cut] + far[cut]) / 2), errors, cut


def paired_difference_variance(err_a, err_b, mask):
    """Variance of a paired Bernoulli-rate difference on one trial class."""
    diff = err_a[mask].astype(np.float64) - err_b[mask].astype(np.float64)
    return float((np.mean(diff * diff) - np.mean(diff) ** 2) / len(diff))


def holm(pvals, m=None):
    """Holm-Bonferroni; m lets the family be larger than the pairs listed."""
    m = m or len(pvals)
    order = sorted(pvals, key=pvals.get)
    adj, running = {}, 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * pvals[k]))
        adj[k] = running
    return adj


def main():
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = p[5]
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u] == "bonafide" else 0 for u in utts])
    n_bona, n_spoof = int(labels.sum()), int((1 - labels).sum())

    eer, errors = {}, {}
    scores = {}
    for m in BASELINES:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        s = np.array([float(d[u]) for u in utts])
        scores[m] = s
        eer[m], errors[m], _ = eer_and_errors(s, labels)
        assert eer[m] == plain_eer(s, labels)
        print(f"{BXX[m]} {m:<10} EER {100*eer[m]:6.3f}  (published {PUBLISHED_EER[m]})",
              flush=True)
        assert abs(100 * eer[m] - PUBLISHED_EER[m]) < 0.05, "EER does not reproduce"

    results = {
        "source": "Yamagishi et al., ASVspoof 2021 overview (ASVspoof Workshop 2021), "
                  "Fig. 4c cites Bengio & Marie'thoz, Odyssey 2004 without disclosing "
                  "which variant was used",
        "eval_phase_trials": len(utts), "n_bona": n_bona, "n_spoof": n_spoof,
        "eer_percent": {BXX[m]: round(100 * eer[m], 3) for m in BASELINES},
        "note": "Both cited variants are reconstructed with a system-specific, "
                "non-interpolated EER threshold selected on eval. Because Bengio & "
                "Marie'thoz assume a fixed model and threshold, neither reconstruction "
                "is described as an exact finite-sample test or as the unpublished Fig. 4c cells.",
        "pairs": {},
    }

    pvals = {}
    pvals_dependent = {}
    order = sorted(BASELINES, key=lambda m: eer[m])
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            d = eer[a] - eer[b]
            se = sqrt(var_eer(eer[a], n_spoof, n_bona) + var_eer(eer[b], n_spoof, n_bona))
            z = d / se
            p = norm_sf2(z)
            v_dep = (paired_difference_variance(errors[a], errors[b], labels == 0)
                     + paired_difference_variance(errors[a], errors[b], labels == 1)) / 4
            z_dep = d / sqrt(v_dep)
            p_dep = norm_sf2(z_dep)
            key = f"{BXX[a]} vs {BXX[b]}"
            pvals[key] = p
            pvals_dependent[key] = p_dep
            entry = {
                "systems": f"{a} vs {b}",
                "delta_eer_pts": round(100 * d, 3),
                "z_iid": round(z, 2),
                "p_raw": p,
                "z_dependent": round(z_dep, 3),
                "p_raw_dependent": p_dep,
                "discordant_bona": int(np.sum(errors[a][labels == 1] != errors[b][labels == 1])),
                "discordant_spoof": int(np.sum(errors[a][labels == 0] != errors[b][labels == 0])),
            }
            if p == 0.0:
                entry["p_raw_underflowed"] = True
                entry["log10_p_asymptotic"] = round(log10_p_asymptotic(z), 1)
            if p_dep == 0.0:
                entry["p_raw_dependent_underflowed"] = True
                entry["log10_p_dependent_asymptotic"] = round(log10_p_asymptotic(z_dep), 1)
            results["pairs"][key] = entry

    for m in FAMILY_SIZES:
        adj = holm(pvals, m=m)
        adj_dep = holm(pvals_dependent, m=m)
        for k, v in adj.items():
            results["pairs"][k][f"p_holm_family{m}"] = v
            results["pairs"][k][f"significant_holm_family{m}"] = bool(v <= 0.05)
            results["pairs"][k][f"p_holm_dependent_family{m}"] = adj_dep[k]
            results["pairs"][k][f"significant_holm_dependent_family{m}"] = bool(adj_dep[k] <= 0.05)

    # Smallest family size that would render each pair non-significant, i.e. how
    # implausibly large the organizers' correction would have to be for the figure
    # to show these pairs as white.
    for k, p in pvals.items():
        results["pairs"][k]["family_size_needed_to_lose_significance"] = (
            int(np.ceil(0.05 / p)) if p > 1e-12 else "> 1e10 (astronomically larger than any "
                                                    "plausible family)")

    # Cross-check with OUR paired i.i.d. permutation test on the same pairs (the key
    # name must not suggest an organizer release). Where the systems' errors are
    # positively correlated -- as they are here -- a paired form removes shared
    # variance and tends to be more significant; note however that this test leaves
    # B02 vs B01 unresolved (p = 0.131), so we do not speculate that the sixth pair
    # would become significant under a paired form of the organizers' test.
    derived = Path(__file__).parent.parent / "derived"
    pairs_path = derived / "results_pairs.json"
    pairs_art = json.load(open(pairs_path))["21df"]["pairs"]
    for k, v in results["pairs"].items():
        a, b = v["systems"].split(" vs ")
        hit = pairs_art.get(f"{a} vs {b}") or pairs_art.get(f"{b} vs {a}")
        if hit:
            v["our_paired_permutation_p"] = hit["perm_p"]

    # Our clustered verdict on the same six pairs, for the contrast.
    sel_path = derived / "results_selection.json"
    sel = json.load(open(sel_path))
    results["_input_provenance_sha256"] = input_provenance(pairs_path, sel_path)
    inv = {v: k for k, v in BXX.items()}
    for k, v in results["pairs"].items():
        a, b = (inv[x] for x in k.split(" vs "))
        hit = sel["21df"]["pairs"].get(f"{a} vs {b}") or sel["21df"]["pairs"].get(f"{b} vs {a}")
        v["clustered_resolved_simultaneous"] = hit["resolved_simultaneous"]
        v["clustered_resolved_jackknife"] = hit["resolved_jackknife"]
        v["clustered_ci_simultaneous"] = hit["ci_simultaneous"]

    n_sig = {m: sum(results["pairs"][k][f"significant_holm_family{m}"] for k in pvals)
             for m in FAMILY_SIZES}
    n_sig_dep = {
        m: sum(results["pairs"][k][f"significant_holm_dependent_family{m}"] for k in pvals)
        for m in FAMILY_SIZES}
    n_clust = sum(results["pairs"][k]["clustered_resolved_simultaneous"] and
                  results["pairs"][k]["clustered_resolved_jackknife"] for k in pvals)
    results["summary"] = {
        "n_pairs": len(pvals),
        "n_significant_by_holm_family": n_sig,
        "n_significant_independent_by_holm_family": n_sig,
        "n_significant_dependent_by_holm_family": n_sig_dep,
        "n_resolved_clustered": n_clust,
    }
    print("\nsignificant under the independent reconstruction, by Holm family size:",
          n_sig, flush=True)
    print("significant under the dependent reconstruction, by Holm family size:",
          n_sig_dep, flush=True)
    print("resolved under speaker x attack clustering:", n_clust, "of", len(pvals), flush=True)
    for k, v in results["pairs"].items():
        print(f"  {k:<14} {v['systems']:<26} d={v['delta_eer_pts']:6.2f}  "
              f"z_ind={v['z_iid']:6.1f} z_dep={v['z_dependent']:6.1f}  "
              f"p={v['p_raw']:.2e}  clustered={'res' if v['clustered_resolved_simultaneous'] else 'UNRES'}",
              flush=True)

    out = derived / "results_organizer_test.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
