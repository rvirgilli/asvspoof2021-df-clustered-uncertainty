# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy==2.4.2", "numba==0.64.0"]
# ///
"""Fail-closed fixed-roster ASV5 analysis for EXP-106 Amendments 5--6.

This is deliberately separate from both historical ``analyze_asv5.py`` and
the stopped v2 confidence driver.  It emits descriptive perturbation bands and
never maps the registered numeric summaries to an inferential verdict.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import platform
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numba
import numpy as np
from numpy.lib.format import open_memmap

from asv5_descriptive_core import (
    ARM_NAMESPACES,
    B_FROZEN,
    SEED_FROZEN,
    SYSTEM_ORDER,
    DescriptiveContractError,
    combine_summaries,
    one_replicate,
    point_eers,
    summarize_arm,
)


class InputContractError(ValueError):
    """A pre-outcome Amendment-5/6 input condition failed."""


@dataclass(frozen=True)
class ContractSpec:
    protocol_sha256: str
    manifest_sha256: str
    incidence_sha256: str
    n_trials: int
    n_bonafide: int
    n_spoof: int
    n_target: int
    n_non_target: int
    n_attacks: int
    n_codecs: int
    n_speaker_attack_cells: int


REAL_SPEC = ContractSpec(
    protocol_sha256="62cc6d5e30eb7624ab348ea21713cce5d814299d723b4ce789ec9c1cf18611f2",
    manifest_sha256="c45659c79aab45bc58a6730c6d0ebb908e83fe23cf0c31c6ac9a8aafdc5842cb",
    incidence_sha256="e5afcffa8f69e0ff5fe78fe34341174383cff2c169f55b558f3344b30d2fc771",
    n_trials=680_774,
    n_bonafide=138_688,
    n_spoof=542_086,
    n_target=367,
    n_non_target=370,
    n_attacks=16,
    n_codecs=12,
    n_speaker_attack_cells=5_872,
)


@dataclass(frozen=True)
class ProtocolRow:
    speaker: str
    utterance: str
    gender: str
    codec: str
    codec_index: str
    source: str
    attack_condition: str
    attack: str
    label: str
    tail: str


@dataclass(frozen=True)
class ScoreConfig:
    name: str
    path: Path
    kind: str
    sidecar: Path | None = None
    expected_model: str | None = None


@dataclass(frozen=True)
class AnalysisConfig:
    protocol: Path
    manifest: Path
    incidence: Path
    scores: tuple[ScoreConfig, ...]
    amendment5: Path
    amendment6: Path
    static_audit: Path
    core: Path
    core_tests: Path
    analyzer_tests: Path
    sealed_reference: Path
    run_contract: Path
    result: Path
    checkpoint_dir: Path
    config_path: Path

    @classmethod
    def from_json(cls, path: str | Path) -> "AnalysisConfig":
        config_path = Path(path).resolve()
        try:
            payload = json.loads(config_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise InputContractError(f"invalid config {config_path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise InputContractError("config must be a JSON object")
        base = config_path.parent

        def resolved(value: object, label: str) -> Path:
            if not isinstance(value, str) or not value:
                raise InputContractError(f"{label} must be a path string")
            candidate = Path(value).expanduser()
            return (candidate if candidate.is_absolute() else base / candidate).resolve()

        score_rows = payload.get("scores")
        if not isinstance(score_rows, list):
            raise InputContractError("config scores must be a list")
        scores: list[ScoreConfig] = []
        for index, row in enumerate(score_rows):
            if not isinstance(row, dict):
                raise InputContractError(f"scores[{index}] must be an object")
            sidecar = row.get("sidecar")
            scores.append(
                ScoreConfig(
                    name=str(row.get("name", "")),
                    path=resolved(row.get("path"), f"scores[{index}].path"),
                    kind=str(row.get("kind", "")),
                    sidecar=(
                        resolved(sidecar, f"scores[{index}].sidecar")
                        if sidecar is not None
                        else None
                    ),
                    expected_model=(
                        str(row["expected_model"])
                        if row.get("expected_model") is not None
                        else None
                    ),
                )
            )
        artifacts = payload.get("artifacts")
        outputs = payload.get("outputs")
        if not isinstance(artifacts, dict) or not isinstance(outputs, dict):
            raise InputContractError("config requires artifacts and outputs objects")
        return cls(
            protocol=resolved(payload.get("protocol"), "protocol"),
            manifest=resolved(payload.get("manifest"), "manifest"),
            incidence=resolved(payload.get("incidence"), "incidence"),
            scores=tuple(scores),
            amendment5=resolved(artifacts.get("amendment5"), "artifacts.amendment5"),
            amendment6=resolved(artifacts.get("amendment6"), "artifacts.amendment6"),
            static_audit=resolved(
                artifacts.get("static_audit"), "artifacts.static_audit"
            ),
            core=resolved(artifacts.get("core"), "artifacts.core"),
            core_tests=resolved(artifacts.get("core_tests"), "artifacts.core_tests"),
            analyzer_tests=resolved(
                artifacts.get("analyzer_tests"), "artifacts.analyzer_tests"
            ),
            sealed_reference=resolved(
                artifacts.get("sealed_reference"), "artifacts.sealed_reference"
            ),
            run_contract=resolved(outputs.get("run_contract"), "outputs.run_contract"),
            result=resolved(outputs.get("result"), "outputs.result"),
            checkpoint_dir=resolved(
                outputs.get("checkpoint_dir"), "outputs.checkpoint_dir"
            ),
            config_path=config_path,
        )


@dataclass(frozen=True)
class ValidatedData:
    config: AnalysisConfig
    rows: tuple[ProtocolRow, ...]
    manifest_order: tuple[str, ...]
    labels: np.ndarray
    target_index: np.ndarray
    non_target_index: np.ndarray
    attack_index: np.ndarray
    scores: np.ndarray
    snapshot: Mapping[str, object]
    run_contract_payload: Mapping[str, object]
    run_contract_sha256: str


def sha256_file(path: str | Path) -> str:
    source = Path(path)
    if not source.is_file():
        raise InputContractError(f"required file is missing: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_json_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def write_json_atomic(path: str | Path, payload: object, *, allow_identical: bool) -> None:
    target = Path(path)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if target.exists():
        if allow_identical and target.read_text() == serialized:
            return
        raise InputContractError(f"refusing to overwrite {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_protocol(path: str | Path) -> tuple[ProtocolRow, ...]:
    rows: list[ProtocolRow] = []
    seen: set[str] = set()
    try:
        lines = Path(path).read_text().splitlines()
    except OSError as exc:
        raise InputContractError(f"cannot read protocol {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        fields = line.split()
        if len(fields) != 10:
            raise InputContractError(
                f"protocol line {line_number}: expected 10 fields, got {len(fields)}"
            )
        row = ProtocolRow(*fields)
        if row.utterance in seen:
            raise InputContractError(f"duplicate protocol utterance {row.utterance}")
        if row.label not in {"bonafide", "spoof"}:
            raise InputContractError(f"invalid protocol label {row.label!r}")
        # The official ASVspoof 5 protocol encodes the attack column itself as
        # ``bonafide`` for bona-fide trials; ``-`` belongs to the adjacent
        # attack-condition column.  Keep this literal so a shifted/wrong
        # schema fails before any score is oriented or summarized.
        if (row.label == "bonafide") != (row.attack == "bonafide"):
            raise InputContractError(f"protocol attack/label mismatch for {row.utterance}")
        seen.add(row.utterance)
        rows.append(row)
    return tuple(rows)


def parse_manifest(path: str | Path) -> tuple[tuple[str, ...], Mapping[str, str]]:
    try:
        with Path(path).open(newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None:
                raise InputContractError("manifest has no header")
            id_fields = [field for field in ("utt_id", "utt") if field in reader.fieldnames]
            if len(id_fields) != 1 or "label" not in reader.fieldnames:
                raise InputContractError("manifest requires one of utt_id/utt and label")
            id_field = id_fields[0]
            order: list[str] = []
            labels: dict[str, str] = {}
            for line_number, row in enumerate(reader, start=2):
                utterance = str(row.get(id_field, ""))
                label = str(row.get("label", ""))
                if not utterance or utterance in labels:
                    raise InputContractError(
                        f"manifest line {line_number}: missing/duplicate utterance"
                    )
                if label not in {"bonafide", "spoof"}:
                    raise InputContractError(
                        f"manifest line {line_number}: invalid label {label!r}"
                    )
                order.append(utterance)
                labels[utterance] = label
    except OSError as exc:
        raise InputContractError(f"cannot read manifest {path}: {exc}") from exc
    return tuple(order), labels


def validate_protocol_and_manifest(
    rows: Sequence[ProtocolRow],
    manifest_order: Sequence[str],
    manifest_labels: Mapping[str, str],
    spec: ContractSpec,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, Mapping[str, object]]:
    if len(rows) != spec.n_trials or len(manifest_order) != spec.n_trials:
        raise InputContractError("protocol/manifest trial count mismatch")
    by_id = {row.utterance: row for row in rows}
    if len(by_id) != spec.n_trials or set(by_id) != set(manifest_order):
        raise InputContractError("protocol/manifest utterance sets differ")
    for utterance in manifest_order:
        if by_id[utterance].label != manifest_labels[utterance]:
            raise InputContractError(f"manifest label mismatch for {utterance}")
    ordered = tuple(by_id[utterance] for utterance in manifest_order)
    counts = Counter(row.label for row in ordered)
    if counts != Counter({"bonafide": spec.n_bonafide, "spoof": spec.n_spoof}):
        raise InputContractError(f"class counts mismatch: {dict(counts)}")
    bona_speakers = {row.speaker for row in ordered if row.label == "bonafide"}
    spoof_speakers = {row.speaker for row in ordered if row.label == "spoof"}
    target = tuple(sorted(bona_speakers & spoof_speakers))
    non_target = tuple(sorted(bona_speakers - spoof_speakers))
    if set(target) != spoof_speakers or set(target) & set(non_target):
        raise InputContractError("speaker roles are not target-both/non-target-bona-only")
    if len(target) != spec.n_target or len(non_target) != spec.n_non_target:
        raise InputContractError("speaker-role counts differ from contract")
    attacks = tuple(sorted({row.attack for row in ordered if row.label == "spoof"}))
    codecs = tuple(sorted({row.codec for row in ordered}))
    if len(attacks) != spec.n_attacks or len(codecs) != spec.n_codecs:
        raise InputContractError("attack/codec counts differ from contract")
    observed_cells = {
        (row.speaker, row.attack) for row in ordered if row.label == "spoof"
    }
    possible_cells = {(speaker, attack) for speaker in target for attack in attacks}
    if observed_cells != possible_cells or len(observed_cells) != spec.n_speaker_attack_cells:
        raise InputContractError("target-speaker x attack incidence is not complete")
    source_speakers: dict[str, set[str]] = defaultdict(set)
    for row in ordered:
        if row.source != "-":
            source_speakers[row.source].add(row.speaker)
    if any(len(speakers) > 1 for speakers in source_speakers.values()):
        raise InputContractError("a source recording crosses speakers")
    target_lookup = {speaker: index for index, speaker in enumerate(target)}
    non_target_lookup = {speaker: index for index, speaker in enumerate(non_target)}
    attack_lookup = {attack: index for index, attack in enumerate(attacks)}
    labels = np.asarray([1 if row.label == "bonafide" else 0 for row in ordered], dtype=np.int8)
    target_index = np.asarray(
        [target_lookup.get(row.speaker, -1) for row in ordered], dtype=np.int64
    )
    non_target_index = np.asarray(
        [non_target_lookup.get(row.speaker, -1) for row in ordered], dtype=np.int64
    )
    attack_index = np.asarray(
        [attack_lookup.get(row.attack, -1) if row.label == "spoof" else -1 for row in ordered],
        dtype=np.int64,
    )
    trial_digest = hashlib.sha256()
    for row in ordered:
        trial_digest.update(
            (
                "\t".join(
                    (row.utterance, row.label, row.speaker, row.attack, row.codec)
                )
                + "\n"
            ).encode("utf-8")
        )

    def sequence_digest(values: Sequence[str]) -> str:
        return hashlib.sha256(("\n".join(values) + "\n").encode("utf-8")).hexdigest()

    summary = {
        "n_trials": len(ordered),
        "n_bonafide": int((labels == 1).sum()),
        "n_spoof": int((labels == 0).sum()),
        "n_target": len(target),
        "n_non_target": len(non_target),
        "n_attacks": len(attacks),
        "n_codecs": len(codecs),
        "speaker_attack_cells": len(observed_cells),
        "source_recordings_crossing_speakers": 0,
        "ordered_trial_join_sha256": trial_digest.hexdigest(),
        "target_speaker_set_sha256": sequence_digest(target),
        "non_target_speaker_set_sha256": sequence_digest(non_target),
        "attack_set_sha256": sequence_digest(attacks),
        "codec_set_sha256": sequence_digest(codecs),
    }
    return labels, target_index, non_target_index, attack_index, summary


def score_files(config: ScoreConfig) -> tuple[Path, ...]:
    if config.kind == "npz_dir":
        if not config.path.is_dir():
            raise InputContractError(f"score directory is missing: {config.path}")
        files = tuple(sorted(config.path.glob("*.npz")))
        if not files:
            raise InputContractError(f"score directory contains no NPZ: {config.path}")
        return files
    if config.kind == "delimited":
        if not config.path.is_file():
            raise InputContractError(f"score file is missing: {config.path}")
        return (config.path,)
    raise InputContractError(f"unknown score kind {config.kind!r}")


def file_record(path: Path) -> Mapping[str, object]:
    return {
        "path": str(path.resolve()),
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def snapshot_inputs(config: AnalysisConfig) -> Mapping[str, object]:
    score_records: dict[str, object] = {}
    for score in config.scores:
        files = [file_record(path) for path in score_files(score)]
        sidecar = file_record(score.sidecar) if score.sidecar is not None else None
        score_records[score.name] = {
            "kind": score.kind,
            "path": str(score.path.resolve()),
            "files": files,
            "sidecar": sidecar,
            "legacy_input_ledger_not_historical_run_provenance": score.sidecar is None,
        }
    artifacts = {
        "config": file_record(config.config_path),
        "protocol": file_record(config.protocol),
        "manifest": file_record(config.manifest),
        "incidence": file_record(config.incidence),
        "amendment5": file_record(config.amendment5),
        "amendment6": file_record(config.amendment6),
        "static_audit": file_record(config.static_audit),
        "core": file_record(config.core),
        "core_tests": file_record(config.core_tests),
        "analyzer": file_record(Path(__file__).resolve()),
        "analyzer_tests": file_record(config.analyzer_tests),
        "sealed_reference": file_record(config.sealed_reference),
    }
    return {"artifacts": artifacts, "scores": score_records}


def _decode_id(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _open_delimited(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", newline="")
    return path.open(newline="")


def load_score_map(config: ScoreConfig) -> Mapping[str, float]:
    values: dict[str, float] = {}
    for path in score_files(config):
        if path.suffix == ".npz":
            try:
                # The audited legacy chunks store IDs as native Unicode and
                # scores as float32.  Pickled object arrays are not accepted.
                with np.load(path, allow_pickle=False) as payload:
                    ids = payload["utt_id"] if "utt_id" in payload else payload["utt"]
                    scores = payload["score"]
                    if len(ids) != len(scores):
                        raise InputContractError(f"array length mismatch in {path}")
                    for raw_id, raw_score in zip(ids, scores):
                        utterance = _decode_id(raw_id)
                        if utterance in values:
                            raise InputContractError(
                                f"{config.name}: duplicate score ID {utterance}"
                            )
                        values[utterance] = float(raw_score)
            except (OSError, KeyError, ValueError) as exc:
                if isinstance(exc, InputContractError):
                    raise
                raise InputContractError(f"cannot parse score chunk {path}: {exc}") from exc
            continue
        delimiter = "\t" if ".tsv" in path.suffixes or path.suffix == ".tsv" else ","
        try:
            with _open_delimited(path) as stream:
                reader = csv.DictReader(stream, delimiter=delimiter)
                if reader.fieldnames is None:
                    raise InputContractError(f"score file has no header: {path}")
                id_fields = [field for field in ("utt_id", "utt") if field in reader.fieldnames]
                if len(id_fields) != 1 or "score" not in reader.fieldnames:
                    raise InputContractError(
                        f"score file {path} requires one of utt_id/utt plus score"
                    )
                id_field = id_fields[0]
                for line_number, row in enumerate(reader, start=2):
                    utterance = str(row.get(id_field, ""))
                    if not utterance or utterance in values:
                        raise InputContractError(
                            f"{config.name} line {line_number}: missing/duplicate score ID"
                        )
                    try:
                        values[utterance] = float(row["score"])
                    except (TypeError, ValueError) as exc:
                        raise InputContractError(
                            f"{config.name} line {line_number}: invalid score"
                        ) from exc
        except OSError as exc:
            raise InputContractError(f"cannot read score file {path}: {exc}") from exc
    return values


def validate_sidecar(config: ScoreConfig, spec: ContractSpec) -> Mapping[str, object] | None:
    if config.sidecar is None:
        return None
    try:
        payload = json.loads(config.sidecar.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise InputContractError(f"invalid score sidecar {config.sidecar}: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputContractError(f"score sidecar is not an object: {config.sidecar}")
    if payload.get("schema_version") != 1:
        raise InputContractError(f"{config.name}: sidecar schema mismatch")
    if payload.get("score_contract") != "higher_is_bonafide":
        raise InputContractError(f"{config.name}: sidecar orientation mismatch")
    if payload.get("manifest_sha256") != spec.manifest_sha256:
        raise InputContractError(f"{config.name}: sidecar manifest hash mismatch")
    if config.expected_model is not None and payload.get("model") != config.expected_model:
        raise InputContractError(f"{config.name}: sidecar model mismatch")
    return payload


def validate_pre_outcome(
    config: AnalysisConfig, spec: ContractSpec = REAL_SPEC
) -> ValidatedData:
    if tuple(score.name for score in config.scores) != SYSTEM_ORDER:
        raise InputContractError("score inputs do not follow the frozen system order")
    if len({score.path.resolve() for score in config.scores}) != len(SYSTEM_ORDER):
        raise InputContractError("score input paths are not unique")
    for path, expected, label in (
        (config.protocol, spec.protocol_sha256, "protocol"),
        (config.manifest, spec.manifest_sha256, "manifest"),
        (config.incidence, spec.incidence_sha256, "incidence"),
    ):
        observed = sha256_file(path)
        if observed != expected:
            raise InputContractError(
                f"{label} hash mismatch: observed={observed}, expected={expected}"
            )
    initial_snapshot = snapshot_inputs(config)
    rows = parse_protocol(config.protocol)
    manifest_order, manifest_labels = parse_manifest(config.manifest)
    labels, target, non_target, attacks, structure = validate_protocol_and_manifest(
        rows, manifest_order, manifest_labels, spec
    )
    expected_ids = set(manifest_order)
    arrays: list[np.ndarray] = []
    sidecars: dict[str, object] = {}
    for score in config.scores:
        sidecars[score.name] = validate_sidecar(score, spec)
        score_map = load_score_map(score)
        observed_ids = set(score_map)
        if observed_ids != expected_ids:
            raise InputContractError(
                f"{score.name}: roster mismatch missing={len(expected_ids-observed_ids)}, "
                f"extra={len(observed_ids-expected_ids)}"
            )
        vector = np.asarray([score_map[utterance] for utterance in manifest_order], dtype=np.float64)
        if not np.isfinite(vector).all():
            raise InputContractError(f"{score.name}: nonfinite score")
        arrays.append(vector)
    if snapshot_inputs(config) != initial_snapshot:
        raise InputContractError("an input mutated during the identity phase")
    scores = np.vstack(arrays)
    payload = {
        "schema_version": 1,
        "experiment": "EXP-106-amendment5-fixed-roster-descriptive",
        "scientific_role": "fixed-roster descriptive perturbation sensitivity; not population inference",
        "constants": {
            "B": B_FROZEN,
            "seed": SEED_FROZEN,
            "systems": list(SYSTEM_ORDER),
            "arm_namespaces": dict(ARM_NAMESPACES),
            "eer_rule": "position-wise first-argmin weighted EER with quicksort order",
            "percentile_method": "linear",
            "max_t_center": "bootstrap-column-mean",
        },
        "structure": structure,
        "inputs": initial_snapshot,
        "score_sidecars_validated": sidecars,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "numba": numba.__version__,
        },
    }
    write_json_atomic(config.run_contract, payload, allow_identical=True)
    run_hash = sha256_file(config.run_contract)
    if snapshot_inputs(config) != initial_snapshot:
        raise InputContractError("an input mutated before the outcome phase")
    return ValidatedData(
        config=config,
        rows=rows,
        manifest_order=manifest_order,
        labels=labels,
        target_index=target,
        non_target_index=non_target,
        attack_index=attacks,
        scores=scores,
        snapshot=initial_snapshot,
        run_contract_payload=payload,
        run_contract_sha256=run_hash,
    )


def verify_snapshot(validated: ValidatedData) -> None:
    if snapshot_inputs(validated.config) != validated.snapshot:
        raise InputContractError("an input changed after run-contract commit")
    if sha256_file(validated.config.run_contract) != validated.run_contract_sha256:
        raise InputContractError("run contract changed after commit")


def checkpoint_for_arm(
    validated: ValidatedData,
    arm: str,
    *,
    B: int = B_FROZEN,
) -> np.memmap:
    directory = validated.config.checkpoint_dir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{arm}.B{B}.npy"
    sidecar_path = directory / f"{arm}.B{B}.checkpoint.json"
    state = {
        "schema_version": 1,
        "arm": arm,
        "namespace": ARM_NAMESPACES[arm],
        "B": B,
        "seed": SEED_FROZEN,
        "systems": list(SYSTEM_ORDER),
        "run_contract_sha256": validated.run_contract_sha256,
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
        "core_sha256": sha256_file(validated.config.core),
    }
    if path.exists() or sidecar_path.exists():
        if not (path.exists() and sidecar_path.exists()):
            raise InputContractError(f"partial checkpoint state for {arm}")
        try:
            observed_state = json.loads(sidecar_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise InputContractError(f"invalid checkpoint sidecar for {arm}: {exc}") from exc
        if observed_state != state:
            raise InputContractError(f"checkpoint contract mismatch for {arm}")
        output = np.load(path, mmap_mode="r+")
        if output.shape != (B, len(SYSTEM_ORDER)) or output.dtype != np.float64:
            raise InputContractError(f"checkpoint array mismatch for {arm}")
    else:
        output = open_memmap(
            path, mode="w+", dtype=np.float64, shape=(B, len(SYSTEM_ORDER))
        )
        output[:] = np.nan
        output.flush()
        write_json_atomic(sidecar_path, state, allow_identical=False)
    finite = np.isfinite(output)
    row_finite = finite.all(axis=1)
    row_nan = np.isnan(output).all(axis=1)
    if not np.all(row_finite | row_nan):
        raise InputContractError(f"mixed/nonfinite checkpoint row for {arm}")
    return output


def run_arm(validated: ValidatedData, orders: np.ndarray, arm: str) -> np.ndarray:
    verify_snapshot(validated)
    output = checkpoint_for_arm(validated, arm)
    pending = np.flatnonzero(np.isnan(output).all(axis=1))
    progress_step = max(1, len(pending) // 20)
    for completed, replicate in enumerate(pending, start=1):
        output[replicate] = one_replicate(
            arm,
            int(replicate),
            orders,
            validated.labels,
            validated.target_index,
            validated.non_target_index,
            validated.attack_index,
        )
        if completed <= 3 or completed % progress_step == 0 or completed == len(pending):
            output.flush()
            print(f"{arm}: completed {completed}/{len(pending)} pending", flush=True)
    if not np.isfinite(output).all():
        raise InputContractError(f"arm {arm} did not finish all replicates")
    verify_snapshot(validated)
    return np.asarray(output)


def run_outcomes(validated: ValidatedData) -> Mapping[str, object]:
    verify_snapshot(validated)
    bona = validated.labels == 1
    orientation: dict[str, object] = {}
    for system, vector in zip(SYSTEM_ORDER, validated.scores):
        median_bona = float(np.median(vector[bona]))
        median_spoof = float(np.median(vector[~bona]))
        if not median_bona > median_spoof:
            raise InputContractError(
                f"{system}: orientation gate failed median_bona={median_bona}, "
                f"median_spoof={median_spoof}"
            )
        orientation[system] = {
            "median_bonafide": median_bona,
            "median_spoof": median_spoof,
            "bonafide_score_is_higher": True,
        }
    orders = np.asarray(
        [np.argsort(vector, kind="quicksort") for vector in validated.scores],
        dtype=np.int64,
    )
    point = point_eers(orders, validated.labels)
    arm_replicates: dict[str, np.ndarray] = {}
    arm_summaries: dict[str, Mapping[str, object]] = {}
    for arm in ("trial_iid", "speaker_attack", "speaker_only"):
        arm_replicates[arm] = run_arm(validated, orders, arm)
        arm_summaries[arm] = summarize_arm(
            arm_replicates[arm], point, arm=arm, system_order=SYSTEM_ORDER
        )
    comparison = combine_summaries(
        arm_summaries["trial_iid"],
        arm_summaries["speaker_attack"],
        arm_summaries["speaker_only"],
    )
    verify_snapshot(validated)
    return {
        "schema_version": 1,
        "experiment": "EXP-106-amendment5-fixed-roster-descriptive",
        "scientific_role": "fixed-roster descriptive perturbation sensitivity; not population inference",
        "run_contract": {
            "path": str(validated.config.run_contract),
            "sha256": validated.run_contract_sha256,
        },
        "orientation": orientation,
        "pooled_fixed_roster_eer_percent": {
            system: float(point[index]) for index, system in enumerate(SYSTEM_ORDER)
        },
        "arms": arm_summaries,
        "comparison": comparison,
        "point_statistics_identical_across_arms": True,
        "interpretation_boundary": {
            "procedure_bands_have_population_coverage": False,
            "zero_exclusion_has_population_interpretation": False,
            "acquisition_population_claim_authorized": False,
        },
    }


def run_driver(config: AnalysisConfig, spec: ContractSpec = REAL_SPEC) -> Mapping[str, object]:
    if config.result.exists():
        raise InputContractError(f"refusing to overwrite result {config.result}")
    validated = validate_pre_outcome(config, spec)
    result = run_outcomes(validated)
    write_json_atomic(config.result, result, allow_identical=False)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    config = AnalysisConfig.from_json(args.config)
    result = run_driver(config)
    print(
        "wrote descriptive result",
        config.result,
        "numeric criteria true=",
        result["comparison"]["registered_descriptive_summaries"]["n_true"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
