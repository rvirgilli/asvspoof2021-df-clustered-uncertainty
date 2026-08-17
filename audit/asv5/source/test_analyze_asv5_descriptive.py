#!/usr/bin/env python3
"""Synthetic fail-closed tests for the Amendment-5 descriptive executor."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analyze_asv5_descriptive import (
    AnalysisConfig,
    ContractSpec,
    InputContractError,
    checkpoint_for_arm,
    parse_protocol,
    run_outcomes,
    sha256_file,
    validate_pre_outcome,
    verify_snapshot,
)


HERE = Path(__file__).resolve().parent


def write_protocol(path: Path) -> list[tuple[str, str]]:
    rows = [
        ("t0", "t0b", "M", "c0", "0", "src-t0b", "-", "bonafide", "bonafide", "-"),
        ("t1", "t1b", "F", "c1", "1", "src-t1b", "-", "bonafide", "bonafide", "-"),
        ("n0", "n0b", "M", "c0", "0", "src-n0b", "-", "bonafide", "bonafide", "-"),
        ("n1", "n1b", "F", "c1", "1", "src-n1b", "-", "bonafide", "bonafide", "-"),
        ("t0", "t0a0", "M", "c0", "0", "src-t0a0", "x", "a0", "spoof", "-"),
        ("t0", "t0a1", "M", "c1", "1", "src-t0a1", "x", "a1", "spoof", "-"),
        ("t1", "t1a0", "F", "c0", "0", "src-t1a0", "x", "a0", "spoof", "-"),
        ("t1", "t1a1", "F", "c1", "1", "src-t1a1", "x", "a1", "spoof", "-"),
    ]
    path.write_text("\n".join(" ".join(row) for row in rows) + "\n")
    return [(row[1], row[8]) for row in rows]


def write_manifest(path: Path, trials: list[tuple[str, str]]) -> list[str]:
    order = [trials[index][0] for index in (3, 0, 6, 2, 5, 1, 7, 4)]
    label = dict(trials)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["utt_id", "path", "label"])
        writer.writeheader()
        for utterance in order:
            writer.writerow(
                {"utt_id": utterance, "path": f"/synthetic/{utterance}.wav", "label": label[utterance]}
            )
    return order


def synthetic_scores(order: list[str]) -> list[dict[str, float]]:
    # Ascending-score orders.  Each system has a distinct mixture of classes
    # and a distinct within-class speaker/attack ordering, while retaining a
    # strictly higher bona-fide median.
    ascending = (
        ("t0a0", "t0b", "t0a1", "t1b", "t1a0", "n0b", "t1a1", "n1b"),
        ("t1a1", "t0a1", "n0b", "t0a0", "t0b", "t1a0", "n1b", "t1b"),
        ("t1a0", "n1b", "t0a0", "t1a1", "t0b", "n0b", "t0a1", "t1b"),
        ("t0a1", "t1a0", "t0b", "n1b", "t1a1", "t1b", "t0a0", "n0b"),
    )
    return [
        {utterance: float(rank) for rank, utterance in enumerate(system_order)}
        for system_order in ascending
    ]


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.protocol = root / "protocol.tsv"
        self.manifest = root / "manifest.csv"
        self.incidence = root / "incidence.json"
        trials = write_protocol(self.protocol)
        order = write_manifest(self.manifest, trials)
        self.incidence.write_text(json.dumps({"synthetic": True}) + "\n")
        score_maps = synthetic_scores(order)
        names = ("SSL-AASIST", "AASIST", "XLS-R+SLS", "XLSR-Mamba")
        score_rows = []
        for index, (name, mapping) in enumerate(zip(names, score_maps)):
            if index < 2:
                directory = root / f"legacy-{index}"
                directory.mkdir()
                halfway = len(order) // 2
                for chunk, subset in enumerate((order[:halfway], order[halfway:])):
                    np.savez(
                        directory / f"chunk-{chunk}.npz",
                        utt_id=np.asarray(subset),
                        score=np.asarray([mapping[utterance] for utterance in subset]),
                    )
                score_rows.append({"name": name, "path": str(directory), "kind": "npz_dir"})
            else:
                path = root / f"new-{index}.tsv"
                with path.open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=["utt", "score"], delimiter="\t")
                    writer.writeheader()
                    for utterance in order:
                        writer.writerow({"utt": utterance, "score": mapping[utterance]})
                sidecar = path.with_suffix(path.suffix + ".run.json")
                model = "sls" if index == 2 else "xlsr_mamba"
                sidecar.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "score_contract": "higher_is_bonafide",
                            "manifest_sha256": sha256_file(self.manifest),
                            "model": model,
                        }
                    )
                    + "\n"
                )
                score_rows.append(
                    {
                        "name": name,
                        "path": str(path),
                        "kind": "delimited",
                        "sidecar": str(sidecar),
                        "expected_model": model,
                    }
                )
        self.config_path = root / "config.json"
        self.run_contract = root / "run-contract.json"
        self.result = root / "result.json"
        self.checkpoints = root / "checkpoints"
        payload = {
            "protocol": str(self.protocol),
            "manifest": str(self.manifest),
            "incidence": str(self.incidence),
            "scores": score_rows,
            "artifacts": {
                "amendment5": str(HERE / "AMENDMENT-5-fixed-roster-descriptive.md"),
                "amendment6": str(HERE / "AMENDMENT-6-descriptive-executor.md"),
                "static_audit": str(HERE / "STATIC-AUDIT-descriptive-executor.md"),
                "core": str(HERE / "asv5_descriptive_core.py"),
                "core_tests": str(HERE / "test_asv5_descriptive_core.py"),
                "analyzer_tests": str(Path(__file__).resolve()),
                "sealed_reference": str(HERE.parent / "EXP-101-m1-campaign" / "exp101_matched_iid.py"),
            },
            "outputs": {
                "run_contract": str(self.run_contract),
                "result": str(self.result),
                "checkpoint_dir": str(self.checkpoints),
            },
        }
        self.config_path.write_text(json.dumps(payload, indent=2) + "\n")
        self.config = AnalysisConfig.from_json(self.config_path)
        self.spec = ContractSpec(
            protocol_sha256=sha256_file(self.protocol),
            manifest_sha256=sha256_file(self.manifest),
            incidence_sha256=sha256_file(self.incidence),
            n_trials=8,
            n_bonafide=4,
            n_spoof=4,
            n_target=2,
            n_non_target=2,
            n_attacks=2,
            n_codecs=2,
            n_speaker_attack_cells=4,
        )


class DescriptiveAnalyzerTests(unittest.TestCase):
    def test_official_bonafide_attack_token_is_literal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            protocol = Path(directory) / "protocol.tsv"
            protocol.write_text("s u F - 0 - - bonafide bonafide -\n")
            self.assertEqual(parse_protocol(protocol)[0].attack, "bonafide")
            protocol.write_text("s u F - 0 - - - bonafide -\n")
            with self.assertRaises(InputContractError):
                parse_protocol(protocol)

    def test_identity_phase_commits_before_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            validated = validate_pre_outcome(fixture.config, fixture.spec)
            self.assertTrue(fixture.run_contract.is_file())
            self.assertFalse(fixture.result.exists())
            self.assertEqual(validated.scores.shape, (4, 8))
            contract = json.loads(fixture.run_contract.read_text())
            self.assertEqual(contract["structure"]["speaker_attack_cells"], 4)
            self.assertTrue(
                contract["inputs"]["scores"]["SSL-AASIST"][
                    "legacy_input_ledger_not_historical_run_provenance"
                ]
            )

    def test_full_synthetic_outcome_has_descriptive_schema_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            validated = validate_pre_outcome(fixture.config, fixture.spec)
            result = run_outcomes(validated)
            self.assertEqual(set(result["arms"]), {"trial_iid", "speaker_attack", "speaker_only"})
            self.assertTrue(result["point_statistics_identical_across_arms"])
            self.assertEqual(
                len(result["comparison"]["primary_over_iid_simultaneous_width_ratio"]), 6
            )
            serialized = json.dumps(result).lower()
            for forbidden in ("confidence", "significant", "resolved", "confirmed", "refuted"):
                self.assertNotIn(forbidden, serialized)

    def test_input_mutation_after_contract_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            validated = validate_pre_outcome(fixture.config, fixture.spec)
            with fixture.protocol.open("a") as stream:
                stream.write("\n")
            with self.assertRaises(InputContractError, msg="mutation must fail"):
                verify_snapshot(validated)

    def test_duplicate_score_is_rejected_before_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            path = fixture.config.scores[2].path
            with path.open("a") as stream:
                stream.write("t0b\t0.7\n")
            with self.assertRaises(InputContractError):
                validate_pre_outcome(fixture.config, fixture.spec)
            self.assertFalse(fixture.run_contract.exists())

    def test_nonfinite_score_is_rejected_before_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            path = fixture.config.scores[2].path
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter="\t"))
            rows[0]["score"] = "nan"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["utt", "score"], delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(InputContractError):
                validate_pre_outcome(fixture.config, fixture.spec)
            self.assertFalse(fixture.run_contract.exists())

    def test_orientation_failure_occurs_only_after_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            # Negate all four vectors while retaining finite, complete inputs.
            for score in fixture.config.scores:
                if score.kind == "npz_dir":
                    for path in score.path.glob("*.npz"):
                        with np.load(path) as payload:
                            ids = payload["utt_id"].copy()
                            values = -payload["score"].copy()
                        np.savez(path, utt_id=ids, score=values)
                else:
                    with score.path.open(newline="") as input_stream:
                        lines = list(csv.DictReader(input_stream, delimiter="\t"))
                    with score.path.open("w", newline="") as stream:
                        writer = csv.DictWriter(stream, fieldnames=["utt", "score"], delimiter="\t")
                        writer.writeheader()
                        for row in lines:
                            writer.writerow({"utt": row["utt"], "score": -float(row["score"])})
            validated = validate_pre_outcome(fixture.config, fixture.spec)
            self.assertTrue(fixture.run_contract.exists())
            with self.assertRaises(InputContractError, msg="orientation must fail"):
                run_outcomes(validated)

    def test_mixed_checkpoint_row_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Fixture(Path(directory))
            validated = validate_pre_outcome(fixture.config, fixture.spec)
            checkpoint = checkpoint_for_arm(validated, "trial_iid", B=5)
            checkpoint[0, 0] = 1.0
            checkpoint.flush()
            with self.assertRaises(InputContractError):
                checkpoint_for_arm(validated, "trial_iid", B=5)


if __name__ == "__main__":
    unittest.main()
