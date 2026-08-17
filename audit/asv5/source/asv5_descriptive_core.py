# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy==2.4.2", "numba==0.64.0"]
# ///
"""Outcome-agnostic numerical core for EXP-106 Amendments 5--6.

This module contains no real paths and performs no I/O on import.  Its output
is a fixed-roster perturbation description, not population inference.
"""

from __future__ import annotations

import hashlib
from itertools import combinations
from typing import Mapping, Sequence

import numpy as np
from numba import njit


SYSTEM_ORDER = ("SSL-AASIST", "AASIST", "XLS-R+SLS", "XLSR-Mamba")
B_FROZEN = 5000
SEED_FROZEN = 20260826
ARM_NAMESPACES = {
    "trial_iid": "exp106-amendment5/class-stratified-trial-iid",
    "speaker_attack": "exp106-amendment5/role-speaker-attack",
    "speaker_only": "exp106-amendment5/role-speaker-only",
}


class DescriptiveContractError(ValueError):
    """A frozen Amendment-6 numerical condition was violated."""


def pair_order(system_order: Sequence[str] = SYSTEM_ORDER) -> tuple[tuple[str, str], ...]:
    names = tuple(system_order)
    if len(names) != len(set(names)) or len(names) < 2:
        raise DescriptiveContractError("system order must contain unique systems")
    return tuple(combinations(names, 2))


def namespace_word(namespace: str) -> int:
    if not isinstance(namespace, str) or not namespace:
        raise DescriptiveContractError("RNG namespace must be a nonempty string")
    return int.from_bytes(hashlib.sha256(namespace.encode("utf-8")).digest()[:4], "little")


def replicate_rng(arm: str, replicate: int, seed: int = SEED_FROZEN) -> np.random.Generator:
    if arm not in ARM_NAMESPACES:
        raise DescriptiveContractError(f"unknown perturbation arm {arm!r}")
    if replicate < 0:
        raise DescriptiveContractError("replicate index must be nonnegative")
    return np.random.default_rng(
        np.random.SeedSequence([int(seed), namespace_word(ARM_NAMESPACES[arm]), int(replicate)])
    )


def weighted_eer_reference(
    order: np.ndarray, labels: np.ndarray, weights: np.ndarray
) -> float:
    """Literal sealed EXP-101 weighted-EER functional."""

    order = np.asarray(order)
    labels = np.asarray(labels, dtype=np.int8)
    weights = np.asarray(weights, dtype=np.float64)
    if order.ndim != 1 or labels.ndim != 1 or weights.ndim != 1:
        raise DescriptiveContractError("weighted EER inputs must be vectors")
    if len(order) != len(labels) or len(labels) != len(weights):
        raise DescriptiveContractError("weighted EER vector lengths differ")
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise DescriptiveContractError("weighted EER requires finite nonnegative weights")
    lab = labels[order]
    weight = weights[order]
    cumulative_bona = np.cumsum(weight * lab)
    cumulative_spoof = np.cumsum(weight * (1 - lab))
    total_bona = cumulative_bona[-1]
    total_spoof = cumulative_spoof[-1]
    if total_bona <= 0 or total_spoof <= 0:
        raise DescriptiveContractError("perturbation draw lost one class")
    frr = cumulative_bona / total_bona
    far = 1.0 - cumulative_spoof / total_spoof
    index = int(np.argmin(np.abs(frr - far)))
    return float((frr[index] + far[index]) / 2.0)


@njit(cache=True)
def _weighted_eers_scan(
    orders: np.ndarray, labels: np.ndarray, weights: np.ndarray
) -> np.ndarray:
    """Allocation-light exact scan with the same first-argmin convention."""

    n_systems, n_trials = orders.shape
    total_bona = 0.0
    total_spoof = 0.0
    for row in range(n_trials):
        if labels[row] == 1:
            total_bona += weights[row]
        else:
            total_spoof += weights[row]
    output = np.empty(n_systems, dtype=np.float64)
    if total_bona <= 0.0 or total_spoof <= 0.0:
        for system in range(n_systems):
            output[system] = np.nan
        return output
    for system in range(n_systems):
        cumulative_bona = 0.0
        cumulative_spoof = 0.0
        best_gap = np.inf
        best_eer = np.nan
        for rank in range(n_trials):
            row = orders[system, rank]
            if labels[row] == 1:
                cumulative_bona += weights[row]
            else:
                cumulative_spoof += weights[row]
            frr = cumulative_bona / total_bona
            far = 1.0 - cumulative_spoof / total_spoof
            gap = abs(frr - far)
            if gap < best_gap:
                best_gap = gap
                best_eer = 0.5 * (frr + far)
        output[system] = best_eer
    return output


def weighted_eers(
    orders: np.ndarray, labels: np.ndarray, weights: np.ndarray
) -> np.ndarray:
    orders = np.asarray(orders, dtype=np.int64)
    labels = np.asarray(labels, dtype=np.int8)
    weights = np.asarray(weights, dtype=np.float64)
    if orders.ndim != 2 or labels.ndim != 1 or weights.ndim != 1:
        raise DescriptiveContractError("malformed weighted-EER array")
    if orders.shape[1] != len(labels) or len(weights) != len(labels):
        raise DescriptiveContractError("weighted-EER shapes differ")
    if set(np.unique(labels).tolist()) != {0, 1}:
        raise DescriptiveContractError("both binary classes are required")
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise DescriptiveContractError("weights must be finite and nonnegative")
    result = _weighted_eers_scan(orders, labels, weights)
    if not np.isfinite(result).all():
        raise DescriptiveContractError("perturbation draw lost one class")
    return result


def validate_design_indices(
    labels: np.ndarray,
    target_index: np.ndarray,
    non_target_index: np.ndarray,
    attack_index: np.ndarray,
) -> tuple[int, int, int]:
    labels = np.asarray(labels, dtype=np.int8)
    target = np.asarray(target_index, dtype=np.int64)
    non_target = np.asarray(non_target_index, dtype=np.int64)
    attack = np.asarray(attack_index, dtype=np.int64)
    if not (labels.ndim == target.ndim == non_target.ndim == attack.ndim == 1):
        raise DescriptiveContractError("design indices must be vectors")
    if len({len(labels), len(target), len(non_target), len(attack)}) != 1:
        raise DescriptiveContractError("design-index lengths differ")
    bona = labels == 1
    spoof = labels == 0
    if set(np.unique(labels).tolist()) != {0, 1}:
        raise DescriptiveContractError("both binary classes are required")
    if (target[spoof] < 0).any() or (non_target[spoof] >= 0).any() or (attack[spoof] < 0).any():
        raise DescriptiveContractError("spoof rows must be target speakers with attacks")
    if (attack[bona] >= 0).any():
        raise DescriptiveContractError("bona-fide rows cannot carry attack indices")
    if ((target[bona] >= 0) == (non_target[bona] >= 0)).any():
        raise DescriptiveContractError("each bona-fide row must have exactly one speaker role")
    n_target = int(target.max()) + 1
    n_non_target = int(non_target.max()) + 1
    n_attack = int(attack.max()) + 1
    if n_target <= 0 or n_non_target <= 0 or n_attack <= 0:
        raise DescriptiveContractError("all role/attack dimensions must be nonempty")
    if set(target[target >= 0].tolist()) != set(range(n_target)):
        raise DescriptiveContractError("target indices are not contiguous")
    if set(non_target[non_target >= 0].tolist()) != set(range(n_non_target)):
        raise DescriptiveContractError("non-target indices are not contiguous")
    if set(attack[attack >= 0].tolist()) != set(range(n_attack)):
        raise DescriptiveContractError("attack indices are not contiguous")
    for index in range(n_target):
        rows = target == index
        if not (np.any(rows & bona) and np.any(rows & spoof)):
            raise DescriptiveContractError("every target speaker must occur in both classes")
    return n_target, n_non_target, n_attack


def draw_weights(
    arm: str,
    replicate: int,
    labels: np.ndarray,
    target_index: np.ndarray,
    non_target_index: np.ndarray,
    attack_index: np.ndarray,
    *,
    seed: int = SEED_FROZEN,
) -> np.ndarray:
    labels = np.asarray(labels, dtype=np.int8)
    target = np.asarray(target_index, dtype=np.int64)
    non_target = np.asarray(non_target_index, dtype=np.int64)
    attack = np.asarray(attack_index, dtype=np.int64)
    n_target, n_non_target, n_attack = validate_design_indices(
        labels, target, non_target, attack
    )
    rng = replicate_rng(arm, replicate, seed)
    weights = np.zeros(len(labels), dtype=np.float64)
    bona_rows = np.flatnonzero(labels == 1)
    spoof_rows = np.flatnonzero(labels == 0)
    if arm == "trial_iid":
        bona_draw = rng.integers(0, len(bona_rows), size=len(bona_rows))
        spoof_draw = rng.integers(0, len(spoof_rows), size=len(spoof_rows))
        bona_counts = np.bincount(bona_draw, minlength=len(bona_rows))
        spoof_counts = np.bincount(spoof_draw, minlength=len(spoof_rows))
        weights[bona_rows] = bona_counts
        weights[spoof_rows] = spoof_counts
        if weights[bona_rows].sum() != len(bona_rows):
            raise DescriptiveContractError("trial-iid bona-fide total changed")
        if weights[spoof_rows].sum() != len(spoof_rows):
            raise DescriptiveContractError("trial-iid spoof total changed")
        return weights
    if arm not in {"speaker_attack", "speaker_only"}:
        raise DescriptiveContractError(f"unknown perturbation arm {arm!r}")
    target_draw = rng.integers(0, n_target, size=n_target)
    non_target_draw = rng.integers(0, n_non_target, size=n_non_target)
    target_counts = np.bincount(target_draw, minlength=n_target)
    non_target_counts = np.bincount(non_target_draw, minlength=n_non_target)
    if target_counts.sum() != n_target or non_target_counts.sum() != n_non_target:
        raise DescriptiveContractError("speaker multinomial total changed")
    is_target = target >= 0
    is_non_target = non_target >= 0
    weights[is_target] = target_counts[target[is_target]]
    weights[is_non_target] = non_target_counts[non_target[is_non_target]]
    if arm == "speaker_attack":
        attack_draw = rng.integers(0, n_attack, size=n_attack)
        attack_counts = np.bincount(attack_draw, minlength=n_attack)
        if attack_counts.sum() != n_attack:
            raise DescriptiveContractError("attack multinomial total changed")
        weights[spoof_rows] *= attack_counts[attack[spoof_rows]]
    return weights


def point_eers(orders: np.ndarray, labels: np.ndarray) -> np.ndarray:
    return 100.0 * weighted_eers(
        orders, labels, np.ones(len(labels), dtype=np.float64)
    )


def one_replicate(
    arm: str,
    replicate: int,
    orders: np.ndarray,
    labels: np.ndarray,
    target_index: np.ndarray,
    non_target_index: np.ndarray,
    attack_index: np.ndarray,
    *,
    seed: int = SEED_FROZEN,
) -> np.ndarray:
    weights = draw_weights(
        arm,
        replicate,
        labels,
        target_index,
        non_target_index,
        attack_index,
        seed=seed,
    )
    return 100.0 * weighted_eers(orders, labels, weights)


def summarize_arm(
    replicates: np.ndarray,
    point: np.ndarray,
    *,
    arm: str,
    system_order: Sequence[str] = SYSTEM_ORDER,
    seed: int = SEED_FROZEN,
) -> dict[str, object]:
    names = tuple(system_order)
    pairs = pair_order(names)
    reps = np.asarray(replicates, dtype=np.float64)
    point = np.asarray(point, dtype=np.float64)
    if reps.ndim != 2 or reps.shape[1] != len(names) or len(reps) < 2:
        raise DescriptiveContractError("replicate matrix has the wrong shape")
    if point.shape != (len(names),):
        raise DescriptiveContractError("point vector has the wrong shape")
    if not np.isfinite(reps).all() or not np.isfinite(point).all():
        raise DescriptiveContractError("summary inputs must be finite")
    columns = np.column_stack(
        [reps[:, names.index(a)] - reps[:, names.index(b)] for a, b in pairs]
    )
    hats = np.asarray([point[names.index(a)] - point[names.index(b)] for a, b in pairs])
    scale = columns.std(axis=0, ddof=1)
    if not np.isfinite(scale).all() or (scale <= 0).any():
        raise DescriptiveContractError("nonpositive or nonfinite pairwise bootstrap SD")
    centered = np.abs(columns - columns.mean(axis=0)) / scale
    critical = float(np.percentile(centered.max(axis=1), 95.0, method="linear"))
    rows: dict[str, object] = {}
    for index, (a, b) in enumerate(pairs):
        pointwise = np.percentile(
            columns[:, index], [2.5, 97.5], method="linear"
        )
        simultaneous = np.asarray(
            [hats[index] - critical * scale[index], hats[index] + critical * scale[index]]
        )
        key = f"{a} vs {b}"
        rows[key] = {
            "delta_eer_pts": float(hats[index]),
            "bootstrap_sd_pts": float(scale[index]),
            "pointwise_percentile": [float(value) for value in pointwise],
            "simultaneous_numeric_band": [float(value) for value in simultaneous],
            "numeric_band_excludes_zero": bool(
                not (simultaneous[0] <= 0.0 <= simultaneous[1])
            ),
        }
    return {
        "arm": arm,
        "namespace": ARM_NAMESPACES[arm],
        "B": int(len(reps)),
        "seed": int(seed),
        "max_t_center": "bootstrap-column-mean",
        "percentile_method": "linear",
        "max_t_critical_value": critical,
        "pairs": rows,
    }


def combine_summaries(
    iid: Mapping[str, object],
    primary: Mapping[str, object],
    speaker_only: Mapping[str, object],
) -> dict[str, object]:
    iid_pairs = iid.get("pairs")
    primary_pairs = primary.get("pairs")
    sensitivity_pairs = speaker_only.get("pairs")
    if not all(isinstance(value, Mapping) for value in (iid_pairs, primary_pairs, sensitivity_pairs)):
        raise DescriptiveContractError("arm summaries lack pair mappings")
    keys = tuple(f"{a} vs {b}" for a, b in pair_order())
    if set(iid_pairs) != set(keys) or set(primary_pairs) != set(keys) or set(sensitivity_pairs) != set(keys):
        raise DescriptiveContractError("arm summaries use different pair families")
    ratios: dict[str, float] = {}
    iid_only: list[str] = []
    primary_only: list[str] = []
    for key in keys:
        iid_row = iid_pairs[key]
        primary_row = primary_pairs[key]
        iid_band = iid_row["simultaneous_numeric_band"]
        primary_band = primary_row["simultaneous_numeric_band"]
        iid_width = float(iid_band[1]) - float(iid_band[0])
        primary_width = float(primary_band[1]) - float(primary_band[0])
        if not np.isfinite([iid_width, primary_width]).all() or iid_width <= 0:
            raise DescriptiveContractError("invalid simultaneous-band width")
        ratios[key] = primary_width / iid_width
        iid_flag = bool(iid_row["numeric_band_excludes_zero"])
        primary_flag = bool(primary_row["numeric_band_excludes_zero"])
        if iid_flag and not primary_flag:
            iid_only.append(key)
        if primary_flag and not iid_flag:
            primary_only.append(key)
    median_ratio = float(np.median(np.fromiter(ratios.values(), dtype=np.float64)))
    criterion_a = bool(iid_only)
    criterion_b = bool(median_ratio >= 2.0)
    return {
        "primary_over_iid_simultaneous_width_ratio": ratios,
        "median_primary_over_iid_width_ratio": median_ratio,
        "iid_zero_exclusions_absent_under_primary": iid_only,
        "primary_zero_exclusions_absent_under_iid": primary_only,
        "registered_descriptive_summaries": {
            "A_iid_exclusion_absent_under_speaker_attack": criterion_a,
            "B_median_width_ratio_at_least_2": criterion_b,
            "n_true": int(criterion_a) + int(criterion_b),
        },
    }

