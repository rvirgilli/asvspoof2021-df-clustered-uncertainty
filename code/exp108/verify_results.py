#!/usr/bin/env python3
"""Independent reconstruction and verification of EXP-108 raw outcomes.

This module intentionally imports neither build_contract.py nor analyze.py.
"""

from __future__ import annotations

from collections import defaultdict
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
SYSTEMS = (
    "XLSR-Mamba",
    "XLS-R+SLS",
    "XLSR-Conformer",
    "SSL-AASIST",
    "RawNet2",
    "LFCC-LCNN",
    "LFCC-GMM",
    "CQCC-GMM",
)
POLICIES = tuple(f"B{b}xS{s}" for b in range(3) for s in range(4))
PAIRS = tuple((SYSTEMS[i], SYSTEMS[j]) for i in range(8) for j in range(i + 1, 8))


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_weights(weights: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(weights, dtype="<f8").tobytes()).hexdigest()


def name(pair: tuple[str, str]) -> str:
    return f"{pair[0]} vs {pair[1]}"


def close(left: float, right: float, tol: float = 1e-10) -> None:
    if not np.isfinite(left) or not np.isfinite(right) or abs(left - right) > tol:
        raise AssertionError(f"numeric mismatch: {left} vs {right} (tol {tol})")


def read_metadata(path: Path) -> list[dict[str, str]]:
    rows = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        field = line.split()
        if len(field) < 10:
            raise AssertionError(f"short metadata row {line_number}")
        if field[7] == "eval":
            rows.append(
                {
                    "speaker": field[0],
                    "id": field[1],
                    "source": field[3],
                    "attack": field[4],
                    "label": field[5],
                    "family": field[8],
                    "task": field[9],
                }
            )
    rows.sort(key=lambda row: row["id"])
    if len({row["id"] for row in rows}) != len(rows):
        raise AssertionError("duplicate metadata ID")
    return rows


def read_all_phases(path: Path) -> dict[str, str]:
    phases = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split()
        if len(fields) < 8:
            raise AssertionError(f"short full metadata row {line_number}")
        if fields[1] in phases:
            raise AssertionError(f"duplicate full metadata ID: {fields[1]}")
        phases[fields[1]] = fields[7]
    return phases


def stratum(row: dict[str, str]) -> str:
    return "asvspoof" if row["source"] == "asvspoof" else f"{row['source']}/{row['task']}"


def hierarchy_mass(
    rows: list[dict[str, str]], indices: list[int], key_functions: tuple
) -> np.ndarray:
    mass = np.zeros(len(rows), dtype=np.float64)
    stack = [(indices, 0, 1.0)]
    while stack:
        members, depth, parent_mass = stack.pop()
        if depth == len(key_functions):
            mass[np.asarray(members)] = parent_mass / len(members)
            continue
        groups: dict[str, list[int]] = defaultdict(list)
        for index in members:
            groups[str(key_functions[depth](rows[index]))].append(index)
        child_mass = parent_mass / len(groups)
        for group_name in sorted(groups, reverse=True):
            stack.append((groups[group_name], depth + 1, child_mass))
    return mass


def reconstruct_policies(rows: list[dict[str, str]]) -> dict[str, np.ndarray]:
    bona_index = [i for i, row in enumerate(rows) if row["label"] == "bonafide"]
    spoof_index = [i for i, row in enumerate(rows) if row["label"] == "spoof"]
    b0 = np.zeros(len(rows)); b0[bona_index] = 1 / len(bona_index)
    s0 = np.zeros(len(rows)); s0[spoof_index] = 1 / len(spoof_index)
    bona = {
        "B0": b0,
        "B1": hierarchy_mass(rows, bona_index, (lambda row: row["source"],)),
        "B2": hierarchy_mass(
            rows, bona_index, (lambda row: row["source"], lambda row: row["speaker"])
        ),
    }
    spoof = {
        "S0": s0,
        "S1": hierarchy_mass(rows, spoof_index, (stratum,)),
        "S2": hierarchy_mass(
            rows,
            spoof_index,
            (stratum, lambda row: f"{row['speaker']}\x1f{row['attack']}"),
        ),
        "S3": hierarchy_mass(
            rows,
            spoof_index,
            (
                stratum,
                lambda row: row["family"],
                lambda row: row["attack"],
                lambda row: row["speaker"],
            ),
        ),
    }
    return {f"{b}x{s}": bona[b] + spoof[s] for b in bona for s in spoof}


def load_score_vectors(
    rows: list[dict[str, str]], run_contract: dict[str, object], all_phases: dict[str, str]
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    ids = [row["id"] for row in rows]
    wanted = set(ids)
    output = {}
    alignment = {}
    for system in SYSTEMS:
        entry = run_contract["score_files"][system]
        path = Path(entry["path"])
        if sha_file(path) != entry["sha256"]:
            raise AssertionError(f"score hash drift: {system}")
        mapping = {}
        for line in path.read_text().splitlines():
            fields = line.split()
            if fields[0] in mapping:
                raise AssertionError(f"duplicate score ID: {system} {fields[0]}")
            mapping[fields[0]] = float(fields[1])
        missing = wanted - set(mapping)
        extras = set(mapping) - wanted
        if missing or not extras <= set(all_phases):
            raise AssertionError(f"score ID mismatch: {system}")
        if any(all_phases[utterance] == "eval" for utterance in extras):
            raise AssertionError(f"release-only ID marked eval: {system}")
        output[system] = np.asarray([mapping[utterance] for utterance in ids])
        alignment[system] = {
            "n_release_rows": len(mapping),
            "n_eval_rows_used": len(ids),
            "n_official_non_eval_rows_ignored": len(extras),
            "ignored_phase_counts": dict(
                sorted(Counter(all_phases[utterance] for utterance in extras).items())
            ),
        }
    return output, alignment


def reference_eer(scores: np.ndarray, labels: np.ndarray, weights: np.ndarray) -> tuple[float, int]:
    order = np.argsort(scores)
    lab = labels[order]
    weight = weights[order]
    false_reject = np.cumsum(weight * lab)
    accepted_spoof_cdf = np.cumsum(weight * (1 - lab))
    false_reject /= false_reject[-1]
    accepted_spoof = 1.0 - accepted_spoof_cdf / accepted_spoof_cdf[-1]
    distance = np.abs(false_reject - accepted_spoof)
    position = int(np.flatnonzero(distance == distance.min())[0])
    return float((false_reject[position] + accepted_spoof[position]) / 2), position


class IndependentGridEER:
    def __init__(
        self,
        scores: np.ndarray,
        labels: np.ndarray,
        start_weights: np.ndarray,
        end_weights: np.ndarray,
    ) -> None:
        order = np.argsort(scores)
        lab = labels[order]
        start = start_weights[order]
        change = end_weights[order] - start
        self.b0 = np.cumsum(start * lab)
        self.s0 = np.cumsum(start * (1 - lab))
        self.bd = np.cumsum(change * lab)
        self.sd = np.cumsum(change * (1 - lab))
        self.tb0 = float(self.b0[-1])
        self.ts0 = float(self.s0[-1])
        self.tbd = float(self.bd[-1])
        self.tsd = float(self.sd[-1])

    def at(self, lam: float) -> tuple[float, int]:
        lo = 0
        hi = len(self.b0)
        while lo < hi:
            middle = (lo + hi) // 2
            gap = (
                (self.b0[middle] + lam * self.bd[middle])
                / (self.tb0 + lam * self.tbd)
                + (self.s0[middle] + lam * self.sd[middle])
                / (self.ts0 + lam * self.tsd)
                - 1.0
            )
            if gap < 0:
                lo = middle + 1
            else:
                hi = middle
        upper = min(lo, len(self.b0) - 1)
        candidates = ([upper - 1, upper] if upper else [upper])

        def gap_eer(index: int) -> tuple[float, float]:
            frr = (self.b0[index] + lam * self.bd[index]) / (self.tb0 + lam * self.tbd)
            far = 1.0 - (self.s0[index] + lam * self.sd[index]) / (
                self.ts0 + lam * self.tsd
            )
            return abs(frr - far), 0.5 * (frr + far)

        selected = candidates[0]
        selected_gap, selected_eer = gap_eer(selected)
        for candidate in candidates[1:]:
            candidate_gap, candidate_eer = gap_eer(candidate)
            if candidate_gap < selected_gap:
                selected, selected_gap, selected_eer = candidate, candidate_gap, candidate_eer
        return float(selected_eer), int(selected)


def verify() -> dict[str, object]:
    result_path = HERE / "results.json"
    result = json.loads(result_path.read_text())
    run_contract = result["run_contract"]
    prereg_hash = (HERE / "FREEZE.sha256").read_text().split()[0]
    if sha_file(HERE / "PREREG.md") != prereg_hash:
        raise AssertionError("prereg hash drift")
    if sha_file(HERE / "run_contract.json") != result["run_contract_sha256"]:
        raise AssertionError("run contract hash mismatch")

    metadata_path = Path(run_contract["metadata"]["path"])
    if sha_file(metadata_path) != run_contract["metadata"]["sha256"]:
        raise AssertionError("metadata hash drift")
    rows = read_metadata(metadata_path)
    all_phases = read_all_phases(metadata_path)
    labels = np.asarray([1 if row["label"] == "bonafide" else 0 for row in rows])
    policies = reconstruct_policies(rows)
    structural = json.loads(Path(run_contract["metadata_contract"]["path"]).read_text())
    scores, alignment = load_score_vectors(rows, run_contract, all_phases)
    if alignment != result["score_alignment"]:
        raise AssertionError("score alignment ledger mismatch")

    policy_checks = 0
    pair_checks = 0
    reconstructed_vectors = {}
    for policy in POLICIES:
        weights = policies[policy]
        if sha_weights(weights) != structural["policies"][policy]["sha256_float64_le"]:
            raise AssertionError(f"independent policy hash mismatch: {policy}")
        if sha_weights(weights) != result["policies"][policy]["weight_sha256_float64_le"]:
            raise AssertionError(f"result policy hash mismatch: {policy}")
        eers = {}
        for system in SYSTEMS:
            eer, position = reference_eer(scores[system], labels, weights)
            eers[system] = 100 * eer
            close(eers[system], result["policies"][policy]["eer_pct"][system])
            if position != result["policies"][policy]["threshold_positions"][system]:
                raise AssertionError(f"threshold mismatch: {policy}, {system}")
            policy_checks += 1
        reconstructed_vectors[policy] = eers
        for pair in PAIRS:
            delta = eers[pair[0]] - eers[pair[1]]
            close(delta, result["policies"][policy]["delta_eer_pct_points"][name(pair)])
            if int(np.sign(delta)) != result["policies"][policy]["signs"][name(pair)]:
                raise AssertionError(f"sign mismatch: {policy}, {name(pair)}")
            pair_checks += 1

    # Independently reconstruct pair multiverse extrema and sign-change flags.
    for pair in PAIRS:
        pair_key = name(pair)
        deltas = {
            policy: reconstructed_vectors[policy][pair[0]]
            - reconstructed_vectors[policy][pair[1]]
            for policy in POLICIES
        }
        saved = result["pair_multiverse"][pair_key]
        close(min(deltas.values()), saved["minimum_delta"])
        close(max(deltas.values()), saved["maximum_delta"])
        empirical_sign = int(np.sign(deltas["B0xS0"]))
        changed = any(int(np.sign(value)) != empirical_sign for value in deltas.values())
        if changed != saved["registered_policy_sign_change"]:
            raise AssertionError(f"multiverse change mismatch: {pair_key}")

    grid_denominator = result["path_grid"]["denominator"]
    path_grid_checks = 0
    full_reference_checks = 0
    start = policies["B0xS0"]
    empirical_signs = {
        name(pair): int(
            np.sign(
                reconstructed_vectors["B0xS0"][pair[0]]
                - reconstructed_vectors["B0xS0"][pair[1]]
            )
        )
        for pair in PAIRS
    }
    for policy, path_result in result["path_grid"]["paths"].items():
        end = policies[policy]
        models = {
            system: IndependentGridEER(scores[system], labels, start, end)
            for system in SYSTEMS
        }
        first_changes = {name(pair): None for pair in PAIRS}
        for grid_index in range(grid_denominator + 1):
            lam = grid_index / grid_denominator
            eers = {system: 100 * models[system].at(lam)[0] for system in SYSTEMS}
            for pair in PAIRS:
                pair_key = name(pair)
                if first_changes[pair_key] is None:
                    sign = int(np.sign(eers[pair[0]] - eers[pair[1]]))
                    if sign != empirical_signs[pair_key]:
                        first_changes[pair_key] = grid_index
            path_grid_checks += len(PAIRS)
        saved_changes = path_result["pairs_with_sign_change"]
        for pair in PAIRS:
            pair_key = name(pair)
            saved = saved_changes.get(pair_key)
            if saved is None:
                if first_changes[pair_key] is not None:
                    raise AssertionError(f"missing path witness: {policy}, {pair_key}")
                continue
            if first_changes[pair_key] != saved["first_changed_grid_index"]:
                raise AssertionError(f"first grid mismatch: {policy}, {pair_key}")
            right = int(saved["first_changed_grid_index"])
            for local_index in range(max(0, right - 2), min(grid_denominator, right + 2) + 1):
                lam = local_index / grid_denominator
                weights = (1 - lam) * start + lam * end
                left_eer, _ = reference_eer(scores[pair[0]], labels, weights)
                right_eer, _ = reference_eer(scores[pair[1]], labels, weights)
                independent_sign = int(np.sign(left_eer - right_eer))
                fast_sign = int(
                    np.sign(models[pair[0]].at(lam)[0] - models[pair[1]].at(lam)[0])
                )
                if independent_sign != fast_sign:
                    raise AssertionError(f"local full-reference mismatch: {policy}, {pair_key}")
                full_reference_checks += 2
            witness_lam = saved["lambda_witness"]
            witness_weights = (1 - witness_lam) * start + witness_lam * end
            if sha_weights(witness_weights) != saved["weight_sha256_float64_le"]:
                raise AssertionError(f"witness hash mismatch: {policy}, {pair_key}")

    return {
        "experiment": "EXP-108",
        "passed": True,
        "independent_implementation": True,
        "imports_analysis_or_policy_builder": False,
        "result_sha256": sha_file(result_path),
        "checks": {
            "policy_system_eers": policy_checks,
            "policy_pair_deltas": pair_checks,
            "registered_path_grid_pair_signs": path_grid_checks,
            "local_full_reference_system_eers": full_reference_checks,
            "score_file_hashes": len(SYSTEMS),
            "policy_weight_hashes": len(POLICIES),
        },
    }


def main() -> None:
    try:
        output = verify()
    except Exception as error:  # fail closed with a machine-readable artifact
        output = {
            "experiment": "EXP-108",
            "passed": False,
            "error_type": type(error).__name__,
            "error": str(error),
        }
        (HERE / "verification.json").write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n"
        )
        raise
    (HERE / "verification.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    print(f"independent verification passed: {output['checks']}")


if __name__ == "__main__":
    main()
