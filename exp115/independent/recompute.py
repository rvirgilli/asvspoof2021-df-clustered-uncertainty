#!/usr/bin/env python3
"""Standalone EXP-115 recomputation with no repository analysis imports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


SYSTEMS = ("aasist", "ssl_aasist", "sls", "xlsr_mamba")
B = 5000
SEED = 20260830
EXPECTED_MANIFEST_SHA256 = (
    "008371adaeb300401357a58035d3c4ac9e1c440abe804ceab8ccd1bdc84b2544"
)
EXPECTED_SCORE_SHA256 = {
    "aasist": "6e75ff20e525713a800e47d756d289604e145f868eed174809c4983fcedac2ad",
    "ssl_aasist": "f0237f3712c435157d2cbd5f84f403acf6bea23e2c5553210f8fe276a82743b5",
    "sls": "4e83b949a51de18866dd2021559cfe4dcab5df6ff028080e28c7b2c82b8d28c9",
    "xlsr_mamba": "5d4c6ca9cc4be52746f7cc1ae2b1007e5dc5e1ca01ddd1221b9560236f1ff835",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_scores(values: list[str]) -> dict[str, Path]:
    result = {}
    for value in values:
        system, raw_path = value.split("=", 1)
        result[system] = Path(raw_path)
    if set(result) != set(SYSTEMS):
        raise ValueError("score family mismatch")
    return result


def read_inputs(manifest: Path, score_paths: dict[str, Path]) -> tuple[dict, dict]:
    if sha256_file(manifest) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("manifest hash mismatch")
    with manifest.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 91_130 or len({row["utt"] for row in rows}) != len(rows):
        raise ValueError("manifest roster mismatch")
    if {row["source"] for row in rows} != {"TITW-VoxCeleb1"}:
        raise ValueError("source roster mismatch")
    utterances = [row["utt"] for row in rows]
    labels = np.asarray([row["label"] == "bonafide" for row in rows], dtype=np.int8)
    speaker_names, speakers = np.unique(
        [row["speaker"] for row in rows], return_inverse=True,
    )
    attack_names, attacks = np.unique(
        [row["attack"] for row in rows], return_inverse=True,
    )
    spoof = labels == 0
    spoof_attacks = np.unique(attacks[spoof])
    if len(speaker_names) != 40 or len(spoof_attacks) != 9:
        raise ValueError("factor census mismatch")
    scores = {}
    for system in SYSTEMS:
        path = score_paths[system]
        if sha256_file(path) != EXPECTED_SCORE_SHA256[system]:
            raise ValueError(f"{system} score hash mismatch")
        with path.open(newline="") as stream:
            score_rows = list(csv.DictReader(stream, delimiter="\t"))
        mapping = {row["utt"]: float(row["score"]) for row in score_rows}
        if len(mapping) != len(utterances) or set(mapping) != set(utterances):
            raise ValueError(f"{system} score roster mismatch")
        scores[system] = np.asarray([mapping[utt] for utt in utterances])
    return {
        "labels": labels,
        "speakers": speakers,
        "speaker_names": speaker_names,
        "attacks": attacks,
        "attack_names": attack_names,
        "spoof_attacks": spoof_attacks,
    }, scores


def run(data: dict, scores: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    labels = data["labels"]
    orders = {
        system: np.argsort(scores[system], kind="mergesort") for system in SYSTEMS
    }

    def system_eers(weights: np.ndarray) -> np.ndarray:
        mass = np.zeros(len(weights), dtype=np.float64)
        for value in (1, 0):
            mask = labels == value
            total = weights[mask].sum(dtype=np.float64)
            if not total > 0:
                raise ValueError("lost class support")
            mass[mask] = weights[mask] / total
        output = []
        for system in SYSTEMS:
            order = orders[system]
            ordered_labels = labels[order]
            ordered_mass = mass[order]
            frr = np.cumsum(ordered_mass * ordered_labels)
            far = 1.0 - np.cumsum(ordered_mass * (1 - ordered_labels))
            distance = np.abs(frr - far)
            tied = np.flatnonzero(
                np.isclose(distance, distance.min(), rtol=1e-12, atol=1e-15)
            )
            index = int(tied[0])
            output.append((frr[index] + far[index]) / 2.0)
        return np.asarray(output)

    point = system_eers(np.ones(len(labels)))
    speaker = np.empty((B, len(SYSTEMS)), dtype=np.float64)
    attack = np.empty_like(speaker)
    speaker_seed, attack_seed = np.random.SeedSequence(SEED).spawn(2)
    speaker_rng = np.random.default_rng(speaker_seed)
    attack_rng = np.random.default_rng(attack_seed)
    spoof = labels == 0
    for replicate in range(B):
        sampled_speakers = speaker_rng.integers(
            0, len(data["speaker_names"]), size=len(data["speaker_names"]),
        )
        speaker_counts = np.bincount(
            sampled_speakers, minlength=len(data["speaker_names"]),
        )
        speaker[replicate] = system_eers(
            speaker_counts[data["speakers"]].astype(np.float64),
        )
        sampled_attacks = attack_rng.choice(
            data["spoof_attacks"], size=len(data["spoof_attacks"]), replace=True,
        )
        attack_counts = np.bincount(
            sampled_attacks, minlength=len(data["attack_names"]),
        )
        attack_weights = np.ones(len(labels), dtype=np.float64)
        attack_weights[spoof] = attack_counts[data["attacks"][spoof]]
        attack[replicate] = system_eers(attack_weights)
    return point, speaker, attack


def summarize(boot: np.ndarray, point: np.ndarray) -> dict:
    rows = []
    for first, first_name in enumerate(SYSTEMS):
        for second in range(first + 1, len(SYSTEMS)):
            rows.append((f"{first_name} vs {SYSTEMS[second]}", first, second))
    deltas = np.column_stack([
        100.0 * (boot[:, first] - boot[:, second])
        for _, first, second in rows
    ])
    sd = deltas.std(axis=0, ddof=1)
    critical = float(np.quantile(
        np.max(np.abs((deltas - deltas.mean(axis=0)) / sd), axis=1), 0.95,
    ))
    pairs = {}
    for index, (name, first, second) in enumerate(rows):
        observed = 100.0 * (point[first] - point[second])
        interval = [
            float(observed - critical * sd[index]),
            float(observed + critical * sd[index]),
        ]
        pairs[name] = {
            "bootstrap_sd": float(sd[index]),
            "simultaneous_max_t": interval,
            "simultaneous_excludes_zero": bool(interval[0] > 0 or interval[1] < 0),
        }
    return {
        "max_t_critical_value": critical,
        "simultaneous_excluding_zero": sum(
            row["simultaneous_excludes_zero"] for row in pairs.values()
        ),
        "pairs": pairs,
    }


def compare(summary: dict, expected: dict) -> None:
    np.testing.assert_allclose(
        summary["max_t_critical_value"], expected["max_t_critical_value"],
        rtol=0, atol=0,
    )
    if summary["simultaneous_excluding_zero"] != expected["simultaneous_excluding_zero"]:
        raise AssertionError("endpoint mismatch")
    for pair, row in summary["pairs"].items():
        expected_row = expected["pairs"][pair]
        np.testing.assert_allclose(
            row["bootstrap_sd"], expected_row["bootstrap_sd"], rtol=0, atol=0,
        )
        np.testing.assert_allclose(
            row["simultaneous_max_t"], expected_row["simultaneous_max_t"],
            rtol=0, atol=0,
        )
        if row["simultaneous_excludes_zero"] != expected_row["simultaneous_excludes_zero"]:
            raise AssertionError(f"decision mismatch: {pair}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--score", action="append", required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--speaker-array", type=Path, required=True)
    parser.add_argument("--attack-array", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    score_paths = parse_scores(args.score)
    data, scores = read_inputs(args.manifest, score_paths)
    point, speaker, attack = run(data, scores)
    expected_speaker = np.load(args.speaker_array, allow_pickle=False)
    expected_attack = np.load(args.attack_array, allow_pickle=False)
    if not np.array_equal(speaker, expected_speaker):
        raise AssertionError("speaker-only bootstrap array mismatch")
    if not np.array_equal(attack, expected_attack):
        raise AssertionError("attack-only bootstrap array mismatch")
    result = json.loads(args.result.read_text())
    speaker_summary = summarize(speaker, point)
    attack_summary = summarize(attack, point)
    compare(speaker_summary, result["arm_speaker_only"])
    compare(attack_summary, result["arm_attack_only"])
    output = {
        "schema_version": 1,
        "status": "exact_reproduction",
        "evidence_status": "post-result standalone recomputation",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "implementation_sha256": sha256_file(Path(__file__)),
        "inputs": {
            "manifest": sha256_file(args.manifest),
            "scores": {
                system: sha256_file(score_paths[system]) for system in SYSTEMS
            },
            "result": sha256_file(args.result),
            "speaker_array": sha256_file(args.speaker_array),
            "attack_array": sha256_file(args.attack_array),
        },
        "speaker_array_exact": True,
        "attack_array_exact": True,
        "speaker_only_excluding_zero": speaker_summary["simultaneous_excluding_zero"],
        "attack_only_excluding_zero": attack_summary["simultaneous_excluding_zero"],
        "speaker_max_t_critical_value": speaker_summary["max_t_critical_value"],
        "attack_max_t_critical_value": attack_summary["max_t_critical_value"],
    }
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
