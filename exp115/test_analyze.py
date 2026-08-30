#!/usr/bin/env python3

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("exp115_analyze", HERE / "analyze.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EERTests(unittest.TestCase):
    def test_perfect_and_reversed(self):
        labels = np.asarray([1, 1, 0, 0], dtype=np.int8)
        scores = np.asarray([0.9, 0.8, 0.2, 0.1])
        mass = MODULE.normalized_class_mass(np.ones(4), labels)
        self.assertEqual(
            MODULE.eer_from_mass(np.argsort(scores, kind="mergesort"), labels, mass),
            0.0,
        )
        self.assertEqual(
            MODULE.eer_from_mass(np.argsort(-scores, kind="mergesort"), labels, mass),
            1.0,
        )

    def test_one_class_support_fails(self):
        labels = np.asarray([1, 1, 0, 0], dtype=np.int8)
        with self.assertRaisesRegex(ValueError, "positive support"):
            MODULE.normalized_class_mass(np.asarray([1, 1, 0, 0]), labels)


class ArmTests(unittest.TestCase):
    @staticmethod
    def data():
        labels = np.tile(np.asarray([1, 0, 0], dtype=np.int8), 12)
        return {
            "labels": labels,
            "speakers": np.repeat(np.arange(12), 3),
            "speaker_names": np.asarray([f"s{i}" for i in range(12)]),
            "attacks": np.tile(np.arange(3), 12),
            "attack_names": np.asarray(["A00", "A15", "A16"]),
        }

    def test_speaker_only_has_no_attack_multiplier(self):
        data = self.data()
        weights, _ = MODULE.draw_speaker_only(np.random.default_rng(5), data)
        for speaker in range(12):
            observed = weights[data["speakers"] == speaker]
            self.assertEqual(len(np.unique(observed)), 1)

    def test_attack_only_has_no_speaker_multiplier(self):
        data = self.data()
        weights, _ = MODULE.draw_attack_only(np.random.default_rng(5), data)
        self.assertTrue(np.all(weights[data["labels"] == 1] == 1))
        for attack in (1, 2):
            observed = weights[data["attacks"] == attack]
            self.assertEqual(len(np.unique(observed)), 1)

    def test_small_run_is_deterministic_and_complete(self):
        data = self.data()
        rng = np.random.default_rng(4)
        scores = {
            system: rng.normal(size=len(data["labels"]))
            + data["labels"] * separation
            for system, separation in zip(MODULE.SYSTEMS, (0.1, 0.3, 0.5, 0.7))
        }
        first, first_speaker, first_attack = MODULE.run(
            data, scores, replicates=100, seed=11,
        )
        second, second_speaker, second_attack = MODULE.run(
            data, scores, replicates=100, seed=11,
        )
        np.testing.assert_array_equal(first_speaker, second_speaker)
        np.testing.assert_array_equal(first_attack, second_attack)
        self.assertEqual(first, second)
        self.assertEqual(len(first["arm_speaker_only"]["pairs"]), 6)
        self.assertEqual(len(first["arm_attack_only"]["pairs"]), 6)


class BindingTests(unittest.TestCase):
    def test_changed_manifest_hash_fails_before_parse(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                MODULE.read_manifest(path)

    def test_changed_score_hash_fails_before_parse(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.tsv"
            path.write_text("utt\tscore\na\t0\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                MODULE.read_scores(path, np.asarray(["a"], dtype=object), "aasist")

    def test_freeze_mutation_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = {
                "PREREG.md", "DATA.md", "analyze.py", "test_analyze.py",
                "pyproject.toml", "uv.lock",
            }
            lines = []
            for name in sorted(names):
                path = root / name
                path.write_text("frozen\n")
                lines.append(f"{MODULE.sha256_file(path)}  {name}")
            (root / "FREEZE.sha256").write_text("\n".join(lines) + "\n")
            MODULE.verify_freeze(root)
            (root / "analyze.py").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "frozen file mismatch"):
                MODULE.verify_freeze(root)

    def test_joint_roster_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text("{}\n")
            digest = MODULE.sha256_file(path)
            with mock.patch.object(MODULE, "EXPECTED_JOINT_RESULT_SHA256", digest):
                with self.assertRaisesRegex(ValueError, "trial-IID endpoint"):
                    MODULE.validate_joint_result(path)


class ReadingTests(unittest.TestCase):
    @staticmethod
    def arm(excludes: tuple[bool, bool, bool]):
        pairs = {}
        for pair, value in zip(MODULE.EXPECTED_JOINT_SENSITIVE, excludes):
            pairs[pair] = {"simultaneous_excludes_zero": value}
        return {"pairs": pairs}

    def test_all_four_reading_branches(self):
        speaker = self.arm((False, False, True))
        attack = self.arm((False, True, False))
        result = MODULE.classify_known_pairs(speaker, attack)
        self.assertEqual(
            result[MODULE.EXPECTED_JOINT_SENSITIVE[0]]["classification"],
            "both_one_factor_arms_include_zero",
        )
        self.assertEqual(
            result[MODULE.EXPECTED_JOINT_SENSITIVE[1]]["classification"],
            "speaker_only_includes_zero",
        )
        self.assertEqual(
            result[MODULE.EXPECTED_JOINT_SENSITIVE[2]]["classification"],
            "attack_only_includes_zero",
        )
        neither = MODULE.classify_known_pairs(self.arm((True, True, True)), self.arm((True, True, True)))
        self.assertEqual(
            neither[MODULE.EXPECTED_JOINT_SENSITIVE[0]]["classification"],
            "neither_one_factor_arm_includes_zero",
        )


if __name__ == "__main__":
    unittest.main()
