#!/usr/bin/env python3
"""Verify the frozen EXP-115 delivery and its optional licensed inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


FREEZE_COMMIT = "49b9057b7edba43c3914897d31fdb7917737c379"
EXPECTED_MANIFEST_SHA256 = (
    "008371adaeb300401357a58035d3c4ac9e1c440abe804ceab8ccd1bdc84b2544"
)
EXPECTED_JOINT_RESULT_SHA256 = (
    "ff999f5b35ecc77c92299037a07a1700dbed1f88c5ff874a5cbfc3222a6836ae"
)
EXPECTED_SCORE_SHA256 = {
    "aasist": "6e75ff20e525713a800e47d756d289604e145f868eed174809c4983fcedac2ad",
    "ssl_aasist": "f0237f3712c435157d2cbd5f84f403acf6bea23e2c5553210f8fe276a82743b5",
    "sls": "4e83b949a51de18866dd2021559cfe4dcab5df6ff028080e28c7b2c82b8d28c9",
    "xlsr_mamba": "5d4c6ca9cc4be52746f7cc1ae2b1007e5dc5e1ca01ddd1221b9560236f1ff835",
}
ARRAYS = ("SPEAKER-ONLY-BOOTSTRAP.npy", "ATTACK-ONLY-BOOTSTRAP.npy")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise ValueError(f"{label} hash mismatch: {observed} != {expected}")


def verify_freeze(directory: Path) -> None:
    freeze = directory / "FREEZE.sha256"
    if not freeze.is_file():
        raise FileNotFoundError("missing FREEZE.sha256")
    for raw in freeze.read_text().splitlines():
        digest, name = raw.split("  ", 1)
        require_hash(directory / name, digest, f"frozen file {name}")


def expected_bindings(directory: Path) -> dict[str, str]:
    return {
        "RESULTS.json": sha256_file(directory / "RESULTS.json"),
        **{name: sha256_file(directory / name) for name in ARRAYS},
        "FREEZE.sha256": sha256_file(directory / "FREEZE.sha256"),
        "EXP-114-PROVENANCE-RERUN-RESULTS.json": EXPECTED_JOINT_RESULT_SHA256,
        "manifest": EXPECTED_MANIFEST_SHA256,
        **{
            f"score:{system}": digest
            for system, digest in EXPECTED_SCORE_SHA256.items()
        },
    }


def verify_artifacts(directory: Path) -> dict:
    verify_freeze(directory)
    result_path = directory / "RESULTS.json"
    receipt_path = directory / "RUN-RECEIPT.json"
    if not result_path.is_file() or not receipt_path.is_file():
        raise FileNotFoundError("missing result or receipt")
    result = json.loads(result_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("status") != "complete":
        raise ValueError("receipt is not complete")
    if receipt.get("evidence_status") != "post-result mechanism diagnostic":
        raise ValueError("receipt evidence status mismatch")
    if receipt.get("git_head") != FREEZE_COMMIT:
        raise ValueError("receipt freeze commit mismatch")
    observed_bindings = receipt.get("bindings")
    current_bindings = expected_bindings(directory)
    if observed_bindings != current_bindings:
        differing = sorted({
            *set(observed_bindings or {}), *set(current_bindings),
        } - {
            key for key in set(observed_bindings or {}) & set(current_bindings)
            if observed_bindings[key] == current_bindings[key]
        })
        raise ValueError(f"receipt binding mismatch: {differing}")
    provenance = result.get("provenance", {})
    if provenance.get("git_head") != FREEZE_COMMIT:
        raise ValueError("result freeze commit mismatch")
    if provenance.get("experiment_git_status_before_run") != "":
        raise ValueError("analysis did not start from a clean experiment tree")
    inputs = provenance.get("inputs", {})
    if inputs.get("manifest", {}).get("sha256") != EXPECTED_MANIFEST_SHA256:
        raise ValueError("result manifest binding mismatch")
    if inputs.get("joint_result", {}).get("sha256") != EXPECTED_JOINT_RESULT_SHA256:
        raise ValueError("result joint binding mismatch")
    if {
        system: row.get("sha256")
        for system, row in inputs.get("scores", {}).items()
    } != EXPECTED_SCORE_SHA256:
        raise ValueError("result score bindings mismatch")
    arrays = provenance.get("bootstrap_arrays", {})
    for name in ARRAYS:
        path = directory / name
        recorded = arrays.get(name, {})
        require_hash(path, recorded.get("sha256", ""), f"result-bound array {name}")
        values = np.load(path, allow_pickle=False)
        if list(values.shape) != recorded.get("shape") or str(values.dtype) != recorded.get("dtype"):
            raise ValueError(f"array metadata mismatch: {name}")
        if values.shape != (5000, 4) or values.dtype != np.float64:
            raise ValueError(f"unexpected frozen array contract: {name}")
        if not np.all(np.isfinite(values)):
            raise ValueError(f"non-finite bootstrap values: {name}")
    if result.get("arm_speaker_only", {}).get("simultaneous_excluding_zero") != 5:
        raise ValueError("speaker-only endpoint mismatch")
    if result.get("arm_attack_only", {}).get("simultaneous_excluding_zero") != 3:
        raise ValueError("attack-only endpoint mismatch")
    return result


def verify_external_inputs(
    manifest: Path, joint_result: Path, scores: dict[str, Path],
) -> None:
    require_hash(manifest, EXPECTED_MANIFEST_SHA256, "manifest")
    require_hash(joint_result, EXPECTED_JOINT_RESULT_SHA256, "EXP-114 result")
    if set(scores) != set(EXPECTED_SCORE_SHA256):
        raise ValueError("external score family mismatch")
    for system, expected in EXPECTED_SCORE_SHA256.items():
        require_hash(scores[system], expected, f"{system} scores")


def parse_scores(values: list[str]) -> dict[str, Path]:
    scores = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"score argument must be NAME=PATH: {value}")
        system, raw_path = value.split("=", 1)
        if system in scores:
            raise ValueError(f"duplicate score argument: {system}")
        scores[system] = Path(raw_path)
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--joint-result", type=Path)
    parser.add_argument("--score", action="append", default=[])
    args = parser.parse_args()
    verify_artifacts(args.directory)
    supplied = args.manifest is not None or args.joint_result is not None or bool(args.score)
    if supplied:
        if args.manifest is None or args.joint_result is None or not args.score:
            raise ValueError("licensed input verification requires every input argument")
        verify_external_inputs(
            args.manifest, args.joint_result, parse_scores(args.score),
        )
    print("PASS — EXP-115 receipt, freeze, arrays, results and bindings verify")


if __name__ == "__main__":
    main()
