#!/usr/bin/env python3
"""Synthetic and score-blind tests for EXP-108."""

from __future__ import annotations

import unittest

import numpy as np

from analyze import FastPathEER, full_weighted_eer
from build_contract import Trial, build_policy_weights, validate_policy


def make_trial(
    utterance: str,
    label: str,
    source: str,
    speaker: str,
    attack: str = "-",
    family: str = "-",
    task: str = "-",
) -> Trial:
    return Trial(
        speaker=speaker,
        utterance=utterance,
        codec="nocodec",
        source=source,
        attack=attack,
        label=label,
        phase="eval",
        family=family,
        task=task,
    )


def synthetic_metadata() -> list[Trial]:
    rows: list[Trial] = []
    index = 0
    for source_index, source in enumerate(("asvspoof", "vcc2018", "vcc2020")):
        for speaker_index in range(2):
            for _ in range(1 + source_index + speaker_index):
                rows.append(
                    make_trial(
                        f"u{index:04d}", "bonafide", source, f"b{source_index}_{speaker_index}"
                    )
                )
                index += 1
    strata = (
        ("asvspoof", "-"),
        ("vcc2018", "HUB"),
        ("vcc2018", "SPO"),
        ("vcc2020", "Task1"),
        ("vcc2020", "Task2"),
    )
    for stratum_index, (source, task) in enumerate(strata):
        for family_index, family in enumerate(("traditional", "neural")):
            attack = f"a{stratum_index}_{family_index}"
            for speaker_index in range(2):
                for _ in range(1 + speaker_index):
                    rows.append(
                        make_trial(
                            f"u{index:04d}",
                            "spoof",
                            source,
                            f"s{stratum_index}_{speaker_index}",
                            attack=attack,
                            family=family,
                            task=task,
                        )
                    )
                    index += 1
    rows.sort(key=lambda row: row.utterance)
    return rows


class PolicyTests(unittest.TestCase):
    def test_all_policy_hierarchies_validate(self) -> None:
        rows = synthetic_metadata()
        policies = build_policy_weights(rows)
        self.assertEqual(len(policies), 12)
        for name, weights in policies.items():
            summary = validate_policy(rows, name, weights)
            self.assertAlmostEqual(summary["bona_sum"], 1.0, places=12)
            self.assertAlmostEqual(summary["spoof_sum"], 1.0, places=12)
            self.assertGreater(summary["minimum_positive_mass"], 0.0)

    def test_policy_builder_is_score_blind(self) -> None:
        rows = synthetic_metadata()
        first = build_policy_weights(rows)
        # There is no score field in Trial; rebuilding after an unrelated RNG
        # operation must therefore be byte-identical.
        np.random.default_rng(9).normal(size=1000)
        second = build_policy_weights(rows)
        for name in first:
            self.assertEqual(first[name].tobytes(), second[name].tobytes())


class EERTests(unittest.TestCase):
    def test_fast_path_matches_full_reference_200_cases(self) -> None:
        rng = np.random.default_rng(20260830)
        for case in range(200):
            n = 60 + case % 31
            labels = np.zeros(n, dtype=np.int8)
            labels[: n // 3] = 1
            rng.shuffle(labels)
            scores = rng.normal(size=n)
            if case % 7 == 0:
                scores = np.round(scores, 1)
            w0 = rng.lognormal(size=n)
            w1 = rng.lognormal(size=n)
            for weights in (w0, w1):
                weights[labels == 1] /= weights[labels == 1].sum()
                weights[labels == 0] /= weights[labels == 0].sum()
            model = FastPathEER.build(scores, labels, w0, w1)
            lam = (case * 7919 % 10001) / 10000
            weights = (1 - lam) * w0 + lam * w1
            fast, fast_position = model.evaluate(lam)
            slow, slow_position = full_weighted_eer(scores, labels, weights)
            self.assertAlmostEqual(fast, slow, places=12)
            self.assertEqual(fast_position, slow_position)

    def test_identical_system_control_cannot_reverse(self) -> None:
        rng = np.random.default_rng(1)
        labels = np.r_[np.ones(20, dtype=np.int8), np.zeros(40, dtype=np.int8)]
        scores = rng.normal(size=len(labels))
        w0 = np.ones(len(labels))
        w1 = rng.lognormal(size=len(labels))
        for weights in (w0, w1):
            weights[labels == 1] /= weights[labels == 1].sum()
            weights[labels == 0] /= weights[labels == 0].sum()
        left = FastPathEER.build(scores, labels, w0, w1)
        right = FastPathEER.build(scores.copy(), labels, w0, w1)
        for lam in np.linspace(0, 1, 101):
            self.assertEqual(left.evaluate(float(lam))[0], right.evaluate(float(lam))[0])

    def test_fixed_gap_control_stays_ordered(self) -> None:
        labels = np.r_[np.ones(20, dtype=np.int8), np.zeros(20, dtype=np.int8)]
        perfect = np.r_[np.full(20, 2.0), np.full(20, -2.0)]
        reversed_scores = -perfect
        rng = np.random.default_rng(2)
        w0 = np.ones(len(labels))
        w1 = rng.lognormal(size=len(labels))
        for weights in (w0, w1):
            weights[labels == 1] /= weights[labels == 1].sum()
            weights[labels == 0] /= weights[labels == 0].sum()
        good = FastPathEER.build(perfect, labels, w0, w1)
        bad = FastPathEER.build(reversed_scores, labels, w0, w1)
        for lam in np.linspace(0, 1, 101):
            self.assertLess(good.evaluate(float(lam))[0], bad.evaluate(float(lam))[0])

    def test_composition_dependent_positive_control_flips(self) -> None:
        # Two equally sized domains.  A is correct only in domain 0, B only in
        # domain 1.  Endpoint masses exchange which domain carries 95% weight.
        labels = np.tile(np.array([1, 0], dtype=np.int8), 40)
        domain = np.repeat(np.array([0, 1]), 40)
        a_scores = np.where(
            domain == 0,
            np.where(labels == 1, 2.0, -2.0),
            np.where(labels == 1, -2.0, 2.0),
        )
        b_scores = np.where(
            domain == 1,
            np.where(labels == 1, 2.0, -2.0),
            np.where(labels == 1, -2.0, 2.0),
        )
        w0 = np.where(domain == 0, 0.95, 0.05).astype(float)
        w1 = np.where(domain == 0, 0.05, 0.95).astype(float)
        for weights in (w0, w1):
            weights[labels == 1] /= weights[labels == 1].sum()
            weights[labels == 0] /= weights[labels == 0].sum()
        delta_0 = full_weighted_eer(a_scores, labels, w0)[0] - full_weighted_eer(
            b_scores, labels, w0
        )[0]
        delta_1 = full_weighted_eer(a_scores, labels, w1)[0] - full_weighted_eer(
            b_scores, labels, w1
        )[0]
        self.assertLess(delta_0 * delta_1, 0.0)


if __name__ == "__main__":
    unittest.main()
