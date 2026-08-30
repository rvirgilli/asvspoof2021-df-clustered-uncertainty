#!/usr/bin/env python3
"""Frozen post-result factor decomposition for EXP-114 SpoofCeleb scores."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


B = 5000
SEED = 20260830
SYSTEMS = ("aasist", "ssl_aasist", "sls", "xlsr_mamba")
EXPECTED_MANIFEST_SHA256 = (
    "008371adaeb300401357a58035d3c4ac9e1c440abe804ceab8ccd1bdc84b2544"
)
EXPECTED_SCORE_SHA256 = {
    "aasist": "6e75ff20e525713a800e47d756d289604e145f868eed174809c4983fcedac2ad",
    "ssl_aasist": "f0237f3712c435157d2cbd5f84f403acf6bea23e2c5553210f8fe276a82743b5",
    "sls": "4e83b949a51de18866dd2021559cfe4dcab5df6ff028080e28c7b2c82b8d28c9",
    "xlsr_mamba": "5d4c6ca9cc4be52746f7cc1ae2b1007e5dc5e1ca01ddd1221b9560236f1ff835",
}
EXPECTED_JOINT_RESULT_SHA256 = (
    "ff999f5b35ecc77c92299037a07a1700dbed1f88c5ff874a5cbfc3222a6836ae"
)
EXPECTED_JOINT_SENSITIVE = (
    "ssl_aasist vs sls",
    "ssl_aasist vs xlsr_mamba",
    "sls vs xlsr_mamba",
)
EXPECTED_SOURCE = "TITW-VoxCeleb1"
SPOOF_ATTACKS = tuple(f"A{index}" for index in range(15, 24))
EXPECTED_TRIALS = 91_130
EXPECTED_BONAFIDE = 9_113
EXPECTED_SPEAKERS = 40


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    partial.replace(path)


def atomic_npy(path: Path, value: np.ndarray) -> None:
    partial = path.with_suffix(path.suffix + ".partial")
    with partial.open("wb") as stream:
        np.save(stream, value, allow_pickle=False)
    partial.replace(path)


def git(*args: str, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stdout.strip())
    return completed.stdout.strip()


def verify_freeze(here: Path) -> dict[str, str]:
    freeze = here / "FREEZE.sha256"
    if not freeze.is_file():
        raise FileNotFoundError("missing FREEZE.sha256")
    declared: dict[str, str] = {}
    for raw in freeze.read_text().splitlines():
        digest, name = raw.split("  ", 1)
        if len(digest) != 64 or name in declared:
            raise ValueError("malformed freeze entry")
        target = here / name
        if not target.is_file() or sha256_file(target) != digest:
            raise ValueError(f"frozen file mismatch: {name}")
        declared[name] = digest
    required = {
        "PREREG.md", "DATA.md", "analyze.py", "test_analyze.py",
        "pyproject.toml", "uv.lock",
    }
    if set(declared) != required:
        raise ValueError(f"freeze surface mismatch: {sorted(declared)}")
    return declared


def validate_grid(rows: list[dict[str, str]]) -> None:
    by_base: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_base[row["base_id"]].append(row)
    if len(by_base) != EXPECTED_BONAFIDE:
        raise ValueError("base-product count mismatch")
    required = {"A00", *SPOOF_ATTACKS}
    for base, group in by_base.items():
        attacks = [row["attack"] for row in group]
        if len(group) != 10 or set(attacks) != required or len(set(attacks)) != 10:
            raise ValueError(f"incomplete product: {base}")
        if len({row["speaker"] for row in group}) != 1:
            raise ValueError(f"speaker mismatch within product: {base}")


def read_manifest(path: Path) -> dict[str, np.ndarray]:
    if sha256_file(path) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("manifest SHA-256 mismatch")
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {"utt", "base_id", "label", "speaker", "attack", "source"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("manifest schema mismatch")
    if len(rows) != EXPECTED_TRIALS:
        raise ValueError("trial count mismatch")
    utterances = [row["utt"] for row in rows]
    if len(set(utterances)) != len(utterances):
        raise ValueError("manifest IDs are not unique")
    if {row["source"] for row in rows} != {EXPECTED_SOURCE}:
        raise ValueError("source roster mismatch")
    labels = np.asarray([row["label"] == "bonafide" for row in rows], dtype=np.int8)
    if int(labels.sum()) != EXPECTED_BONAFIDE:
        raise ValueError("bona-fide count mismatch")
    if {row["attack"] for row in rows if row["label"] == "spoof"} != set(SPOOF_ATTACKS):
        raise ValueError("spoof-attack roster mismatch")
    validate_grid(rows)
    speaker_names, speakers = np.unique(
        [row["speaker"] for row in rows], return_inverse=True,
    )
    if len(speaker_names) != EXPECTED_SPEAKERS:
        raise ValueError("speaker count mismatch")
    attack_names, attacks = np.unique(
        [row["attack"] for row in rows], return_inverse=True,
    )
    return {
        "utt": np.asarray(utterances, dtype=object),
        "labels": labels,
        "speakers": speakers,
        "speaker_names": speaker_names,
        "attacks": attacks,
        "attack_names": attack_names,
    }


def read_scores(path: Path, expected_utt: np.ndarray, system: str) -> np.ndarray:
    if sha256_file(path) != EXPECTED_SCORE_SHA256[system]:
        raise ValueError(f"{system} score SHA-256 mismatch")
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if not rows or not {"utt", "score"}.issubset(rows[0]):
        raise ValueError(f"{system} score schema mismatch")
    if len(rows) != len(expected_utt):
        raise ValueError(f"{system} score row mismatch")
    mapping: dict[str, float] = {}
    for row in rows:
        if row["utt"] in mapping:
            raise ValueError(f"duplicate {system} score ID")
        value = float(row["score"])
        if not math.isfinite(value):
            raise ValueError(f"non-finite {system} score")
        mapping[row["utt"]] = value
    expected = set(expected_utt)
    if set(mapping) != expected:
        raise ValueError(f"{system} score roster mismatch")
    values = np.asarray([mapping[utt] for utt in expected_utt], dtype=np.float64)
    if np.ptp(values) == 0:
        raise ValueError(f"constant {system} score vector")
    return values


def validate_joint_result(path: Path) -> dict:
    if sha256_file(path) != EXPECTED_JOINT_RESULT_SHA256:
        raise ValueError("EXP-114 joint result SHA-256 mismatch")
    result = json.loads(path.read_text())
    if result.get("arm_a_trial_iid", {}).get("simultaneous_excluding_zero") != 6:
        raise ValueError("EXP-114 trial-IID endpoint mismatch")
    if result.get("arm_b_global_product", {}).get("simultaneous_excluding_zero") != 3:
        raise ValueError("EXP-114 joint-product endpoint mismatch")
    observed = tuple(sorted(result.get("registered_reading", {}).get(
        "sampling_unit_sensitive_pairs", []
    )))
    if observed != tuple(sorted(EXPECTED_JOINT_SENSITIVE)):
        raise ValueError("EXP-114 sensitive-pair roster mismatch")
    return result


def normalized_class_mass(weights: np.ndarray, labels: np.ndarray) -> np.ndarray:
    mass = np.zeros(len(weights), dtype=np.float64)
    for value in (1, 0):
        mask = labels == value
        total = float(weights[mask].sum())
        if not total > 0:
            raise ValueError("positive support required for both classes")
        mass[mask] = weights[mask] / total
        if not np.isclose(mass[mask].sum(), 1.0, rtol=1e-12, atol=1e-15):
            raise RuntimeError("class-mass normalization failed")
    return mass


def eer_from_mass(order: np.ndarray, labels: np.ndarray, mass: np.ndarray) -> float:
    ordered_labels = labels[order]
    ordered_mass = mass[order]
    frr = np.cumsum(ordered_mass * ordered_labels)
    far = 1.0 - np.cumsum(ordered_mass * (1 - ordered_labels))
    distance = np.abs(frr - far)
    minimum = float(distance.min())
    tied = np.flatnonzero(np.isclose(distance, minimum, rtol=1e-12, atol=1e-15))
    index = int(tied[0])
    return float((frr[index] + far[index]) / 2.0)


def eers_for_weights(
    weights: np.ndarray, labels: np.ndarray, orders: dict[str, np.ndarray],
) -> np.ndarray:
    mass = normalized_class_mass(weights, labels)
    return np.asarray(
        [eer_from_mass(orders[system], labels, mass) for system in SYSTEMS],
        dtype=np.float64,
    )


def draw_speaker_only(
    rng: np.random.Generator, data: dict[str, np.ndarray],
) -> tuple[np.ndarray, tuple[int, ...]]:
    n_speakers = len(data["speaker_names"])
    counts = np.bincount(
        rng.integers(0, n_speakers, size=n_speakers), minlength=n_speakers,
    )
    weights = counts[data["speakers"]].astype(np.float64)
    return weights, tuple(int(value) for value in counts)


def draw_attack_only(
    rng: np.random.Generator, data: dict[str, np.ndarray],
) -> tuple[np.ndarray, tuple[int, ...]]:
    labels = data["labels"]
    spoof = labels == 0
    spoof_attacks = np.unique(data["attacks"][spoof])
    drawn = rng.choice(spoof_attacks, size=len(spoof_attacks), replace=True)
    counts = np.bincount(drawn, minlength=len(data["attack_names"]))
    weights = np.ones(len(labels), dtype=np.float64)
    weights[spoof] = counts[data["attacks"][spoof]]
    return weights, tuple(int(counts[index]) for index in spoof_attacks)


def pair_rows() -> list[tuple[str, str, int, int]]:
    rows = []
    for first_index, first in enumerate(SYSTEMS):
        for second_index in range(first_index + 1, len(SYSTEMS)):
            second = SYSTEMS[second_index]
            rows.append((first, second, first_index, second_index))
    return rows


def summarize(boot: np.ndarray, point: np.ndarray) -> dict:
    rows = pair_rows()
    deltas = np.column_stack([
        100.0 * (boot[:, first_index] - boot[:, second_index])
        for _, _, first_index, second_index in rows
    ])
    sd = deltas.std(axis=0, ddof=1)
    if np.any(sd <= 0) or not np.all(np.isfinite(sd)):
        raise ValueError("invalid bootstrap SD")
    centered = np.abs((deltas - deltas.mean(axis=0)) / sd)
    critical = float(np.quantile(centered.max(axis=1), 0.95))
    pairs = {}
    for index, (first, second, first_index, second_index) in enumerate(rows):
        observed = 100.0 * (point[first_index] - point[second_index])
        percentile = np.quantile(deltas[:, index], [0.025, 0.975])
        simultaneous = np.asarray([
            observed - critical * sd[index], observed + critical * sd[index],
        ])
        unique = int(len(np.unique(deltas[:, index])))
        if unique <= 1:
            raise ValueError(f"degenerate bootstrap delta: {first} vs {second}")
        pairs[f"{first} vs {second}"] = {
            "delta_eer_points": float(observed),
            "bootstrap_sd": float(sd[index]),
            "pointwise_percentile": percentile.tolist(),
            "simultaneous_max_t": simultaneous.tolist(),
            "pointwise_excludes_zero": bool(percentile[0] > 0 or percentile[1] < 0),
            "simultaneous_excludes_zero": bool(
                simultaneous[0] > 0 or simultaneous[1] < 0
            ),
            "unique_bootstrap_delta_values": unique,
        }
    return {
        "max_t_critical_value": critical,
        "simultaneous_excluding_zero": sum(
            row["simultaneous_excludes_zero"] for row in pairs.values()
        ),
        "pointwise_excluding_zero": sum(
            row["pointwise_excludes_zero"] for row in pairs.values()
        ),
        "pairs": pairs,
        "unique_bootstrap_eer_values": {
            system: int(len(np.unique(boot[:, index])))
            for index, system in enumerate(SYSTEMS)
        },
    }


def classify_known_pairs(speaker: dict, attack: dict) -> dict[str, dict]:
    result = {}
    for pair in EXPECTED_JOINT_SENSITIVE:
        speaker_includes = not speaker["pairs"][pair]["simultaneous_excludes_zero"]
        attack_includes = not attack["pairs"][pair]["simultaneous_excludes_zero"]
        if speaker_includes and attack_includes:
            label = "both_one_factor_arms_include_zero"
        elif speaker_includes:
            label = "speaker_only_includes_zero"
        elif attack_includes:
            label = "attack_only_includes_zero"
        else:
            label = "neither_one_factor_arm_includes_zero"
        result[pair] = {
            "speaker_only_includes_zero": speaker_includes,
            "attack_only_includes_zero": attack_includes,
            "classification": label,
        }
    return result


def run(
    data: dict[str, np.ndarray], scores: dict[str, np.ndarray], *,
    replicates: int = B, seed: int = SEED,
) -> tuple[dict, np.ndarray, np.ndarray]:
    labels = data["labels"]
    orders = {
        system: np.argsort(scores[system], kind="mergesort") for system in SYSTEMS
    }
    point = eers_for_weights(np.ones(len(labels)), labels, orders)
    speaker_boot = np.empty((replicates, len(SYSTEMS)), dtype=np.float64)
    attack_boot = np.empty_like(speaker_boot)
    speaker_seed, attack_seed = np.random.SeedSequence(seed).spawn(2)
    speaker_rng = np.random.default_rng(speaker_seed)
    attack_rng = np.random.default_rng(attack_seed)
    speaker_patterns: set[tuple[int, ...]] = set()
    attack_patterns: set[tuple[int, ...]] = set()
    for replicate in range(replicates):
        speaker_weights, speaker_pattern = draw_speaker_only(speaker_rng, data)
        attack_weights, attack_pattern = draw_attack_only(attack_rng, data)
        speaker_patterns.add(speaker_pattern)
        attack_patterns.add(attack_pattern)
        speaker_boot[replicate] = eers_for_weights(
            speaker_weights, labels, orders,
        )
        attack_boot[replicate] = eers_for_weights(attack_weights, labels, orders)
        if replicates == B and (replicate + 1) % 250 == 0:
            print(f"bootstrap {replicate + 1}/{replicates}", flush=True)
    if len(speaker_patterns) <= 1 or len(attack_patterns) <= 1:
        raise RuntimeError("multiplicity pattern guard failed")
    speaker_summary = summarize(speaker_boot, point)
    attack_summary = summarize(attack_boot, point)
    result = {
        "schema_version": 1,
        "evidence_status": "post-result mechanism diagnostic",
        "B": replicates,
        "seed": seed,
        "systems": list(SYSTEMS),
        "n_trials": len(labels),
        "n_speakers": len(data["speaker_names"]),
        "n_spoof_attacks": len(SPOOF_ATTACKS),
        "point_eer_percent": {
            system: float(100.0 * point[index])
            for index, system in enumerate(SYSTEMS)
        },
        "arm_speaker_only": speaker_summary,
        "arm_attack_only": attack_summary,
        "known_joint_sensitive_pair_decomposition": classify_known_pairs(
            speaker_summary, attack_summary,
        ),
        "guards": {
            "speaker_only_attack_multiplicity_fixed_at_one": True,
            "attack_only_speaker_multiplicity_fixed_at_one": True,
            "distinct_speaker_multiplicity_patterns_observed": len(speaker_patterns),
            "distinct_attack_multiplicity_patterns_observed": len(attack_patterns),
            "single_official_source": EXPECTED_SOURCE,
            "complete_crossed_grid": True,
            "attack_factor_support": len(SPOOF_ATTACKS),
        },
    }
    return result, speaker_boot, attack_boot


def parse_scores(values: list[str]) -> dict[str, Path]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"score argument must be NAME=PATH: {value}")
        name, raw_path = value.split("=", 1)
        if name in result:
            raise ValueError(f"duplicate score argument: {name}")
        result[name] = Path(raw_path)
    if set(result) != set(SYSTEMS):
        raise ValueError(f"score family mismatch: {sorted(result)}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--joint-result", type=Path, required=True)
    parser.add_argument("--score", action="append", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    project = here.parents[1]
    relative = here.relative_to(project)
    status = git("status", "--short", "--", str(relative), cwd=project)
    if status:
        raise RuntimeError(f"EXP-115 is dirty at analysis time:\n{status}")
    frozen = verify_freeze(here)
    joint = validate_joint_result(args.joint_result)
    data = read_manifest(args.manifest)
    score_paths = parse_scores(args.score)
    scores = {
        system: read_scores(score_paths[system], data["utt"], system)
        for system in SYSTEMS
    }
    started = datetime.now(timezone.utc).isoformat()
    result, speaker_boot, attack_boot = run(data, scores)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    speaker_path = args.out_dir / "SPEAKER-ONLY-BOOTSTRAP.npy"
    attack_path = args.out_dir / "ATTACK-ONLY-BOOTSTRAP.npy"
    result_path = args.out_dir / "RESULTS.json"
    receipt_path = args.out_dir / "RUN-RECEIPT.json"
    atomic_npy(speaker_path, speaker_boot)
    atomic_npy(attack_path, attack_boot)
    result["provenance"] = {
        "started_utc": started,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git("rev-parse", "HEAD", cwd=project),
        "experiment_git_status_before_run": status,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "frozen_files": frozen,
        "inputs": {
            "manifest": {
                "sha256": EXPECTED_MANIFEST_SHA256,
                "bytes": args.manifest.stat().st_size,
            },
            "joint_result": {
                "sha256": EXPECTED_JOINT_RESULT_SHA256,
                "bytes": args.joint_result.stat().st_size,
                "registered_reading": joint["registered_reading"],
            },
            "scores": {
                system: {
                    "sha256": EXPECTED_SCORE_SHA256[system],
                    "bytes": score_paths[system].stat().st_size,
                }
                for system in SYSTEMS
            },
        },
        "bootstrap_arrays": {
            speaker_path.name: {
                "sha256": sha256_file(speaker_path),
                "shape": list(speaker_boot.shape),
                "dtype": str(speaker_boot.dtype),
            },
            attack_path.name: {
                "sha256": sha256_file(attack_path),
                "shape": list(attack_boot.shape),
                "dtype": str(attack_boot.dtype),
            },
        },
    }
    atomic_json(result_path, result)
    receipt = {
        "schema_version": 1,
        "status": "complete",
        "evidence_status": "post-result mechanism diagnostic",
        "git_head": result["provenance"]["git_head"],
        "bindings": {
            "RESULTS.json": sha256_file(result_path),
            speaker_path.name: sha256_file(speaker_path),
            attack_path.name: sha256_file(attack_path),
            "FREEZE.sha256": sha256_file(here / "FREEZE.sha256"),
            "EXP-114-PROVENANCE-RERUN-RESULTS.json": EXPECTED_JOINT_RESULT_SHA256,
            "manifest": EXPECTED_MANIFEST_SHA256,
            **{
                f"score:{system}": digest
                for system, digest in EXPECTED_SCORE_SHA256.items()
            },
        },
    }
    atomic_json(receipt_path, receipt)
    print(json.dumps({
        "speaker_only_excluding_zero": result["arm_speaker_only"][
            "simultaneous_excluding_zero"
        ],
        "attack_only_excluding_zero": result["arm_attack_only"][
            "simultaneous_excluding_zero"
        ],
        "decomposition": result["known_joint_sensitive_pair_decomposition"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
