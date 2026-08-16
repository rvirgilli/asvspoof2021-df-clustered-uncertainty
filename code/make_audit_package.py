"""Emit the audit package for all 28 pairwise comparisons.

The paper reports intervals over eight systems, but the score intersections, fitted
variance components and simulation settings behind them cannot be checked from the PDF.
This derives each of those from the score files and the evaluation key, so every figure
in the paper can be recomputed rather than taken on trust.

Contents, all computed here rather than copied from prose:
  provenance   sha256 + byte/line counts for all eight score files and the eval key
  intersection the trial-ID rule, and the proof that all eight systems are scored on
               one identical set
  eer_rule     the tie and interpolation rule, demonstrated on the observed statistic
               and on a bootstrap replicate to show one routine serves both
  cluster_size the unbalanced effective cluster size n0 = 159.15, and why it differs
               from the arithmetic mean 14,869/93 = 159.88
  seeds        every seed and replicate count
  incidence    the speaker x attack incidence summary
  contrasts    all 28 pairs: delta, both interval variants, verdict
  floor_scope  the pairs the attack-budget statement covers, and its conditions
  coverage_mc  binomial Monte Carlo intervals on the coverage figures
  variant_by_pair  what each resampling variant resolves alone, since a pair counts as
               resolved only when both exclude zero

Writes audit_package/ (JSON + README.md). Modifies nothing. Inputs are not
redistributed; see the package README for the three path variables.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, KEY, weighted_eer

HERE = Path(__file__).parent
OUT = HERE / "audit_package"
SSL_ERA = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
BASELINE = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]


def sha(p):
    b = Path(p).read_bytes()
    return {"sha256_16": hashlib.sha256(b).hexdigest()[:16],
            "bytes": len(b), "lines": b.count(10)}


def main():
    OUT.mkdir(exist_ok=True)
    names = SSL_ERA + BASELINE
    pkg = {"provenance": {"eval_key": sha(KEY),
                          "scores": {m: sha(DF_SCORES[m]) for m in names}}}

    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5], p[3])
    eval_ids = set(utt2meta)

    # Trial intersection: the rule, and the proof that it binds identically for all eight.
    per_system = {}
    for m in names:
        ids = {l.split()[0] for l in DF_SCORES[m].read_text().splitlines()}
        per_system[m] = ids
    common = set.intersection(*per_system.values()) & eval_ids
    pkg["intersection"] = {
        "rule": "eval-phase trial IDs from the official DF key (column 8 == 'eval'), "
                "intersected with the ID set of every score file; all systems are scored "
                "on this identical set and no system contributes a trial another lacks",
        "n_eval_in_key": len(eval_ids),
        "n_common_to_all_eight": len(common),
        "per_system_ids_missing_from_common": {m: len(eval_ids - per_system[m]) for m in names},
        "identical_across_systems": all(eval_ids <= per_system[m] for m in names),
    }

    utts = sorted(eval_ids)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    att = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    is_spoof = labels == 0

    # Cluster size: N/k is the arithmetic mean; the design effect needs the unbalanced
    # effective size, which is smaller whenever speakers contribute unequal trial counts.
    cnt = np.bincount(spk[labels == 1])
    cnt = cnt[cnt > 0]
    N, k = int(cnt.sum()), len(cnt)
    pkg["cluster_size"] = {
        "bona_fide_trials": N, "speakers": k,
        "arithmetic_mean_N_over_k": round(N / k, 2),
        "unbalanced_effective_size_n0": round((N - (cnt ** 2).sum() / N) / (k - 1), 2),
        "per_speaker_min": int(cnt.min()), "per_speaker_max": int(cnt.max()),
        "why": "n0 is the one-way random-effects effective cluster size (Searle, unbalanced). "
               "It equals N/k only for equal-size clusters; here counts run 8 to 355, so the "
               "two differ. The design-effect figure in the paper uses n0.",
    }

    # EER rule, demonstrated on the observed statistic and on one bootstrap replicate.
    orders = {}
    for m in names:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        orders[m] = np.argsort(np.array([float(d[u]) for u in utts]))
    rng = np.random.default_rng(20260817)
    w1 = np.ones(len(labels))
    cs = np.bincount(rng.integers(0, spk.max() + 1, spk.max() + 1), minlength=spk.max() + 1)
    w2 = cs[spk].astype(float)
    drawn = np.bincount(rng.choice(np.unique(att[is_spoof]), size=len(np.unique(att[is_spoof])),
                                   replace=True), minlength=att.max() + 1)
    w2[is_spoof] *= drawn[att[is_spoof]]
    pkg["eer_rule"] = {
        "rule": "scores sorted ascending once per system; FRR and FAR accumulated as weighted "
                "cumulative sums; the operating point is argmin|FRR-FAR| and the EER is their "
                "mean at that point. No interpolation between adjacent thresholds. The SAME "
                "routine (weighted_eer) computes the observed statistic and every replicate; "
                "only the weight vector differs.",
        "tie_handling": "ties keep the sort order; check_tie_safety.py shows evaluating only at "
                        "distinct-score boundaries moves every pooled EER and every pairwise "
                        "delta by at most 0.0001 points",
        "demonstration": {
            "observed_weights_all_ones": {m: round(100 * weighted_eer(orders[m], labels, w1), 4)
                                          for m in names},
            "one_clustered_replicate": {m: round(100 * weighted_eer(orders[m], labels, w2), 4)
                                        for m in names},
        },
    }

    pkg["incidence"] = {
        "trials": len(labels), "bona_fide": int(labels.sum()), "spoof": int((1 - labels).sum()),
        "speakers_bona_fide": k, "speaker_ids_on_spoof_side": int(len(np.unique(spk[is_spoof]))),
        "attack_conditions_spoof": int(len(np.unique(att[is_spoof]))),
        "occupied_speaker_x_attack_cells": int(len({(int(a), int(b))
                                                    for a, b in zip(spk[is_spoof], att[is_spoof])})),
        "note": "the speaker field on a spoof trial is the VC/TTS target speaker, which is why "
                "fewer speaker ids appear there than on the bona-fide side",
    }

    sel = json.loads((HERE / "results_selection.json").read_text())["21df"]
    pkg["contrasts"] = {
        k2: {"delta_eer_pts": v["delta_eer_pts"],
             "ci_pointwise": v["ci_pointwise"], "ci_simultaneous": v["ci_simultaneous"],
             "ci_jackknife": v["ci_jackknife"],
             "resolved_simultaneous": v["resolved_simultaneous"],
             "both_certified_variants_agree": v["certified_agree"]}
        for k2, v in sel["pairs"].items()}
    pkg["seeds"] = {"selection_B5000": 20260817, "widths": 20260818, "scaling": 20260819,
                    "floor_ci_B4000": 20260820, "verdict_ci_R150": 20260821,
                    "source_permutation_B20000": 20260822,
                    "supt_critical_value": sel["supt_critical_value"]}

    fl = json.loads((HERE / "results_floor_ci.json").read_text())
    below = [k2 for k2, v in fl["pairs"].items()
             if not v["resolved_simultaneous"] and v["gap"] < v["half_floor_point"]]
    pkg["floor_scope"] = {
        "statement": "adding attacks alone cannot reach the target half-width for these pairs, "
                     "holding the observed effect and this speaker pool fixed; a genuinely new "
                     "attack family changes the effect itself and is not bounded here",
        "pairs_below_half_their_floor": sorted(below),
        "n_point_estimate": len(below),
        "bootstrap_ci_on_the_count": fl["summary"]["bootstrap_count_ci95"],
        "p_at_least_6": fl["summary"]["p_at_least_6_of_10"],
    }

    def wilson(p, n, z=1.96):
        c = p + z * z / (2 * n)
        h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
        return [round((c - h) / (1 + z * z / n), 3), round((c + h) / (1 + z * z / n), 3)]

    cov = json.loads((HERE / "results_coverage_real.json").read_text())
    R = cov["R"]
    pkg["coverage_mc"] = {"R": R, "note": "binomial (Wilson) Monte Carlo intervals; at R=200 a "
                                          "coverage near .95 carries about +/-3 points",
                          "organizer_era": {v: {"coverage": cov[v]["coverage"],
                                                "mc_interval": wilson(cov[v]["coverage"], R)}
                                            for v in ("iid", "twoway", "jackknife", "wild")
                                            if v in cov}}
    low = json.loads((HERE / "results_contingency.json").read_text())["C1b_low_eer_semisynth_mctruth"]
    pkg["coverage_mc"]["low_eer"] = {
        v: {"coverage": low[v]["coverage"], "mc_interval": wilson(low[v]["coverage"], low["R"])}
        for v in ("twoway", "jackknife") if v in low and "coverage" in low[v]}

    # Variant-by-pair. S3.2 requires BOTH the product-weight bootstrap and the
    # delete-one-cluster jackknife to exclude zero, and states that the crossed product
    # scheme is delicate and biased against resolution. A reader therefore needs to see
    # what each procedure resolves ALONE -- especially for the two weak modern
    # resolutions and the ten non-resolutions, where the conjunction does the work.
    SSL = set(SSL_ERA)
    by_variant = {}
    for k2, v in sel["pairs"].items():
        a, b = k2.split(" vs ")
        within = (a in SSL) == (b in SSL)
        boot = not (v["ci_simultaneous"][0] <= 0 <= v["ci_simultaneous"][1])
        jack = not (v["ci_jackknife"][0] <= 0 <= v["ci_jackknife"][1])
        by_variant[k2] = {
            "block": ("within-SSL" if a in SSL else "within-baseline") if within else "cross",
            "delta_eer_pts": v["delta_eer_pts"],
            "bootstrap_simultaneous_excludes_zero": boot,
            "jackknife_excludes_zero": jack,
            "resolved_requires_both": bool(boot and jack),
            "variants_disagree": bool(boot != jack),
        }
    dis = [k2 for k2, v in by_variant.items() if v["variants_disagree"]]
    close = {k2: v for k2, v in by_variant.items() if v["block"] != "cross"}
    pkg["variant_by_pair"] = {
        "rule": "a pair is resolved only if BOTH the product-weight simultaneous bootstrap "
                "and the delete-one-cluster jackknife exclude zero",
        "n_pairs_where_the_two_disagree": len(dis),
        "pairs_where_they_disagree": sorted(dis),
        "all_28": by_variant,
        "the_12_close_comparisons": close,
    }
    print(f"  variant-by-pair: the two procedures disagree on {len(dis)} of 28 pairs")

    (OUT / "audit.json").write_text(json.dumps(pkg, indent=2))
    print(f"wrote {OUT/'audit.json'}")
    print(f"  intersection identical across all eight systems: "
          f"{pkg['intersection']['identical_across_systems']}")
    print(f"  n0 {pkg['cluster_size']['unbalanced_effective_size_n0']} vs mean "
          f"{pkg['cluster_size']['arithmetic_mean_N_over_k']}")
    print(f"  contrasts: {len(pkg['contrasts'])}")


if __name__ == "__main__":
    main()
