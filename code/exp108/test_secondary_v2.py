#!/usr/bin/env python3
"""Synthetic gates for the EXP-108 secondary v2 backends."""

from __future__ import annotations

import unittest

import numpy as np

from search_witnesses_v2 import CountCanonicalEER, MaterializedEER, distances


class BackendTests(unittest.TestCase):
    def test_count_and_direct_are_close_away_from_boundary(self) -> None:
        rng = np.random.default_rng(20260831)
        labels = np.r_[np.ones(60, dtype=np.int8), np.zeros(100, dtype=np.int8)]
        bidx = np.r_[np.repeat(np.arange(3), 20), np.full(100, -1)]
        sidx = np.r_[np.full(60, -1), np.repeat(np.arange(5), 20)]
        permutation = rng.permutation(len(labels))
        labels, bidx, sidx = labels[permutation], bidx[permutation], sidx[permutation]
        scores = rng.normal(size=len(labels)) + 0.8 * labels
        count = CountCanonicalEER(scores, labels, bidx, sidx)
        direct = MaterializedEER(scores, labels, bidx, sidx)
        for _ in range(200):
            qb = rng.dirichlet(np.ones(3))
            qs = rng.dirichlet(np.ones(5))
            count_eer = count.at(qb, qs)[0]
            direct_eer = direct.direct(qb, qs)[0]
            largest_trial_mass = max((qb / 20).max(), (qs / 20).max())
            self.assertLessEqual(abs(count_eer - direct_eer), largest_trial_mass + 1e-12)

    def test_tie_safe_is_invariant_to_within_tie_order(self) -> None:
        labels = np.r_[np.ones(30, dtype=np.int8), np.zeros(50, dtype=np.int8)]
        bidx = np.r_[np.repeat(np.arange(3), 10), np.full(50, -1)]
        sidx = np.r_[np.full(30, -1), np.repeat(np.arange(5), 10)]
        scores = np.round(np.linspace(-2, 2, len(labels)), 1)
        qb = np.array([0.2, 0.3, 0.5])
        qs = np.array([0.1, 0.15, 0.2, 0.25, 0.3])
        first = MaterializedEER(scores, labels, bidx, sidx).tie_safe(qb, qs)[0]
        # Reverse every equal-score run without changing scores or row masses.
        order = np.arange(len(scores))
        for value in np.unique(scores):
            selected = np.flatnonzero(scores == value)
            order[selected] = selected[::-1]
        second = MaterializedEER(
            scores[order], labels[order], bidx[order], sidx[order]
        ).tie_safe(qb, qs)[0]
        self.assertAlmostEqual(first, second, places=12)

    def test_distance_identity_and_positive_shift(self) -> None:
        pb = np.array([0.5, 0.3, 0.2])
        ps = np.array([0.1, 0.2, 0.15, 0.25, 0.3])
        self.assertEqual(distances(pb, ps, pb, ps), (0.0, 1.0))
        tv, odds = distances(np.array([0.4, 0.4, 0.2]), ps, pb, ps)
        self.assertAlmostEqual(tv, 0.1)
        self.assertGreater(odds, 1.0)


if __name__ == "__main__":
    unittest.main()
