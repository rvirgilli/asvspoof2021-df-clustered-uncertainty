"""Coherent marginal-sum simultaneous sensitivity output.

See ``plans/COHERENT-JACKKNIFE-DIAGNOSTIC.md``.  This intentionally avoids
combining a PSD-projected joint covariance with pair-specific variance floors.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from analyze_multiway import (
    contract,
    jack_cov,
    load_data,
    pair_cov,
    pair_matrix,
    refit_memmap,
    weighted_eer,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLAN = ROOT / "plans/COHERENT-JACKKNIFE-DIAGNOSTIC.md"
OUT = ROOT / "derived/results_coherent_jackknife.json"
SEED = 2026081605
GAUSSIAN_DRAWS = 200_000
BASELINES = {"RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite existing diagnostic: {OUT}")
    (
        _utts,
        labels,
        spk_names,
        spk_idx,
        _att_names,
        att_idx,
        cell_pairs,
        cell_idx,
        scores,
    ) = load_data()
    names = list(scores)
    orders = {name: np.argsort(scores[name]) for name in names}
    ones = np.ones(len(labels), dtype=np.float64)
    point = np.asarray(
        [100.0 * weighted_eer(orders[name], labels, ones) for name in names]
    )
    provenance, digest = contract(scores)
    is_spoof = labels == 0
    spk_masks = [spk_idx == index for index in range(len(spk_names))]
    spoof_attacks = np.unique(att_idx[is_spoof])
    att_masks = [is_spoof & (att_idx == index) for index in spoof_attacks]
    cell_masks = [is_spoof & (cell_idx == index) for index in range(len(cell_pairs))]
    ref_spk = refit_memmap("speaker", spk_masks, names, orders, labels, digest)
    ref_att = refit_memmap("attack", att_masks, names, orders, labels, digest)
    ref_cell = refit_memmap(
        "speaker_attack_cell", cell_masks, names, orders, labels, digest
    )

    cov_spk = jack_cov(ref_spk)
    cov_att = jack_cov(ref_att)
    cov_cell = jack_cov(ref_cell)
    cov_raw = cov_spk + cov_att - cov_cell
    cov_sum = cov_spk + cov_att
    eigen_checks = {
        "Sigma_speaker": np.linalg.eigvalsh(cov_spk),
        "Sigma_attack": np.linalg.eigvalsh(cov_att),
        "Sigma_cell": np.linalg.eigvalsh(cov_cell),
        "Sigma_sum": np.linalg.eigvalsh(cov_sum),
        "Sigma_sum_minus_speaker": np.linalg.eigvalsh(cov_sum - cov_spk),
        "Sigma_sum_minus_attack": np.linalg.eigvalsh(cov_sum - cov_att),
        "Sigma_sum_minus_raw": np.linalg.eigvalsh(cov_sum - cov_raw),
    }
    if min(float(values.min()) for values in eigen_checks.values()) < -1e-9:
        raise AssertionError("PSD/Loewner dominance check failed")

    pairs = [(a, b) for index, a in enumerate(names) for b in names[index + 1 :]]
    pair_names = [f"{a} vs {b}" for a, b in pairs]
    contrast_cov = pair_cov(cov_sum, pairs, names)
    sd = np.sqrt(np.diag(contrast_cov))
    if np.any(~np.isfinite(sd)) or np.any(sd <= 0):
        raise AssertionError("invalid marginal-sum pair SD")
    rng = np.random.default_rng(SEED)
    system_draws = rng.multivariate_normal(
        np.zeros(len(names)), cov_sum, size=GAUSSIAN_DRAWS, check_valid="raise"
    )
    pair_draws = pair_matrix(system_draws, pairs, names)
    q = float(np.percentile(np.max(np.abs(pair_draws) / sd, axis=1), 95.0))
    point_pairs = np.asarray(
        [point[names.index(a)] - point[names.index(b)] for a, b in pairs]
    )

    old = json.loads((ROOT / "derived/results_multiway_real.json").read_text())
    product = {
        key: bool(value["product_bootstrap_resolved_simultaneous"])
        for key, value in old["pairs"].items()
    }
    floored_exact = {
        key: bool(value["explicit_cell_jackknife"]["resolved_simultaneous_own_q"])
        for key, value in old["pairs"].items()
    }
    result_pairs: dict[str, object] = {}
    for index, key in enumerate(pair_names):
        interval = [
            float(point_pairs[index] - q * sd[index]),
            float(point_pairs[index] + q * sd[index]),
        ]
        result_pairs[key] = {
            "delta_eer_pts": round(float(point_pairs[index]), 6),
            "V_speaker": float(pair_cov(cov_spk, [pairs[index]], names)[0, 0]),
            "V_attack": float(pair_cov(cov_att, [pairs[index]], names)[0, 0]),
            "V_cell": float(pair_cov(cov_cell, [pairs[index]], names)[0, 0]),
            "V_raw_exact_cell": float(pair_cov(cov_raw, [pairs[index]], names)[0, 0]),
            "V_coherent_marginal_sum": float(sd[index] ** 2),
            "se_coherent_marginal_sum": float(sd[index]),
            "simultaneous": [round(value, 6) for value in interval],
            "resolved_simultaneous": bool(not (interval[0] <= 0.0 <= interval[1])),
            "product_bootstrap_resolved_simultaneous": product[key],
            "old_floored_exact_cell_resolved_simultaneous": floored_exact[key],
            "organizer_baseline_pair": set(key.split(" vs ")) <= BASELINES,
        }

    baseline_keys = [
        key for key in pair_names if result_pairs[key]["organizer_baseline_pair"]
    ]
    payload = {
        "status": "post-audit descriptive diagnostic; no population or coverage claim",
        "construction": "Sigma_sum = Sigma_speaker + Sigma_attack; one coherent covariance supplies both pair SEs and Gaussian max-t critical value",
        "seed": SEED,
        "gaussian_draws": GAUSSIAN_DRAWS,
        "q95": q,
        "n_trials": int(len(labels)),
        "n_speakers": int(len(spk_names)),
        "n_spoof_attacks": int(len(spoof_attacks)),
        "n_observed_spoof_cells": int(len(cell_pairs)),
        "minimum_eigenvalues": {
            key: float(values.min()) for key, values in eigen_checks.items()
        },
        "organizer_baseline_resolved": {
            "coherent_marginal_sum": sum(
                result_pairs[key]["resolved_simultaneous"] for key in baseline_keys
            ),
            "product_bootstrap": sum(product[key] for key in baseline_keys),
            "old_floored_exact_cell": sum(floored_exact[key] for key in baseline_keys),
        },
        "all_28_resolved_coherent_marginal_sum": sum(
            value["resolved_simultaneous"] for value in result_pairs.values()
        ),
        "pairs": result_pairs,
        "input_provenance": provenance,
        "sha256": {
            "plan": sha256(PLAN),
            "script": sha256(Path(__file__)),
            "results_multiway_real": sha256(HERE / "results_multiway_real.json"),
        },
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        "coherent marginal-sum diagnostic:",
        payload["organizer_baseline_resolved"],
        f"all={payload['all_28_resolved_coherent_marginal_sum']}/28",
        f"q={q:.6f}",
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
