#!/usr/bin/env python3
"""EXP-108 secondary v2 multi-backend constructive witness search."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import platform

import numpy as np
import scipy
from scipy.optimize import NonlinearConstraint, differential_evolution, minimize
from scipy.stats import qmc

from analyze import SYSTEMS, PAIRS, load_scores, pair_name
from build_contract import DEFAULT_METADATA, load_trials, sha256_file, spoof_stratum


HERE = Path(__file__).resolve().parent
PREREG = HERE / "SECONDARY-V2-PREREG.md"
DE_SEED = 20260828
SOBOL_SEED = 20260829
SOBOL_POWER = 18
TOP_K = 32
GRID_DENOMINATOR = 10_000
MAX_CONSENSUS_STEPS = 100
BONA_GROUPS = ("asvspoof", "vcc2018", "vcc2020")
SPOOF_GROUPS = (
    "asvspoof",
    "vcc2018/HUB",
    "vcc2018/SPO",
    "vcc2020/Task1",
    "vcc2020/Task2",
)


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sign(value: float) -> int:
    return int(np.sign(value))


def softmax_free(values: np.ndarray) -> np.ndarray:
    augmented = np.r_[values, 0.0]
    shifted = augmented - augmented.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


def decode(logits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return softmax_free(logits[:2]), softmax_free(logits[2:])


def distances(qb: np.ndarray, qs: np.ndarray, pb: np.ndarray, ps: np.ndarray) -> tuple[float, float]:
    tv = max(0.5 * float(np.abs(qb - pb).sum()), 0.5 * float(np.abs(qs - ps).sum()))
    ratio = np.r_[qb / pb, qs / ps]
    odds = float(max(ratio.max(), (1.0 / ratio).max()))
    return tv, odds


def structure(rows):
    labels = np.asarray([1 if row.label == "bonafide" else 0 for row in rows], dtype=np.int8)
    bona_lookup = {group: index for index, group in enumerate(BONA_GROUPS)}
    spoof_lookup = {group: index for index, group in enumerate(SPOOF_GROUPS)}
    bona_index = np.full(len(rows), -1, dtype=np.int8)
    spoof_index = np.full(len(rows), -1, dtype=np.int8)
    for index, row in enumerate(rows):
        if row.label == "bonafide":
            bona_index[index] = bona_lookup[row.source]
        else:
            spoof_index[index] = spoof_lookup[spoof_stratum(row)]
    pb = np.bincount(bona_index[labels == 1], minlength=3).astype(float)
    ps = np.bincount(spoof_index[labels == 0], minlength=5).astype(float)
    pb /= pb.sum()
    ps /= ps.sum()
    return labels, bona_index, spoof_index, pb, ps


class CountCanonicalEER:
    def __init__(self, scores, labels, bona_index, spoof_index):
        order = np.argsort(scores)
        lab = labels[order]
        bidx = bona_index[order]
        sidx = spoof_index[order]
        self.bona_counts = np.empty((3, len(scores)), dtype=np.int32)
        self.spoof_counts = np.empty((5, len(scores)), dtype=np.int32)
        self.bona_totals = np.empty(3, dtype=np.int64)
        self.spoof_totals = np.empty(5, dtype=np.int64)
        for group in range(3):
            indicator = ((lab == 1) & (bidx == group)).astype(np.int32)
            self.bona_counts[group] = np.cumsum(indicator, dtype=np.int32)
            self.bona_totals[group] = int(indicator.sum())
        for group in range(5):
            indicator = ((lab == 0) & (sidx == group)).astype(np.int32)
            self.spoof_counts[group] = np.cumsum(indicator, dtype=np.int32)
            self.spoof_totals[group] = int(indicator.sum())

    def at(self, qb, qs):
        lo, hi = 0, self.bona_counts.shape[1]

        def values(index):
            frr = float((self.bona_counts[:, index] / self.bona_totals) @ qb)
            spoof_cdf = float((self.spoof_counts[:, index] / self.spoof_totals) @ qs)
            far = 1.0 - spoof_cdf
            return frr - far, 0.5 * (frr + far)

        while lo < hi:
            middle = (lo + hi) // 2
            gap, _ = values(middle)
            if gap < 0:
                lo = middle + 1
            else:
                hi = middle
        upper = min(lo, self.bona_counts.shape[1] - 1)
        candidates = [upper - 1, upper] if upper else [upper]
        selected = candidates[0]
        best_gap, best_eer = values(selected)
        for candidate in candidates[1:]:
            candidate_gap, candidate_eer = values(candidate)
            if abs(candidate_gap) < abs(best_gap):
                selected, best_gap, best_eer = candidate, candidate_gap, candidate_eer
        return float(best_eer), int(selected)


class MaterializedEER:
    def __init__(self, scores, labels, bona_index, spoof_index):
        self.labels = labels
        self.bona_index = bona_index
        self.spoof_index = spoof_index
        self.bona_totals = np.bincount(bona_index[labels == 1], minlength=3)
        self.spoof_totals = np.bincount(spoof_index[labels == 0], minlength=5)
        self.default_order = np.argsort(scores)
        stable_order = np.argsort(scores, kind="stable")
        stable_scores = scores[stable_order]
        self.stable_order = stable_order
        self.tie_ends = np.r_[
            np.flatnonzero(stable_scores[1:] != stable_scores[:-1]), len(scores) - 1
        ]

    def weights(self, qb, qs):
        out = np.empty(len(self.labels), dtype=np.float64)
        bona = self.labels == 1
        spoof = ~bona
        out[bona] = qb[self.bona_index[bona]] / self.bona_totals[self.bona_index[bona]]
        out[spoof] = qs[self.spoof_index[spoof]] / self.spoof_totals[self.spoof_index[spoof]]
        return out

    def _evaluate_order(self, weights, order, ends=None):
        lab = self.labels[order]
        w = weights[order]
        bona = np.cumsum(w * lab)
        spoof = np.cumsum(w * (1 - lab))
        if ends is not None:
            bona = bona[ends]
            spoof = spoof[ends]
        frr = bona / bona[-1]
        far = 1.0 - spoof / spoof[-1]
        index = int(np.argmin(np.abs(frr - far)))
        return float((frr[index] + far[index]) / 2.0), index

    def direct(self, qb, qs):
        return self._evaluate_order(self.weights(qb, qs), self.default_order)

    def tie_safe(self, qb, qs):
        return self._evaluate_order(
            self.weights(qb, qs), self.stable_order, self.tie_ends
        )


def canonical_eers(models, qb, qs):
    return np.asarray([100 * models[system].at(qb, qs)[0] for system in SYSTEMS])


def canonical_delta(models, pair, qb, qs):
    return 100 * (models[pair[0]].at(qb, qs)[0] - models[pair[1]].at(qb, qs)[0])


def write_contract():
    primary = json.loads((HERE / "run_contract.json").read_text())
    files = (
        "search_witnesses_v2.py",
        "verify_secondary_v2.py",
        "test_secondary_v2.py",
    )
    for filename in files:
        if not (HERE / filename).is_file():
            raise FileNotFoundError(filename)
    result = {
        "kind": "EXP-108-secondary-v2-pre-output-contract",
        "outcomes_computed_when_written": False,
        "v2_preregistration": {"path": str(PREREG), "sha256": sha256_file(PREREG)},
        "primary_results_sha256": sha256_file(HERE / "results.json"),
        "primary_verification_sha256": sha256_file(HERE / "verification.json"),
        "metadata": primary["metadata"],
        "score_files": primary["score_files"],
        "code": {filename: sha256_file(HERE / filename) for filename in files},
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "constants": {
            "sobol_seed": SOBOL_SEED,
            "sobol_power": SOBOL_POWER,
            "top_k": TOP_K,
            "de_seed": DE_SEED,
            "grid_denominator": GRID_DENOMINATOR,
            "max_consensus_steps": MAX_CONSENSUS_STEPS,
        },
    }
    path = HERE / "secondary_v2_contract.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def consensus_direction(
    pair,
    empirical_sign,
    qb_endpoint,
    qs_endpoint,
    pb,
    ps,
    canonical,
    materialized,
):
    coarse = None
    previous = 0.0
    for step in range(1, 101):
        lam = step / 100
        qb = (1 - lam) * pb + lam * qb_endpoint
        qs = (1 - lam) * ps + lam * qs_endpoint
        if sign(canonical_delta(canonical, pair, qb, qs)) != empirical_sign:
            coarse = (previous, lam)
            break
        previous = lam
    if coarse is None:
        return {"accepted": False, "reason": "no_canonical_coarse_flip"}
    low, high = coarse
    for _ in range(60):
        middle = 0.5 * (low + high)
        qb = (1 - middle) * pb + middle * qb_endpoint
        qs = (1 - middle) * ps + middle * qs_endpoint
        if sign(canonical_delta(canonical, pair, qb, qs)) != empirical_sign:
            high = middle
        else:
            low = middle
    start_index = min(GRID_DENOMINATOR, int(math.ceil(high * GRID_DENOMINATOR - 1e-12)))
    for extra in range(MAX_CONSENSUS_STEPS + 1):
        grid_index = start_index + extra
        if grid_index > GRID_DENOMINATOR:
            break
        lam = grid_index / GRID_DENOMINATOR
        qb = (1 - lam) * pb + lam * qb_endpoint
        qs = (1 - lam) * ps + lam * qs_endpoint
        deltas = {
            "count_canonical": canonical_delta(canonical, pair, qb, qs),
            "direct_per_trial": 100
            * (
                materialized[pair[0]].direct(qb, qs)[0]
                - materialized[pair[1]].direct(qb, qs)[0]
            ),
            "tie_safe_threshold": 100
            * (
                materialized[pair[0]].tie_safe(qb, qs)[0]
                - materialized[pair[1]].tie_safe(qb, qs)[0]
            ),
        }
        signs = {backend: sign(value) for backend, value in deltas.items()}
        if all(value != 0 and value != empirical_sign for value in signs.values()):
            trial_weights = materialized[pair[0]].weights(qb, qs)
            tv, odds = distances(qb, qs, pb, ps)
            return {
                "accepted": True,
                "lambda": lam,
                "grid_index": grid_index,
                "extra_consensus_steps": extra,
                "q_bona": qb.tolist(),
                "q_spoof": qs.tolist(),
                "r_TV": tv,
                "odds_factor": odds,
                "deltas": deltas,
                "signs": signs,
                "group_mass_sha256_float64_le": sha_bytes(
                    np.asarray(np.r_[qb, qs], dtype="<f8").tobytes()
                ),
                "trial_mass_sha256_float64_le": sha_bytes(
                    np.asarray(trial_weights, dtype="<f8").tobytes()
                ),
            }
    return {
        "accepted": False,
        "reason": "no_three_backend_consensus_within_100_grid_steps",
        "canonical_boundary_grid_index": start_index,
    }


def differential_direction(models, pair, empirical_sign, pb, ps, objective_index):
    def objective(z):
        qb, qs = decode(z)
        return distances(qb, qs, pb, ps)[objective_index]

    def constraint_value(z):
        qb, qs = decode(z)
        return -empirical_sign * canonical_delta(models, pair, qb, qs)

    constraint = NonlinearConstraint(constraint_value, 0.0, np.inf)
    de = differential_evolution(
        objective,
        bounds=[(-16.0, 16.0)] * 6,
        constraints=(constraint,),
        seed=DE_SEED,
        popsize=12,
        maxiter=240,
        tol=1e-8,
        polish=False,
        updating="immediate",
        workers=1,
    )
    slsqp = minimize(
        objective,
        de.x,
        method="SLSQP",
        bounds=[(-16.0, 16.0)] * 6,
        constraints=({"type": "ineq", "fun": constraint_value},),
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    candidates = []
    if constraint_value(de.x) >= 0:
        candidates.append((objective(de.x), "DE", de.x))
    if slsqp.success and constraint_value(slsqp.x) >= 0:
        candidates.append((objective(slsqp.x), "SLSQP", slsqp.x))
    if not candidates:
        return {
            "retained": False,
            "reason": "no_canonical_feasible_endpoint",
            "de_message": str(de.message),
            "slsqp_message": str(slsqp.message),
        }
    _, selected, z = min(candidates, key=lambda item: item[0])
    qb, qs = decode(z)
    return {
        "retained": True,
        "selected": selected,
        "de_message": str(de.message),
        "slsqp_message": str(slsqp.message),
        "endpoint_q_bona": qb.tolist(),
        "endpoint_q_spoof": qs.tolist(),
        "endpoint_objectives": dict(zip(("r_TV", "odds_factor"), distances(qb, qs, pb, ps))),
        "endpoint_canonical_delta": canonical_delta(models, pair, qb, qs),
    }


def main():
    preoutput = write_contract()
    rows = load_trials(DEFAULT_METADATA)
    labels, bidx, sidx, pb, ps = structure(rows)
    scores, alignment = load_scores(rows, DEFAULT_METADATA)
    canonical = {
        system: CountCanonicalEER(scores[system], labels, bidx, sidx) for system in SYSTEMS
    }
    materialized = {
        system: MaterializedEER(scores[system], labels, bidx, sidx) for system in SYSTEMS
    }
    empirical = canonical_eers(canonical, pb, ps)
    empirical_signs = {
        pair_name(pair): sign(
            empirical[SYSTEMS.index(pair[0])] - empirical[SYSTEMS.index(pair[1])]
        )
        for pair in PAIRS
    }

    sampler = qmc.Sobol(d=8, scramble=True, seed=SOBOL_SEED)
    uniform = np.clip(sampler.random_base2(SOBOL_POWER), 1e-15, 1 - 1e-15)
    exponential = -np.log(uniform)
    qb_all = exponential[:, :3]
    qs_all = exponential[:, 3:]
    qb_all /= qb_all.sum(axis=1, keepdims=True)
    qs_all /= qs_all.sum(axis=1, keepdims=True)
    tv_all = np.maximum(
        0.5 * np.abs(qb_all - pb).sum(axis=1), 0.5 * np.abs(qs_all - ps).sum(axis=1)
    )
    ratio = np.c_[qb_all / pb, qs_all / ps]
    odds_all = np.maximum(ratio.max(axis=1), (1.0 / ratio).max(axis=1))
    best = {
        pair_name(pair): {"r_TV": [], "odds_factor": []} for pair in PAIRS
    }
    batch_size = 2048
    for start in range(0, len(qb_all), batch_size):
        stop = min(start + batch_size, len(qb_all))
        batch_eers = np.empty((stop - start, len(SYSTEMS)), dtype=np.float64)
        for local, global_index in enumerate(range(start, stop)):
            batch_eers[local] = canonical_eers(canonical, qb_all[global_index], qs_all[global_index])
        for pair in PAIRS:
            key = pair_name(pair)
            delta = batch_eers[:, SYSTEMS.index(pair[0])] - batch_eers[:, SYSTEMS.index(pair[1])]
            feasible_local = np.flatnonzero(np.sign(delta).astype(int) != empirical_signs[key])
            if not len(feasible_local):
                continue
            global_indices = start + feasible_local
            for metric_name, values in (("r_TV", tv_all), ("odds_factor", odds_all)):
                if len(global_indices) > TOP_K:
                    selected_local = np.argpartition(values[global_indices], TOP_K - 1)[:TOP_K]
                    candidates = global_indices[selected_local]
                else:
                    candidates = global_indices
                merged = best[key][metric_name] + [
                    (float(values[index]), int(index)) for index in candidates
                ]
                merged.sort(key=lambda item: (item[0], item[1]))
                best[key][metric_name] = merged[:TOP_K]

    pair_output = {}
    for pair in PAIRS:
        key = pair_name(pair)
        entry = {"empirical_sign": empirical_signs[key], "objectives": {}}
        for objective_index, objective_name in enumerate(("r_TV", "odds_factor")):
            sobol_directions = []
            for rank, (endpoint_objective, index) in enumerate(best[key][objective_name]):
                consensus = consensus_direction(
                    pair,
                    empirical_signs[key],
                    qb_all[index],
                    qs_all[index],
                    pb,
                    ps,
                    canonical,
                    materialized,
                )
                sobol_directions.append(
                    {
                        "rank": rank + 1,
                        "sobol_index": index,
                        "endpoint_objective": endpoint_objective,
                        "endpoint_q_bona": qb_all[index].tolist(),
                        "endpoint_q_spoof": qs_all[index].tolist(),
                        "consensus": consensus,
                    }
                )
            differential = differential_direction(
                canonical,
                pair,
                empirical_signs[key],
                pb,
                ps,
                objective_index,
            )
            if differential.get("retained"):
                differential["consensus"] = consensus_direction(
                    pair,
                    empirical_signs[key],
                    np.asarray(differential["endpoint_q_bona"]),
                    np.asarray(differential["endpoint_q_spoof"]),
                    pb,
                    ps,
                    canonical,
                    materialized,
                )
            accepted_sobol = [
                direction for direction in sobol_directions if direction["consensus"].get("accepted")
            ]
            accepted_differential = (
                differential.get("retained")
                and differential.get("consensus", {}).get("accepted")
            )
            objective_field = objective_name
            best_sobol = (
                min(
                    accepted_sobol,
                    key=lambda item: item["consensus"][objective_field],
                )
                if accepted_sobol
                else None
            )
            candidates = []
            if best_sobol:
                candidates.append(("sobol", best_sobol["consensus"]))
            if accepted_differential:
                candidates.append(("differential", differential["consensus"]))
            best_overall = (
                min(candidates, key=lambda item: item[1][objective_field]) if candidates else None
            )
            entry["objectives"][objective_name] = {
                "sobol": {
                    "n_retained": len(sobol_directions),
                    "n_consensus_accepted": len(accepted_sobol),
                    "directions": sobol_directions,
                    "best_accepted": best_sobol,
                },
                "differential": differential,
                "best_overall": (
                    {"algorithm": best_overall[0], "witness": best_overall[1]}
                    if best_overall
                    else None
                ),
                "dual_search": bool(best_sobol and accepted_differential),
                "algorithm_objective_difference": (
                    abs(
                        best_sobol["consensus"][objective_field]
                        - differential["consensus"][objective_field]
                    )
                    if best_sobol and accepted_differential
                    else None
                ),
            }
        pair_output[key] = entry

    output = {
        "experiment": "EXP-108-secondary-v2",
        "scientific_role": "constructive_upper_bounds_only",
        "changes_primary_classification": False,
        "preoutput_contract_sha256": sha256_file(HERE / "secondary_v2_contract.json"),
        "preoutput_contract": preoutput,
        "score_alignment": alignment,
        "bona_groups": list(BONA_GROUPS),
        "spoof_groups": list(SPOOF_GROUPS),
        "empirical_bona_mass": pb.tolist(),
        "empirical_spoof_mass": ps.tolist(),
        "pairs": pair_output,
    }
    path = HERE / "secondary_v2_results.json"
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print("wrote secondary_v2_results.json; primary classification unchanged")


if __name__ == "__main__":
    main()
