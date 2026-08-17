"""Execute EXP-105 preregistration gate 4 on the real 21DF inputs.

This compares the independent EER/incidence path in ``coverage_interaction``
with the released weighted-EER path used by ``analyze_multiway``.  It also
checks the compiled product-bootstrap kernel on real tied score files under
shared speaker/attack weights.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import analyze_multiway as am
import coverage_interaction as ci


HERE = Path(__file__).resolve().parent
DERIVED = HERE.parent / "derived"
SEED = 20260826


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=32)
    parser.add_argument("--out", type=Path,
                        default=DERIVED / "results_crosspath_gate.json")
    args = parser.parse_args()
    if args.draws < 1:
        raise ValueError("--draws must be positive")

    (utts, labels_a, spk_names, spk_a, _att_names, att_a,
     cell_pairs, cell_a, scores) = am.load_data()
    labels_c, spk_c, att_c, cell_c, n_spk, n_att, n_cell = ci.load_incidence()
    if not np.array_equal(labels_a, labels_c):
        raise AssertionError("label vectors differ across paths")
    if not np.array_equal(spk_a, spk_c):
        raise AssertionError("speaker partitions differ across paths")
    spoof = labels_a == 0
    _, compact_att_a = np.unique(att_a[spoof], return_inverse=True)
    if not np.array_equal(compact_att_a, att_c[spoof]):
        raise AssertionError("attack partitions differ across paths")
    if not np.array_equal(cell_a[spoof], cell_c[spoof]):
        raise AssertionError("speaker-attack cell partitions differ across paths")
    counts = {"n_trials": len(labels_a), "n_speakers": len(spk_names),
              "n_attacks": len(np.unique(att_a[spoof])),
              "n_cells": len(cell_pairs)}
    expected_counts = {"n_trials": len(labels_c), "n_speakers": n_spk,
                       "n_attacks": n_att, "n_cells": n_cell}
    if counts != expected_counts:
        raise AssertionError((counts, expected_counts))

    ones = np.ones(len(labels_a), dtype=np.float64)
    names = list(scores)
    orders = {name: np.argsort(scores[name]) for name in names}
    point = {}
    max_system_diff = 0.0
    for name in names:
        weighted = float(am.weighted_eer(orders[name], labels_a, ones))
        independent = ci.point_eer(orders[name], labels_c)
        reversed_eer = ci.point_eer(np.argsort(-scores[name]), labels_c)
        max_system_diff = max(max_system_diff, abs(weighted - independent))
        if independent >= reversed_eer:
            raise AssertionError(f"{name}: score orientation is not higher-is-bona")
        point[name] = {"weighted_eer": weighted, "independent_eer": independent,
                       "reversed_orientation_eer": reversed_eer}
    if max_system_diff > 1e-15:
        raise AssertionError(f"point EER paths differ by {max_system_diff}")

    real = json.loads((DERIVED / "results_multiway_real.json").read_text())
    if {k: real[k] for k in ("n_trials", "n_speakers", "n_spoof_attacks",
                              "n_observed_spoof_cells")} != {
            "n_trials": counts["n_trials"], "n_speakers": counts["n_speakers"],
            "n_spoof_attacks": counts["n_attacks"],
            "n_observed_spoof_cells": counts["n_cells"]}:
        raise AssertionError("results_multiway_real count fields differ from both paths")
    max_pair_delta_diff_pts = 0.0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            key = f"{a} vs {b}"
            delta = 100.0 * (point[a]["independent_eer"] - point[b]["independent_eer"])
            max_pair_delta_diff_pts = max(
                max_pair_delta_diff_pts,
                abs(delta - float(real["pairs"][key]["delta_eer_pts"])))
    # The released result rounds ΔEER to six decimal places.
    if max_pair_delta_diff_pts > 0.5e-6 + 1e-12:
        raise AssertionError(f"real-result pair delta mismatch {max_pair_delta_diff_pts}")

    bona_counts = np.bincount(spk_c[labels_c == 1], minlength=n_spk).astype(np.int64)
    cell_counts = np.bincount(cell_c[spoof], minlength=n_cell).astype(np.int64)
    first = np.full(n_cell, -1, dtype=np.int64)
    for index in np.flatnonzero(spoof):
        if first[cell_c[index]] < 0:
            first[cell_c[index]] = index
    cell_spk = spk_c[first].astype(np.int64)
    cell_att = att_c[first].astype(np.int64)
    rng = np.random.default_rng(SEED)
    max_product_diff = 0.0
    comparisons = 0
    for _ in range(args.draws):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        ca = np.bincount(rng.integers(0, n_att, n_att), minlength=n_att)
        weights = cs[spk_c].astype(np.float64)
        weights[spoof] *= ca[att_c[spoof]]
        if weights[labels_c == 1].sum() == 0 or weights[spoof].sum() == 0:
            continue
        reference = {name: float(am.weighted_eer(orders[name], labels_a, weights))
                     for name in names}
        # Four disjoint pairs cover all eight system EERs.  Equality for each
        # system implies equality for every one of the 28 pairwise deltas while
        # avoiding 28 redundant full score sweeps per weight draw.
        for a, b in zip(names[::2], names[1::2]):
            got_a, got_b = ci.product_two_eers(
                orders[a], orders[b], labels_c, spk_c, att_c, cs, ca,
                bona_counts, cell_spk, cell_att, cell_counts)
            max_product_diff = max(max_product_diff, abs(got_a - reference[a]),
                                   abs(got_b - reference[b]))
            comparisons += 2
    if max_product_diff > 1e-15:
        raise AssertionError(f"real product-weight paths differ by {max_product_diff}")

    output = {
        "experiment": "EXP-105-crosspath-gate",
        "seed": SEED,
        "draws": args.draws,
        "comparisons": comparisons,
        "scripts": {name: sha256(HERE / name) for name in
                    ("verify_crosspath_gate.py", "coverage_interaction.py",
                     "analyze_multiway.py")},
        "counts": counts,
        "point_eers": point,
        "max_point_system_eer_difference": max_system_diff,
        "max_pair_delta_difference_pts_after_six_decimal_release_rounding":
            max_pair_delta_diff_pts,
        "max_real_product_weight_eer_difference": max_product_diff,
        "pass": True,
    }
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {args.out}; PASS; {comparisons} weighted real-score comparisons")


if __name__ == "__main__":
    main()
