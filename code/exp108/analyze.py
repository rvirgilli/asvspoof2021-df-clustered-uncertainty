#!/usr/bin/env python3
"""Compute raw EXP-108 policy and registered path-grid outcomes.

This file deliberately does not render a qualitative verdict.  REPORT.md is
authorized only after the independent verifier passes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from typing import Iterable

import numpy as np
import scipy

from build_contract import (
    DEFAULT_METADATA,
    POLICIES,
    Trial,
    build_policy_weights,
    load_trials,
    sha256_file,
    validate_policy,
)


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
DATA = Path(os.environ.get("M1_DATA_ROOT", PROJECT / "inputs/anti-spoofing"))
OFFICIAL = DATA / "official-scores"
SCORE_PATHS = {
    "XLSR-Mamba": OFFICIAL / "xlsr-mamba/Bmamba3_LA_WCE_1e-06_ES144_NE12.txt",
    "XLS-R+SLS": OFFICIAL / "xlsr-sls/scores_DF.txt",
    "XLSR-Conformer": OFFICIAL / "xlsr-conformer-rosello/Scores_Best_DF_Fixed_size_train.txt",
    "SSL-AASIST": Path(
        os.environ.get(
            "M1_SSL_AASIST_SCORES",
            DATA / "author-scores/ssl-aasist/Scores_DF.txt",
        )
    ),
    "RawNet2": DATA / "DF-keys-full/keys/DF/CM/RawNet2/score.txt",
    "LFCC-LCNN": DATA / "DF-keys-full/keys/DF/CM/LFCC-LCNN/score.txt",
    "LFCC-GMM": DATA / "DF-keys-full/keys/DF/CM/LFCC-GMM/score.txt",
    "CQCC-GMM": DATA / "DF-keys-full/keys/DF/CM/CQCC-GMM/score.txt",
}
SYSTEMS = tuple(SCORE_PATHS)
MODERN = frozenset(SYSTEMS[:4])
BASELINE = frozenset(SYSTEMS[4:])
PAIRS = tuple((SYSTEMS[i], SYSTEMS[j]) for i in range(8) for j in range(i + 1, 8))
EXPECTED_EMPIRICAL_EER = {
    "XLSR-Mamba": 1.884,
    "XLS-R+SLS": 1.916,
    "XLSR-Conformer": 2.273,
    "SSL-AASIST": 2.852,
    "RawNet2": 22.383,
    "LFCC-LCNN": 23.477,
    "LFCC-GMM": 25.247,
    "CQCC-GMM": 25.563,
}
GRID_DENOMINATOR = 10_000


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def pair_name(pair: tuple[str, str]) -> str:
    return f"{pair[0]} vs {pair[1]}"


def pair_block(pair: tuple[str, str]) -> str:
    left, right = pair
    if left in MODERN and right in MODERN:
        return "modern_within"
    if left in BASELINE and right in BASELINE:
        return "baseline_within"
    return "cross_generation"


def exact_sign(value: float) -> int:
    return int(np.sign(value))


def full_weighted_eer(
    scores: np.ndarray, labels: np.ndarray, weights: np.ndarray
) -> tuple[float, int]:
    order = np.argsort(scores)
    sorted_labels = labels[order]
    sorted_weights = weights[order]
    bona = np.cumsum(sorted_weights * sorted_labels)
    spoof = np.cumsum(sorted_weights * (1 - sorted_labels))
    frr = bona / bona[-1]
    far = 1.0 - spoof / spoof[-1]
    index = int(np.argmin(np.abs(frr - far)))
    return float((frr[index] + far[index]) / 2.0), index


def stable_id_weighted_eer(
    scores: np.ndarray, labels: np.ndarray, weights: np.ndarray
) -> float:
    order = np.argsort(scores, kind="stable")
    sorted_labels = labels[order]
    sorted_weights = weights[order]
    bona = np.cumsum(sorted_weights * sorted_labels)
    spoof = np.cumsum(sorted_weights * (1 - sorted_labels))
    frr = bona / bona[-1]
    far = 1.0 - spoof / spoof[-1]
    index = int(np.argmin(np.abs(frr - far)))
    return float((frr[index] + far[index]) / 2.0)


def grouped_threshold_eer(
    scores: np.ndarray, labels: np.ndarray, weights: np.ndarray
) -> float:
    order = np.argsort(scores, kind="stable")
    sorted_scores = scores[order]
    sorted_labels = labels[order]
    sorted_weights = weights[order]
    end = np.r_[np.flatnonzero(sorted_scores[1:] != sorted_scores[:-1]), len(scores) - 1]
    bona = np.cumsum(sorted_weights * sorted_labels)[end]
    spoof = np.cumsum(sorted_weights * (1 - sorted_labels))[end]
    frr = bona / bona[-1]
    far = 1.0 - spoof / spoof[-1]
    index = int(np.argmin(np.abs(frr - far)))
    return float((frr[index] + far[index]) / 2.0)


@dataclass
class FastPathEER:
    """Exact registered-grid EER for weights affine in lambda."""

    cumulative_bona_0: np.ndarray
    cumulative_spoof_0: np.ndarray
    cumulative_bona_delta: np.ndarray
    cumulative_spoof_delta: np.ndarray
    total_bona_0: float
    total_spoof_0: float
    total_bona_delta: float
    total_spoof_delta: float

    @classmethod
    def build(
        cls,
        scores: np.ndarray,
        labels: np.ndarray,
        weights_0: np.ndarray,
        weights_1: np.ndarray,
    ) -> "FastPathEER":
        order = np.argsort(scores)
        lab = labels[order]
        w0 = weights_0[order]
        dw = weights_1[order] - w0
        cumulative_bona_0 = np.cumsum(w0 * lab)
        cumulative_spoof_0 = np.cumsum(w0 * (1 - lab))
        cumulative_bona_delta = np.cumsum(dw * lab)
        cumulative_spoof_delta = np.cumsum(dw * (1 - lab))
        return cls(
            cumulative_bona_0=cumulative_bona_0,
            cumulative_spoof_0=cumulative_spoof_0,
            cumulative_bona_delta=cumulative_bona_delta,
            cumulative_spoof_delta=cumulative_spoof_delta,
            total_bona_0=float(cumulative_bona_0[-1]),
            total_spoof_0=float(cumulative_spoof_0[-1]),
            total_bona_delta=float(cumulative_bona_delta[-1]),
            total_spoof_delta=float(cumulative_spoof_delta[-1]),
        )

    def evaluate(self, lam: float) -> tuple[float, int]:
        n = len(self.cumulative_bona_0)

        def values(index: int) -> tuple[float, float]:
            frr = (
                self.cumulative_bona_0[index]
                + lam * self.cumulative_bona_delta[index]
            ) / (self.total_bona_0 + lam * self.total_bona_delta)
            spoof_cdf = (
                self.cumulative_spoof_0[index]
                + lam * self.cumulative_spoof_delta[index]
            ) / (self.total_spoof_0 + lam * self.total_spoof_delta)
            far = 1.0 - spoof_cdf
            return frr - far, 0.5 * (frr + far)

        low, high = 0, n
        while low < high:
            middle = (low + high) // 2
            gap, _ = values(middle)
            if gap >= 0.0:
                high = middle
            else:
                low = middle + 1
        first_nonnegative = min(low, n - 1)
        candidates = [first_nonnegative]
        if first_nonnegative > 0:
            candidates.insert(0, first_nonnegative - 1)
        best_index = candidates[0]
        best_gap, best_eer = values(best_index)
        for index in candidates[1:]:
            gap, eer = values(index)
            if abs(gap) < abs(best_gap):
                best_index, best_gap, best_eer = index, gap, eer
        return float(best_eer), int(best_index)


def load_metadata_phases(path: Path) -> dict[str, str]:
    phases: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        fields = line.split()
        if len(fields) < 8:
            raise ValueError(f"metadata line {line_number} has fewer than 8 fields")
        if fields[1] in phases:
            raise ValueError(f"duplicate utterance in full metadata: {fields[1]}")
        phases[fields[1]] = fields[7]
    return phases


def load_scores(
    rows: list[Trial], metadata_path: Path
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    ids = [row.utterance for row in rows]
    wanted = set(ids)
    official_phases = load_metadata_phases(metadata_path)
    scores: dict[str, np.ndarray] = {}
    alignment: dict[str, object] = {}
    for system, path in SCORE_PATHS.items():
        mapping: dict[str, float] = {}
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            fields = line.split()
            if len(fields) < 2:
                raise ValueError(f"{system} score line {line_number} has fewer than 2 fields")
            utterance = fields[0]
            if utterance in mapping:
                raise ValueError(f"{system}: duplicate utterance {utterance}")
            mapping[utterance] = float(fields[1])
        missing_set = wanted - set(mapping)
        extra_set = set(mapping) - wanted
        unknown_extra = extra_set - set(official_phases)
        eval_extra = {utterance for utterance in extra_set if official_phases.get(utterance) == "eval"}
        if missing_set or unknown_extra or eval_extra:
            missing = sorted(wanted - set(mapping))[:5]
            unknown = sorted(unknown_extra)[:5]
            duplicated_eval = sorted(eval_extra)[:5]
            raise ValueError(
                f"{system}: eval identity gate; missing={missing}, "
                f"unknown_extra={unknown}, eval_extra={duplicated_eval}"
            )
        vector = np.asarray([mapping[utterance] for utterance in ids], dtype=np.float64)
        if not np.all(np.isfinite(vector)):
            raise ValueError(f"{system}: nonfinite score")
        scores[system] = vector
        alignment[system] = {
            "n_release_rows": len(mapping),
            "n_eval_rows_used": len(ids),
            "n_official_non_eval_rows_ignored": len(extra_set),
            "ignored_phase_counts": dict(
                sorted(Counter(official_phases[utterance] for utterance in extra_set).items())
            ),
        }
    return scores, alignment


def write_preoutput_contract(metadata: Path, contract_path: Path) -> dict[str, object]:
    prereg = HERE / "PREREG.md"
    frozen_hash = (HERE / "FREEZE.sha256").read_text().split()[0]
    actual_hash = sha256_file(prereg)
    if actual_hash != frozen_hash:
        raise RuntimeError(f"preregistration hash drift: {actual_hash} != {frozen_hash}")
    code_names = (
        "build_contract.py",
        "analyze.py",
        "test_exp108.py",
        "verify_results.py",
    )
    for name in code_names:
        if not (HERE / name).is_file():
            raise FileNotFoundError(f"planned code file missing before score access: {name}")
    structural = json.loads(contract_path.read_text())
    if structural["metadata"]["sha256"] != sha256_file(metadata):
        raise RuntimeError("metadata contract hash drift")
    result = {
        "kind": "pre_output_run_contract",
        "outcomes_computed_when_written": False,
        "preregistration": {"path": str(prereg), "sha256": actual_hash},
        "metadata_contract": {
            "path": str(contract_path),
            "sha256": sha256_file(contract_path),
        },
        "metadata": {"path": str(metadata), "sha256": sha256_file(metadata)},
        "score_files": {
            system: {
                "path": str(path),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for system, path in SCORE_PATHS.items()
        },
        "code": {name: sha256_file(HERE / name) for name in code_names},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }
    path = HERE / "run_contract.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def policy_outcomes(
    scores: dict[str, np.ndarray],
    labels: np.ndarray,
    policies: dict[str, np.ndarray],
) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    output: dict[str, object] = {}
    vectors: dict[str, np.ndarray] = {}
    for policy_name in POLICIES:
        weights = policies[policy_name]
        eers = np.empty(len(SYSTEMS), dtype=np.float64)
        threshold_positions: dict[str, int] = {}
        for system_index, system in enumerate(SYSTEMS):
            eer, position = full_weighted_eer(scores[system], labels, weights)
            eers[system_index] = 100.0 * eer
            threshold_positions[system] = position
        vectors[policy_name] = eers
        ranking_indices = sorted(range(len(SYSTEMS)), key=lambda i: (eers[i], i))
        best = float(eers[ranking_indices[0]])
        deltas = {
            pair_name(pair): float(eers[SYSTEMS.index(pair[0])] - eers[SYSTEMS.index(pair[1])])
            for pair in PAIRS
        }
        output[policy_name] = {
            "weight_sha256_float64_le": sha256_bytes(
                np.asarray(weights, dtype="<f8").tobytes()
            ),
            "eer_pct": {system: float(eers[i]) for i, system in enumerate(SYSTEMS)},
            "threshold_positions": threshold_positions,
            "delta_eer_pct_points": deltas,
            "signs": {name: exact_sign(value) for name, value in deltas.items()},
            "ranking": [SYSTEMS[i] for i in ranking_indices],
            "best_system": SYSTEMS[ranking_indices[0]],
            "regret_pct_points": {
                system: float(eers[i] - best) for i, system in enumerate(SYSTEMS)
            },
        }
    empirical_signs = output["B0xS0"]["signs"]
    for policy_name in POLICIES:
        signs = output[policy_name]["signs"]
        output[policy_name]["kendall_sign_changes_from_empirical"] = sum(
            signs[name] != empirical_signs[name] for name in empirical_signs
        )
        output[policy_name]["strict_reversals_from_empirical"] = sum(
            signs[name] == -empirical_signs[name]
            for name in empirical_signs
            if empirical_signs[name] != 0
        )
    return output, vectors


def pair_multiverse_summary(vectors: dict[str, np.ndarray]) -> dict[str, object]:
    output: dict[str, object] = {}
    empirical = vectors["B0xS0"]
    for left_index, right_index in (
        (SYSTEMS.index(a), SYSTEMS.index(b)) for a, b in PAIRS
    ):
        pair = (SYSTEMS[left_index], SYSTEMS[right_index])
        name = pair_name(pair)
        values = {
            policy: float(vector[left_index] - vector[right_index])
            for policy, vector in vectors.items()
        }
        empirical_sign = exact_sign(empirical[left_index] - empirical[right_index])
        signs = {policy: exact_sign(value) for policy, value in values.items()}
        min_policy = min(values, key=values.get)
        max_policy = max(values, key=values.get)
        bona_ranges = []
        for spoof_policy in ("S0", "S1", "S2", "S3"):
            selected = [values[f"{b}x{spoof_policy}"] for b in ("B0", "B1", "B2")]
            bona_ranges.append(max(selected) - min(selected))
        spoof_ranges = []
        for bona_policy in ("B0", "B1", "B2"):
            selected = [values[f"{bona_policy}x{s}"] for s in ("S0", "S1", "S2", "S3")]
            spoof_ranges.append(max(selected) - min(selected))
        unique_signs = sorted(set(signs.values()))
        output[name] = {
            "block": pair_block(pair),
            "empirical_delta": values["B0xS0"],
            "empirical_sign": empirical_sign,
            "minimum_delta": values[min_policy],
            "minimum_policy": min_policy,
            "maximum_delta": values[max_policy],
            "maximum_policy": max_policy,
            "signs_observed": unique_signs,
            "n_negative": sum(value == -1 for value in signs.values()),
            "n_zero": sum(value == 0 for value in signs.values()),
            "n_positive": sum(value == 1 for value in signs.values()),
            "registered_policy_sign_change": any(
                value != empirical_sign for value in signs.values()
            ),
            "strict_reversal": any(
                value == -empirical_sign for value in signs.values()
                if empirical_sign != 0
            ),
            "strict_dominance_under_all_policies": len(unique_signs) == 1
            and unique_signs[0] != 0,
            "maximum_bona_only_range": float(max(bona_ranges)),
            "maximum_spoof_only_range": float(max(spoof_ranges)),
            "policy_deltas": values,
        }
    return output


def path_grid_outcomes(
    scores: dict[str, np.ndarray],
    labels: np.ndarray,
    policies: dict[str, np.ndarray],
    empirical_vector: np.ndarray,
) -> dict[str, object]:
    empirical_weights = policies["B0xS0"]
    empirical_pair_signs = np.asarray(
        [
            exact_sign(empirical_vector[SYSTEMS.index(a)] - empirical_vector[SYSTEMS.index(b)])
            for a, b in PAIRS
        ],
        dtype=np.int8,
    )
    output: dict[str, object] = {}
    for policy_name in POLICIES:
        if policy_name == "B0xS0":
            continue
        endpoint = policies[policy_name]
        models = [
            FastPathEER.build(scores[system], labels, empirical_weights, endpoint)
            for system in SYSTEMS
        ]
        grid_eers = np.empty((GRID_DENOMINATOR + 1, len(SYSTEMS)), dtype=np.float64)
        for grid_index in range(GRID_DENOMINATOR + 1):
            lam = grid_index / GRID_DENOMINATOR
            for system_index, model in enumerate(models):
                grid_eers[grid_index, system_index] = 100.0 * model.evaluate(lam)[0]
        path_pairs: dict[str, object] = {}
        for pair_index, pair in enumerate(PAIRS):
            left_index, right_index = SYSTEMS.index(pair[0]), SYSTEMS.index(pair[1])
            deltas = grid_eers[:, left_index] - grid_eers[:, right_index]
            signs = np.sign(deltas).astype(np.int8)
            changed = np.flatnonzero(signs != empirical_pair_signs[pair_index])
            if len(changed) == 0:
                continue
            right_grid = int(changed[0])
            left_grid = max(0, right_grid - 1)
            lam_left = left_grid / GRID_DENOMINATOR
            lam_right = right_grid / GRID_DENOMINATOR
            right_weights = (1.0 - lam_right) * empirical_weights + lam_right * endpoint
            bona = labels == 1
            spoof = ~bona
            tv_b_endpoint = 0.5 * float(np.abs(endpoint[bona] - empirical_weights[bona]).sum())
            tv_s_endpoint = 0.5 * float(np.abs(endpoint[spoof] - empirical_weights[spoof]).sum())
            ratio = right_weights / empirical_weights
            odds_b = float(max(ratio[bona].max(), (1.0 / ratio[bona]).max()))
            odds_s = float(max(ratio[spoof].max(), (1.0 / ratio[spoof]).max()))
            left_eers = {}
            right_eers = {}
            left_positions = {}
            right_positions = {}
            for system_index, system in enumerate(SYSTEMS):
                left_value, left_position = models[system_index].evaluate(lam_left)
                right_value, right_position = models[system_index].evaluate(lam_right)
                left_eers[system] = 100.0 * left_value
                right_eers[system] = 100.0 * right_value
                left_positions[system] = left_position
                right_positions[system] = right_position
            path_pairs[pair_name(pair)] = {
                "block": pair_block(pair),
                "first_changed_grid_index": right_grid,
                "lambda_previous": lam_left,
                "lambda_witness": lam_right,
                "delta_previous": float(deltas[left_grid]),
                "delta_witness": float(deltas[right_grid]),
                "sign_previous": int(signs[left_grid]),
                "sign_witness": int(signs[right_grid]),
                "change_kind": (
                    "tie" if signs[right_grid] == 0 else "strict_reversal"
                ),
                "TV_bona": lam_right * tv_b_endpoint,
                "TV_spoof": lam_right * tv_s_endpoint,
                "r_TV": lam_right * max(tv_b_endpoint, tv_s_endpoint),
                "TV_grid_resolution": max(tv_b_endpoint, tv_s_endpoint)
                / GRID_DENOMINATOR,
                "odds_factor_bona": odds_b,
                "odds_factor_spoof": odds_s,
                "odds_factor_joint": max(odds_b, odds_s),
                "weight_sha256_float64_le": sha256_bytes(
                    np.asarray(right_weights, dtype="<f8").tobytes()
                ),
                "eer_previous": left_eers,
                "eer_witness": right_eers,
                "threshold_positions_previous": left_positions,
                "threshold_positions_witness": right_positions,
            }
        output[policy_name] = {
            "endpoint_TV_bona": 0.5
            * float(np.abs(endpoint[labels == 1] - empirical_weights[labels == 1]).sum()),
            "endpoint_TV_spoof": 0.5
            * float(np.abs(endpoint[labels == 0] - empirical_weights[labels == 0]).sum()),
            "pairs_with_sign_change": path_pairs,
        }
    return output


def tie_audit(
    scores: dict[str, np.ndarray], labels: np.ndarray, policies: dict[str, np.ndarray]
) -> dict[str, object]:
    output: dict[str, object] = {}
    failed = False
    for policy_name, weights in policies.items():
        systems: dict[str, object] = {}
        for system in SYSTEMS:
            default = 100.0 * full_weighted_eer(scores[system], labels, weights)[0]
            stable = 100.0 * stable_id_weighted_eer(scores[system], labels, weights)
            grouped = 100.0 * grouped_threshold_eer(scores[system], labels, weights)
            maximum = max(abs(default - stable), abs(default - grouped))
            failed |= maximum > 0.001
            systems[system] = {
                "default_eer": default,
                "stable_id_eer": stable,
                "grouped_threshold_eer": grouped,
                "maximum_absolute_difference_points": maximum,
            }
        output[policy_name] = systems
    return {"failed": bool(failed), "tolerance_points": 0.001, "policies": output}


def summarize_raw(
    pair_summary: dict[str, object], paths: dict[str, object]
) -> dict[str, object]:
    path_changed: dict[str, list[dict[str, object]]] = {pair_name(pair): [] for pair in PAIRS}
    for policy, entry in paths.items():
        for name, witness in entry["pairs_with_sign_change"].items():
            path_changed[name].append({"policy": policy, **witness})
    summary: dict[str, object] = {}
    for name, entry in pair_summary.items():
        witnesses = path_changed[name]
        best = min(witnesses, key=lambda item: item["r_TV"]) if witnesses else None
        summary[name] = {
            "block": entry["block"],
            "registered_policy_sign_change": entry["registered_policy_sign_change"],
            "strict_policy_reversal": entry["strict_reversal"],
            "n_paths_with_sign_change": len(witnesses),
            "best_registered_path_grid_witness": best,
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--contract", type=Path, default=HERE / "contract.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    args = parser.parse_args()

    if not args.contract.is_file():
        raise FileNotFoundError("metadata-only contract must be built before analysis")
    run_contract = write_preoutput_contract(args.metadata, args.contract)

    rows = load_trials(args.metadata)
    labels = np.asarray([1 if row.label == "bonafide" else 0 for row in rows], dtype=np.int8)
    policies = build_policy_weights(rows)
    structural = json.loads(args.contract.read_text())
    for name in POLICIES:
        validation = validate_policy(rows, name, policies[name])
        if validation["sha256_float64_le"] != structural["policies"][name]["sha256_float64_le"]:
            raise RuntimeError(f"policy contract drift: {name}")

    scores, score_alignment = load_scores(rows, args.metadata)
    orientation = {
        system: {
            "median_bonafide": float(np.median(vector[labels == 1])),
            "median_spoof": float(np.median(vector[labels == 0])),
            "higher_is_bonafide": bool(
                np.median(vector[labels == 1]) > np.median(vector[labels == 0])
            ),
        }
        for system, vector in scores.items()
    }
    if not all(entry["higher_is_bonafide"] for entry in orientation.values()):
        raise RuntimeError("score orientation gate failed")

    policy_results, vectors = policy_outcomes(scores, labels, policies)
    empirical_check = {
        system: {
            "computed": float(vectors["B0xS0"][i]),
            "expected_rounded": EXPECTED_EMPIRICAL_EER[system],
            "absolute_difference": abs(
                float(vectors["B0xS0"][i]) - EXPECTED_EMPIRICAL_EER[system]
            ),
        }
        for i, system in enumerate(SYSTEMS)
    }
    if any(entry["absolute_difference"] > 0.001 for entry in empirical_check.values()):
        raise RuntimeError("empirical pooled-EER reproduction gate failed")

    pair_summary = pair_multiverse_summary(vectors)
    paths = path_grid_outcomes(scores, labels, policies, vectors["B0xS0"])
    ties = tie_audit(scores, labels, policies)

    results = {
        "experiment": "EXP-108",
        "scientific_object": "deterministic fixed-benchmark composition robustness",
        "not_confidence_intervals": True,
        "run_contract_sha256": sha256_file(HERE / "run_contract.json"),
        "run_contract": run_contract,
        "systems": list(SYSTEMS),
        "pairs": [pair_name(pair) for pair in PAIRS],
        "pair_blocks": {pair_name(pair): pair_block(pair) for pair in PAIRS},
        "orientation": orientation,
        "score_alignment": score_alignment,
        "empirical_reproduction": empirical_check,
        "tie_audit": ties,
        "policies": policy_results,
        "pair_multiverse": pair_summary,
        "path_grid": {
            "denominator": GRID_DENOMINATOR,
            "n_points": GRID_DENOMINATOR + 1,
            "paths": paths,
        },
        "pair_path_summary": summarize_raw(pair_summary, paths),
        "secondary_arbitrary_source_task_search": {
            "status": "not_run_in_primary_pass",
            "authorized_role": "witness_upper_bound_only",
            "affects_primary_reading": False,
        },
        "qualitative_classification": None,
        "classification_authorized_only_after_independent_verification": True,
    }
    args.out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"wrote raw outcomes {args.out}; no qualitative classification emitted")


if __name__ == "__main__":
    main()
