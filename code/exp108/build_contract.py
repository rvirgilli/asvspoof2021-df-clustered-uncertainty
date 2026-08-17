#!/usr/bin/env python3
"""Build the score-blind EXP-108 composition contract from 21DF metadata."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METADATA = Path(os.environ.get(
    "M1_EXP108_METADATA",
    ROOT / "inputs/anti-spoofing/DF-keys-full/keys/DF/CM/trial_metadata.txt",
))
BONA_POLICIES = ("B0", "B1", "B2")
SPOOF_POLICIES = ("S0", "S1", "S2", "S3")
POLICIES = tuple(f"{b}x{s}" for b in BONA_POLICIES for s in SPOOF_POLICIES)


@dataclass(frozen=True)
class Trial:
    speaker: str
    utterance: str
    codec: str
    source: str
    attack: str
    label: str
    phase: str
    family: str
    task: str


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_trials(path: Path) -> list[Trial]:
    rows: list[Trial] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        fields = line.split()
        if len(fields) < 10:
            raise ValueError(f"metadata line {line_number} has {len(fields)} fields")
        if fields[7] != "eval":
            continue
        rows.append(
            Trial(
                speaker=fields[0],
                utterance=fields[1],
                codec=fields[2],
                source=fields[3],
                attack=fields[4],
                label=fields[5],
                phase=fields[7],
                family=fields[8],
                task=fields[9],
            )
        )
    rows.sort(key=lambda row: row.utterance)
    if not rows:
        raise ValueError("no eval trials")
    if len({row.utterance for row in rows}) != len(rows):
        raise ValueError("eval utterance IDs are not unique")
    labels = {row.label for row in rows}
    if labels != {"bonafide", "spoof"}:
        raise ValueError(f"unexpected labels: {sorted(labels)}")
    return rows


def spoof_stratum(row: Trial) -> str:
    if row.label != "spoof":
        raise ValueError("spoof_stratum called on a bona-fide row")
    if row.source == "asvspoof":
        return "asvspoof"
    if row.task == "-":
        raise ValueError(f"missing task for spoof source {row.source}")
    return f"{row.source}/{row.task}"


def _assign_equal_hierarchy(
    rows: list[Trial],
    indices: Iterable[int],
    keys: tuple,
) -> np.ndarray:
    """Assign equal conditional mass at every successive hierarchy level."""
    index_list = list(indices)
    out = np.zeros(len(rows), dtype=np.float64)

    def recurse(members: list[int], depth: int, mass: float) -> None:
        if depth == len(keys):
            share = mass / len(members)
            out[np.asarray(members, dtype=np.int64)] = share
            return
        grouped: dict[str, list[int]] = defaultdict(list)
        key = keys[depth]
        for index in members:
            grouped[str(key(rows[index]))].append(index)
        child_mass = mass / len(grouped)
        for name in sorted(grouped):
            recurse(grouped[name], depth + 1, child_mass)

    recurse(index_list, 0, 1.0)
    return out


def build_class_weights(rows: list[Trial]) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    bona_indices = [i for i, row in enumerate(rows) if row.label == "bonafide"]
    spoof_indices = [i for i, row in enumerate(rows) if row.label == "spoof"]

    bona: dict[str, np.ndarray] = {}
    b0 = np.zeros(len(rows), dtype=np.float64)
    b0[bona_indices] = 1.0 / len(bona_indices)
    bona["B0"] = b0
    bona["B1"] = _assign_equal_hierarchy(
        rows, bona_indices, (lambda row: row.source,)
    )
    bona["B2"] = _assign_equal_hierarchy(
        rows, bona_indices, (lambda row: row.source, lambda row: row.speaker)
    )

    spoof: dict[str, np.ndarray] = {}
    s0 = np.zeros(len(rows), dtype=np.float64)
    s0[spoof_indices] = 1.0 / len(spoof_indices)
    spoof["S0"] = s0
    spoof["S1"] = _assign_equal_hierarchy(
        rows, spoof_indices, (spoof_stratum,)
    )
    spoof["S2"] = _assign_equal_hierarchy(
        rows,
        spoof_indices,
        (spoof_stratum, lambda row: f"{row.speaker}\x1f{row.attack}"),
    )
    spoof["S3"] = _assign_equal_hierarchy(
        rows,
        spoof_indices,
        (
            spoof_stratum,
            lambda row: row.family,
            lambda row: row.attack,
            lambda row: row.speaker,
        ),
    )
    return bona, spoof


def build_policy_weights(rows: list[Trial]) -> dict[str, np.ndarray]:
    bona, spoof = build_class_weights(rows)
    policies = {
        f"{b_name}x{s_name}": bona[b_name] + spoof[s_name]
        for b_name in BONA_POLICIES
        for s_name in SPOOF_POLICIES
    }
    if tuple(policies) != POLICIES:
        raise AssertionError("policy ordering drift")
    return policies


def _mass_by(rows: list[Trial], weights: np.ndarray, label: str, key) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for row, weight in zip(rows, weights, strict=True):
        if row.label == label:
            out[str(key(row))] += float(weight)
    return {name: out[name] for name in sorted(out)}


def validate_policy(rows: list[Trial], name: str, weights: np.ndarray) -> dict[str, object]:
    if weights.shape != (len(rows),):
        raise AssertionError(f"{name}: shape mismatch")
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0):
        raise AssertionError(f"{name}: every observed trial must have positive finite mass")
    labels = np.array([row.label for row in rows])
    bona_sum = float(weights[labels == "bonafide"].sum())
    spoof_sum = float(weights[labels == "spoof"].sum())
    if abs(bona_sum - 1.0) > 1e-12 or abs(spoof_sum - 1.0) > 1e-12:
        raise AssertionError(f"{name}: class sums {bona_sum}, {spoof_sum}")

    b_name, s_name = name.split("x")
    bona_sources = _mass_by(rows, weights, "bonafide", lambda row: row.source)
    spoof_strata = _mass_by(rows, weights, "spoof", spoof_stratum)
    if b_name in {"B1", "B2"}:
        if max(abs(value - 1 / 3) for value in bona_sources.values()) > 1e-12:
            raise AssertionError(f"{name}: bona source marginal")
    if s_name in {"S1", "S2", "S3"}:
        if max(abs(value - 1 / 5) for value in spoof_strata.values()) > 1e-12:
            raise AssertionError(f"{name}: spoof stratum marginal")

    return {
        "sha256_float64_le": sha256_bytes(np.asarray(weights, dtype="<f8").tobytes()),
        "bona_sum": bona_sum,
        "spoof_sum": spoof_sum,
        "minimum_positive_mass": float(weights.min()),
        "maximum_mass": float(weights.max()),
        "bona_source_mass": bona_sources,
        "spoof_stratum_mass": spoof_strata,
    }


def build_contract(metadata: Path) -> dict[str, object]:
    rows = load_trials(metadata)
    policies = build_policy_weights(rows)
    counts = Counter(row.label for row in rows)
    return {
        "contract": {
            "experiment": "EXP-108",
            "kind": "metadata_only_score_blind_policy_contract",
            "scores_loaded": False,
            "eer_evaluated": False,
            "new_outcomes_opened": False,
        },
        "metadata": {"path": str(metadata), "sha256": sha256_file(metadata)},
        "trial_order": "utterance_id_lexicographic",
        "trial_ids_sha256_newline_utf8": sha256_bytes(
            ("\n".join(row.utterance for row in rows) + "\n").encode()
        ),
        "n_eval_trials": len(rows),
        "n_bonafide": counts["bonafide"],
        "n_spoof": counts["spoof"],
        "policy_order": list(POLICIES),
        "policies": {
            name: validate_policy(rows, name, policies[name]) for name in POLICIES
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "contract.json"
    )
    args = parser.parse_args()
    contract = build_contract(args.metadata)
    args.out.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
    print(f"wrote metadata-only contract {args.out}")


if __name__ == "__main__":
    main()
