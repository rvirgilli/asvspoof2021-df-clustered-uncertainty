#!/usr/bin/env python3
"""Synthetic gates for the EXP-106 Amendment-5 descriptive core."""

from __future__ import annotations

import json
import unittest

import numpy as np

from asv5_descriptive_core import (
    ARM_NAMESPACES,
    DescriptiveContractError,
    combine_summaries,
    draw_weights,
    one_replicate,
    pair_order,
    summarize_arm,
    weighted_eer_reference,
    weighted_eers,
)


def fixture():
    # Two target speakers occur in both classes; two non-target speakers occur
    # in bona fide only.  Both attacks occur for both target speakers.
    labels = np.asarray([1, 1, 1, 1, 0, 0, 0, 0], dtype=np.int8)
    target = np.asarray([0, 1, -1, -1, 0, 0, 1, 1], dtype=np.int64)
    non_target = np.asarray([-1, -1, 0, 1, -1, -1, -1, -1], dtype=np.int64)
    attack = np.asarray([-1, -1, -1, -1, 0, 1, 0, 1], dtype=np.int64)
    scores = np.asarray(
        [
            [0.8, 0.7, 0.9, 0.6, -0.5, -0.3, -0.8, -0.2],
            [0.9, 0.6, 0.7, 0.8, -0.2, -0.9, -0.4, -0.3],
            [0.8, 0.8, 0.6, 0.7, -0.4, -0.4, -0.9, -0.1],
            [0.6, 0.9, 0.8, 0.7, -0.7, -0.2, -0.3, -0.8],
        ],
        dtype=np.float64,
    )
    orders = np.asarray([np.argsort(row, kind="quicksort") for row in scores])
    return labels, target, non_target, attack, scores, orders


class NumericalCoreTests(unittest.TestCase):
    def test_optimized_agrees_with_literal_for_all_arms_and_ties(self) -> None:
        labels, target, non_target, attack, _scores, orders = fixture()
        for arm in ARM_NAMESPACES:
            for replicate in range(8):
                weights = draw_weights(
                    arm, replicate, labels, target, non_target, attack
                )
                optimized = weighted_eers(orders, labels, weights)
                literal = np.asarray(
                    [weighted_eer_reference(order, labels, weights) for order in orders]
                )
                np.testing.assert_allclose(optimized, literal, rtol=0.0, atol=1e-15)

    def test_multinomial_totals_and_role_law(self) -> None:
        labels, target, non_target, attack, _scores, _orders = fixture()
        iid = draw_weights("trial_iid", 2, labels, target, non_target, attack)
        self.assertEqual(iid[labels == 1].sum(), 4)
        self.assertEqual(iid[labels == 0].sum(), 4)

        speaker = draw_weights("speaker_only", 2, labels, target, non_target, attack)
        self.assertEqual(speaker[0], speaker[4])
        self.assertEqual(speaker[0], speaker[5])
        self.assertEqual(speaker[1], speaker[6])
        self.assertEqual(speaker[1], speaker[7])

        crossed = draw_weights("speaker_attack", 2, labels, target, non_target, attack)
        # Attack weights can separate spoof rows from the same speaker, while
        # target-speaker factors are still shared underneath.
        target_factor = speaker[0]
        if target_factor > 0:
            self.assertTrue(
                np.isclose(crossed[4] / crossed[0], round(crossed[4] / crossed[0]))
            )

    def test_replicates_are_batch_and_resume_invariant(self) -> None:
        labels, target, non_target, attack, _scores, orders = fixture()
        direct = np.asarray(
            [
                one_replicate(
                    "speaker_attack", i, orders, labels, target, non_target, attack
                )
                for i in range(12)
            ]
        )
        resumed = np.full_like(direct, np.nan)
        for i in (0, 3, 6, 9, 1, 4, 7, 10, 2, 5, 8, 11):
            resumed[i] = one_replicate(
                "speaker_attack", i, orders, labels, target, non_target, attack
            )
        np.testing.assert_array_equal(direct, resumed)

    def test_arm_namespaces_produce_distinct_draws(self) -> None:
        labels, target, non_target, attack, _scores, _orders = fixture()
        draws = {
            arm: draw_weights(arm, 11, labels, target, non_target, attack).tobytes()
            for arm in ARM_NAMESPACES
        }
        self.assertEqual(len(set(draws.values())), 3)

    def test_malformed_design_fails(self) -> None:
        labels, target, non_target, attack, _scores, _orders = fixture()
        broken = attack.copy()
        broken[4] = -1
        with self.assertRaises(DescriptiveContractError):
            draw_weights("speaker_attack", 0, labels, target, non_target, broken)

    def test_summary_matches_frozen_centered_max_t_formula(self) -> None:
        rng = np.random.default_rng(91)
        reps = rng.normal(size=(101, 4)) + np.asarray([1.0, 2.0, 4.0, 8.0])
        point = np.asarray([1.2, 2.1, 4.2, 7.8])
        result = summarize_arm(reps, point, arm="trial_iid")
        pairs = pair_order()
        deltas = np.column_stack(
            [reps[:, i] - reps[:, j] for i, j in combinations_indices(4)]
        )
        scale = deltas.std(axis=0, ddof=1)
        expected = np.percentile(
            (np.abs(deltas - deltas.mean(axis=0)) / scale).max(axis=1),
            95.0,
            method="linear",
        )
        self.assertAlmostEqual(result["max_t_critical_value"], expected, places=14)
        first = result["pairs"][f"{pairs[0][0]} vs {pairs[0][1]}"]
        expected_percentile = np.percentile(
            deltas[:, 0], [2.5, 97.5], method="linear"
        )
        np.testing.assert_allclose(first["pointwise_percentile"], expected_percentile)

    def test_combined_reading_and_vocabulary(self) -> None:
        rng = np.random.default_rng(18)
        point = np.asarray([0.0, 2.0, 5.0, 9.0])
        iid_reps = point + rng.normal(scale=0.1, size=(200, 4))
        primary_reps = point + rng.normal(scale=0.5, size=(200, 4))
        sensitivity_reps = point + rng.normal(scale=0.3, size=(200, 4))
        iid = summarize_arm(iid_reps, point, arm="trial_iid")
        primary = summarize_arm(primary_reps, point, arm="speaker_attack")
        sensitivity = summarize_arm(sensitivity_reps, point, arm="speaker_only")
        combined = combine_summaries(iid, primary, sensitivity)
        self.assertGreater(combined["median_primary_over_iid_width_ratio"], 2.0)
        self.assertTrue(
            combined["registered_descriptive_summaries"][
                "B_median_width_ratio_at_least_2"
            ]
        )
        serialized = json.dumps(
            {"arms": [iid, primary, sensitivity], "comparison": combined}
        ).lower()
        for forbidden in ("confidence", "significant", "resolved", "confirmed", "refuted"):
            self.assertNotIn(forbidden, serialized)


def combinations_indices(n: int):
    for first in range(n):
        for second in range(first + 1, n):
            yield first, second


if __name__ == "__main__":
    unittest.main()

