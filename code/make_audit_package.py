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
  contrasts    all 28 pairs: delta, product-bootstrap interval, exact-cell
               jackknife interval, verdict
  multiway_intersection  every exact speaker, attack and observed-cell variance term
  floor_scope  the pairs the attack-budget statement covers, and its conditions
  coverage_mc  the superseded R=200 pilot, retained and explicitly labelled
  coverage_validation  the completed 48-cell EXP-105 closure and reading rule
  variant_by_pair  what each resampling variant resolves alone, since a pair counts as
               resolved only when both exclude zero

Writes audit-regenerated/audit.json. Inputs are not
redistributed; see the package README for the three path variables.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, KEY, weighted_eer

HERE = Path(__file__).parent
ROOT = HERE.parent
DERIVED = ROOT / "derived"
OUT = ROOT / "audit-regenerated"
SSL_ERA = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
BASELINE = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]


def sha(p):
    b = Path(p).read_bytes()
    digest = hashlib.sha256(b).hexdigest()
    return {"sha256": digest, "sha256_16": digest[:16],
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

    sel = json.loads((DERIVED / "results_selection.json").read_text())["21df"]
    mw = json.loads((DERIVED / "results_multiway_real.json").read_text())
    def exact_cell_ci(pair):
        row = mw["pairs"][pair]
        d = row["delta_eer_pts"]
        se = row["explicit_cell_jackknife"]["se_psd_floor"]
        q = mw["q95_gaussian_explicit_cell_jackknife_psd"]
        return [round(d - q * se, 3), round(d + q * se, 3)]

    pkg["contrasts"] = {
        k2: {"delta_eer_pts": v["delta_eer_pts"],
             "ci_pointwise": v["ci_pointwise"], "ci_simultaneous": v["ci_simultaneous"],
             "ci_exact_cell_jackknife_simultaneous": exact_cell_ci(k2),
             "resolved_simultaneous": v["resolved_simultaneous"],
             "product_bootstrap_and_exact_cell_agree":
                 bool(v["resolved_simultaneous"] ==
                      mw["pairs"][k2]["explicit_cell_jackknife"]["resolved_simultaneous_own_q"])}
        for k2, v in sel["pairs"].items()}
    pkg["seeds"] = {"selection_B5000": 20260817, "widths": 20260818, "scaling": 20260819,
                    "floor_ci_B4000": 20260820, "verdict_ci_R150": 20260821,
                    "source_permutation_B20000": 20260822,
                    "exp105_outer": 20260824,
                    "supt_critical_value": sel["supt_critical_value"]}

    _mw_ratios = [v["explicit_cell_jackknife"]["se_psd_floor"] /
                  v["current_iid_proxy_se"] for v in mw["pairs"].values()]
    pkg["multiway_intersection"] = {
        "estimator": "exact delete-one speaker + delete-one spoof attack - delete-one "
                     "observed spoof speaker-by-attack cell; pairwise marginal-component "
                     "adjustment max(V_raw, V_speaker, V_attack) is disclosed rather than "
                     "hidden and is not a PSD repair of the full covariance matrix",
        "n_observed_spoof_cells": mw["n_observed_spoof_cells"],
        "cell_size": mw["cell_size"],
        "n_negative_raw_variances": sum(
            v["explicit_cell_jackknife"]["V_raw_inclusion_exclusion"] < 0
            for v in mw["pairs"].values()),
        "exact_cell_over_old_proxy_se_ratio": {
            "min": min(_mw_ratios), "median": float(np.median(_mw_ratios)),
            "max": max(_mw_ratios)},
        "linearized_crve_gate_all_pairs_pass": mw["linearization_gate_all_pairs_pass"],
        "linearized_crve_status": "EXCLUDED_FAILED_PREREGISTERED_GATE",
        "q95_gaussian_exact_cell_max_t":
            mw["q95_gaussian_explicit_cell_jackknife_psd"],
        "organizer_baseline_resolved": mw["organizer_baseline_resolved"],
        "per_pair": {k2: {
            "V_speaker": v["explicit_cell_jackknife"]["V_speaker"],
            "V_attack": v["explicit_cell_jackknife"]["V_attack"],
            "V_speaker_attack_cell":
                v["explicit_cell_jackknife"]["V_speaker_attack_cell"],
            "V_raw_inclusion_exclusion":
                v["explicit_cell_jackknife"]["V_raw_inclusion_exclusion"],
            "V_psd_floor": v["explicit_cell_jackknife"]["V_psd_floor"],
            "se_psd_floor": v["explicit_cell_jackknife"]["se_psd_floor"],
            "resolved_simultaneous_own_q":
                v["explicit_cell_jackknife"]["resolved_simultaneous_own_q"],
            "linearization_gate": v["linearization_gate"],
        } for k2, v in mw["pairs"].items()},
    }

    fl = json.loads((DERIVED / "results_floor_ci.json").read_text())
    below = [k2 for k2, v in fl["pairs"].items()
             if not v["resolved_simultaneous"] and
             v["gap"] < v["half_finite_A_component_point"]]
    pkg["floor_scope"] = {
        "status": "WITHDRAWN_PENDING_INTERACTION_DECOMPOSITION",
        "statement": "this is a finite-A speaker component, not an A-to-infinity floor: it "
                     "contains speaker-by-attack interaction divided by the observed attack "
                     "count. These pairs are below half that measured component, but no "
                     "counterfactual attack-budget claim follows without decomposing the "
                     "interaction.",
        "pairs_below_half_finite_A_component": sorted(below),
        "n_point_estimate": len(below),
        "bootstrap_ci_on_the_count": fl["summary"]["bootstrap_count_ci95"],
        "p_at_least_6": fl["summary"]["p_at_least_6_of_10"],
        "p_at_least_5": fl["summary"]["p_at_least_5_of_10"],
    }

    def wilson(p, n, z=1.96):
        c = p + z * z / (2 * n)
        h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
        return [round((c - h) / (1 + z * z / n), 3), round((c + h) / (1 + z * z / n), 3)]

    cov = json.loads((DERIVED / "results_coverage_real.json").read_text())
    R = cov["R"]
    pkg["coverage_mc"] = {
                          "status": "SUPERSEDED_DIAGNOSTIC_PILOT_NOT_VALIDATION",
                          "superseded_by": "coverage_validation / EXP-105",
                          "R": R,
                          "note": "historical fitted-DGP pilot retained for audit history; "
                                  "its low-EER values may not support coverage claims",
                          "organizer_era": {v: {"coverage": cov[v]["coverage"],
                                                "mc_interval": wilson(cov[v]["coverage"], R)}
                                            for v in ("iid", "twoway", "jackknife", "wild")
                                            if v in cov}}
    low = json.loads((DERIVED / "results_contingency.json").read_text())["C1b_low_eer_semisynth_mctruth"]
    pkg["coverage_mc"]["low_eer"] = {
        v: {"coverage": low[v]["coverage"], "mc_interval": wilson(low[v]["coverage"], low["R"])}
        for v in ("twoway", "jackknife") if v in low and "coverage" in low[v]}

    # The completed EXP-105 grid supersedes the small pilot above.  This block
    # is built from the strict closure artifacts rather than transcribed from
    # the paper so the adverse reading rule is mechanically preserved.
    cov_original = json.loads(
        (DERIVED / "results_coverage_interaction.json").read_text())
    cov_grid = json.loads(
        (DERIVED / "results_coverage_interaction_recalibrated.json").read_text())
    cov_diag = json.loads(
        (DERIVED / "results_coverage_diagnostics.json").read_text())
    cov_verified = json.loads(
        (DERIVED / "results_exp105_verified.json").read_text())
    cov_crosspath = json.loads(
        (DERIVED / "results_crosspath_gate.json").read_text())
    org_cells = [row for row in cov_grid["grid"]
                 if row["spec"]["regime"] == "organizer"]
    low_cells = [row for row in cov_grid["grid"]
                 if row["spec"]["regime"] == "low_eer"]

    def coverage_range(cells, name):
        values = [row["coverage"][name]["coverage"] for row in cells]
        return [min(values), max(values)]

    former_failure = next(
        row for row in low_cells
        if row["spec"] == {"regime": "low_eer", "interaction_share": 0.0,
                           "tail": "gaussian", "target_delta_pts": 2.0})
    pkg["coverage_validation"] = {
        "experiment": "EXP-105",
        "status_under_preregistered_reading_rule":
            cov_verified["status_under_preregistered_reading_rule"],
        "confirmed_estimators": cov_verified["confirmed_estimators"],
        "contract": {
            "seed": cov_original["seed"],
            "outer_replicates_per_cell": cov_original["R"],
            "product_bootstrap_draws_per_replicate":
                cov_original["grid"][0]["product"]["B"],
            "n_cells": len(cov_original["grid"]),
            "n_outer_replicates_total":
                cov_original["R"] * len(cov_original["grid"]),
        },
        "organizer": {
            "n_cells": len(org_cells),
            "coverage_ranges": {name: coverage_range(org_cells, name)
                                for name in ("raw", "floor", "product")},
            "all_cells_inside_092_098": {
                name: all(0.92 <= row["coverage"][name]["coverage"] <= 0.98
                          for row in org_cells)
                for name in ("raw", "floor", "product")},
            "baseline_pairs_resolved":
                cov_verified["organizer_baseline_pairs_resolved"],
            "six_pair_conclusion_invariant":
                cov_verified["six_pair_conclusion_invariant"],
        },
        "low_eer": {
            "n_cells": len(low_cells),
            "coverage_ranges": {name: coverage_range(low_cells, name)
                                for name in ("raw", "floor", "product")},
            "n_cells_any_estimator_below_090": sum(
                any(row["coverage"][name]["coverage"] < 0.90
                    for name in ("raw", "floor", "product"))
                for row in low_cells),
            "n_cells_all_estimators_below_090": sum(
                all(row["coverage"][name]["coverage"] < 0.90
                    for name in ("raw", "floor", "product"))
                for row in low_cells),
            "former_failure_condition": {
                "index": former_failure["index"],
                "spec": former_failure["spec"],
                "coverage": {name: former_failure["coverage"][name]["coverage"]
                             for name in ("raw", "floor", "product")},
            },
            "oracle_constant_sd_minimum_coverage":
                cov_diag["low_eer_minimum_coverage"]["oracle_sd_normal"],
        },
        "truth_sensitivity_minimum_coverage":
            cov_grid["minimum_coverage_under_truth_sensitivity"],
        "crosspath_gate": {
            "pass": cov_crosspath["pass"],
            "weighted_real_score_comparisons": cov_crosspath["comparisons"],
            "max_product_weight_eer_difference":
                cov_crosspath["max_real_product_weight_eer_difference"],
        },
        "scope_consequence": (
            "formal coverage support is retained for the organizer-baseline "
            "reversal; modern low-EER and Arena intervals/ranks are descriptive"),
        "authoritative_artifact": "derived/results_exp105_verified.json",
    }

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
        jack = mw["pairs"][k2]["explicit_cell_jackknife"]["resolved_simultaneous_own_q"]
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
                "and the exact-cell multiway delete-one jackknife exclude zero",
        "n_pairs_where_the_two_disagree": len(dis),
        "pairs_where_they_disagree": sorted(dis),
        "all_28": by_variant,
        "the_12_close_comparisons": close,
    }
    print(f"  variant-by-pair: the two procedures disagree on {len(dis)} of 28 pairs")

    # Quantities the paper reports that lived only in prose or intermediates. The
    # campaign scripts already compute them; they were simply not wired in here, which
    # made this package's own coverage claim false.
    sc = json.loads((DERIVED / "results_scaling.json").read_text())
    fl_full = json.loads((DERIVED / "results_floor.json").read_text())
    fci = json.loads((DERIVED / "results_floor_ci.json").read_text())
    src = json.loads((DERIVED / "results_source.json").read_text())
    icc = json.loads((DERIVED / "results_icc.json").read_text())
    _iccs = [v["speaker_icc_bona"]["icc"] for v in icc["21df"].values() if "speaker_icc_bona" in v]

    pkg["width_ratios"] = {
        "clustered_over_iid_all_28": sc["summary"]["width_ratio_all_28"],
        "median": sc["summary"]["width_ratio_median"],
        "n_resolved_under_iid": sc["summary"]["n_resolved_iid"],
        "per_pair": {k: v["width_ratio_clustered_over_iid"]
                     for k, v in sc["iid_over_all_pairs"].items()},
    }
    _shares = [v["speaker_fraction_of_two_marginal_components"]
               for v in fl_full["pairs"].values()]
    pkg["finite_A_marginal_component_ratios"] = {
        "speaker_fraction_range": [min(_shares), max(_shares)],
        "speaker_icc_bona_range": [min(_iccs), max(_iccs)],
        "per_pair": {k: {"V_spk": v["V_spk"], "V_att": v["V_att"],
                         "speaker_fraction_of_two_marginal_components":
                             v["speaker_fraction_of_two_marginal_components"],
                         "finite_A_speaker_component_width_pts":
                             v["finite_A_speaker_component_width_pts"]}
                     for k, v in fl_full["pairs"].items()},
    }
    pkg["finite_A_component_count"] = {
        "point_estimate":
            fci["summary"]["point_estimate_count_below_half_finite_A_component"],
        "bootstrap_ci95": fci["summary"]["bootstrap_count_ci95"],
        "p_at_least_5_of_10": fci["summary"]["p_at_least_5_of_10"],
        "p_at_least_6_of_10": fci["summary"]["p_at_least_6_of_10"],
        "per_pair_p_gap_below_half_component": {
            k: v["p_gap_below_half_finite_A_component"]
            for k, v in fci["pairs"].items()},
    }
    _pn = src["permutation_null"]
    _ps = sorted((v["p_value"], k) for k, v in _pn["pairs"].items())
    _m, _run, _holm = len(_ps), 0.0, []
    for _i, (_p, _k) in enumerate(_ps):
        _run = max(_run, min(1.0, _p * (_m - _i)))
        _holm.append((_k, _p, round(_run, 5)))
    pkg["source_corpus_test"] = {
        "null_expectation": _pn["analytic_expected_share_under_no_effect"],
        "B": _pn["B"],
        "p_value_rule": _pn["p_value_rule"],
        "multiplicity": "Holm-Bonferroni over the 12 within-generation pairs",
        "per_pair": {k: {"observed_share": _pn["pairs"][k]["observed"],
                         "p_raw": _pn["pairs"][k]["p_value"], "p_holm": h} for k, _p, h in _holm},
        "n_significant_raw_05": sum(1 for _k, p, _h in _holm if p < 0.05),
        "n_significant_holm_05": sum(1 for _k, _p, h in _holm if h < 0.05),
    }
    pkg["leave_one_corpus_out"] = src["leave_one_corpus_out"]

    (OUT / "audit.json").write_text(json.dumps(pkg, indent=2) + "\n")
    print(f"wrote {OUT/'audit.json'}")
    print(f"  intersection identical across all eight systems: "
          f"{pkg['intersection']['identical_across_systems']}")
    print(f"  n0 {pkg['cluster_size']['unbalanced_effective_size_n0']} vs mean "
          f"{pkg['cluster_size']['arithmetic_mean_N_over_k']}")
    print(f"  contrasts: {len(pkg['contrasts'])}")


if __name__ == "__main__":
    main()
