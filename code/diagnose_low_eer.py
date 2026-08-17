"""Frozen post-result diagnostics for the EXP-105 coverage failure.

This script does not regenerate scores, datasets, intervals, or bootstrap
draws.  It reads the checkpointed outer-replicate rows and the independently
recalibrated population truths.  Its diagnostic set was recorded in PREREG.md
after the original reading rule had already been refuted by grid 26 and before
the remaining grid cells completed.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import coverage_interaction as ci


HERE = Path(__file__).resolve().parent
DERIVED = HERE.parent / "derived"
HISTORICAL_COVERAGE_SHA256 = (
    "570727728b78300d30371a4c0e163f7d4d72028ccc006cc02c85a6a6c53b40ef")
Q_PAPER = 2.981


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def average_ranks(values):
    """Return one-based average ranks, including exact ties."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and values[order[stop]] == values[order[start]]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * (start + 1 + stop)
        start = stop
    return ranks


def correlation(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def coverage_count(lo, hi, truth):
    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    covered = (lo <= truth) & (truth <= hi)
    return {
        "covered": int(covered.sum()),
        "coverage": float(covered.mean()),
        "truth_below_interval": int((truth < lo).sum()),
        "truth_above_interval": int((truth > hi).sum()),
    }


def diagnose_cell(index, cell, rows):
    truth = float(cell["population_truth_delta_pts"])
    d_hat = np.asarray([row["d_hat"] for row in rows], dtype=float)
    v_raw = np.asarray([row["v_raw"] for row in rows], dtype=float)
    v_floor = np.asarray([row["v_floor"] for row in rows], dtype=float)
    p_lo = np.asarray([row["product_lo"] for row in rows], dtype=float)
    p_hi = np.asarray([row["product_hi"] for row in rows], dtype=float)
    errors = d_hat - truth
    abs_errors = np.abs(errors)
    valid_raw = np.isfinite(v_raw) & (v_raw > 0.0)
    mc_variance = float(np.var(d_hat, ddof=1))
    oracle_half_width = ci.Z95 * math.sqrt(mc_variance)

    raw_half = np.full(len(rows), np.nan)
    raw_half[valid_raw] = ci.Z95 * np.sqrt(v_raw[valid_raw])
    floor_half = ci.Z95 * np.sqrt(v_floor)
    raw_coverage = coverage_count(d_hat[valid_raw] - raw_half[valid_raw],
                                  d_hat[valid_raw] + raw_half[valid_raw], truth)
    raw_coverage["invalid_variance"] = int((~valid_raw).sum())
    floor_coverage = coverage_count(d_hat - floor_half, d_hat + floor_half, truth)
    product_coverage = coverage_count(p_lo, p_hi, truth)

    # The basic and symmetric intervals reuse frozen percentile endpoints. They
    # are diagnostics only; neither was an estimator in the original reading rule.
    basic_lo = 2.0 * d_hat - p_hi
    basic_hi = 2.0 * d_hat - p_lo
    percentile_radius = np.maximum(d_hat - p_lo, p_hi - d_hat)
    symmetric_lo = d_hat - percentile_radius
    symmetric_hi = d_hat + percentile_radius

    q_raw_lo = d_hat[valid_raw] - Q_PAPER * np.sqrt(v_raw[valid_raw])
    q_raw_hi = d_hat[valid_raw] + Q_PAPER * np.sqrt(v_raw[valid_raw])
    q_floor_lo = d_hat - Q_PAPER * np.sqrt(v_floor)
    q_floor_hi = d_hat + Q_PAPER * np.sqrt(v_floor)

    raw_pass = np.zeros(len(rows), dtype=bool)
    raw_pass[valid_raw] = ((d_hat[valid_raw] - raw_half[valid_raw] <= truth) &
                           (truth <= d_hat[valid_raw] + raw_half[valid_raw]))
    raw_failure = valid_raw & ~raw_pass
    raw_success = valid_raw & raw_pass
    studentized = errors[valid_raw] / np.sqrt(v_raw[valid_raw])

    def median_or_none(values):
        return float(np.median(values)) if len(values) else None

    return {
        "index": index,
        "spec": cell["spec"],
        "R": len(rows),
        "population_truth_delta_pts": truth,
        "point_estimate": {
            "mean": float(np.mean(d_hat)),
            "bias": float(np.mean(errors)),
            "direct_mc_variance": mc_variance,
        },
        "estimated_variance": {
            "mean_raw": float(np.mean(v_raw[valid_raw])),
            "mean_floor": float(np.mean(v_floor)),
            "mean_raw_over_direct_mc": float(np.mean(v_raw[valid_raw]) / mc_variance),
            "mean_floor_over_direct_mc": float(np.mean(v_floor) / mc_variance),
            "raw_invalid_count": int((~valid_raw).sum()),
        },
        "coverage": {
            "raw_normal": raw_coverage,
            "floor_normal": floor_coverage,
            "product_percentile": product_coverage,
            "oracle_sd_normal": coverage_count(
                d_hat - oracle_half_width, d_hat + oracle_half_width, truth),
            "product_basic_posthoc": coverage_count(basic_lo, basic_hi, truth),
            "product_symmetric_widest_tail_posthoc": coverage_count(
                symmetric_lo, symmetric_hi, truth),
            "q_2_981_raw_posthoc": coverage_count(q_raw_lo, q_raw_hi, truth),
            "q_2_981_floor_posthoc": coverage_count(q_floor_lo, q_floor_hi, truth),
        },
        "studentized_raw": {
            "quantiles_0.025_0.5_0.975": [float(x) for x in
                                            np.quantile(studentized, [0.025, 0.5, 0.975])],
            "mean": float(np.mean(studentized)),
            "sd": float(np.std(studentized, ddof=1)),
        },
        "error_variance_association": {
            "pearson_abs_error_vs_raw_variance": correlation(
                abs_errors[valid_raw], v_raw[valid_raw]),
            "spearman_abs_error_vs_raw_variance": correlation(
                average_ranks(abs_errors[valid_raw]), average_ranks(v_raw[valid_raw])),
            "median_raw_variance_failures": median_or_none(v_raw[raw_failure]),
            "median_raw_variance_passes": median_or_none(v_raw[raw_success]),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=ci.RUN_ROOT)
    parser.add_argument(
        "--corrected", type=Path,
        default=DERIVED / "results_coverage_interaction_recalibrated.json")
    parser.add_argument("--out", type=Path,
                        default=DERIVED / "results_coverage_diagnostics.json")
    args = parser.parse_args()

    corrected = json.loads(args.corrected.read_text())
    if len(corrected["grid"]) != 48:
        raise RuntimeError("corrected-truth grid must contain all 48 cells")
    expected_hash = corrected["coverage_script_sha256"]
    released_hash = sha256(HERE / "coverage_interaction.py")
    if expected_hash not in {released_hash, HISTORICAL_COVERAGE_SHA256}:
        raise RuntimeError(
            "corrected truth names neither the historical campaign bytes nor "
            "the released path-adapted coverage code")

    output_cells = []
    for index, cell in enumerate(corrected["grid"]):
        if cell["index"] != index:
            raise RuntimeError(f"corrected grid out of order at {index}")
        root = args.run_root / f"grid_{index:02d}"
        contract = json.loads((root / "contract.json").read_text())
        if contract["script_sha256"] != expected_hash:
            raise RuntimeError(f"grid {index}: script hash mismatch")
        rows = [json.loads(line) for line in
                (root / "replicates.jsonl").read_text().splitlines() if line]
        if len(rows) != contract["R"]:
            raise RuntimeError(f"grid {index}: incomplete rows")
        output_cells.append(diagnose_cell(index, cell, rows))

    low_eer = [cell for cell in output_cells
               if cell["spec"]["regime"] == "low_eer"]
    output = {
        "experiment": "EXP-105-post-result-diagnostics",
        "status": "diagnostic_only_original_reading_rule_remains_refuted",
        "q_2_981_provenance": (
            "pre-existing real-data 28-pair product-bootstrap critical value; "
            "post-hoc relative to the EXP-105 coverage preregistration"),
        "inputs": {
            "coverage_interaction.py": expected_hash,
            "corrected_truth": sha256(args.corrected),
        },
        "diagnostic_script_sha256": sha256(Path(__file__)),
        "grid": output_cells,
        "low_eer_minimum_coverage": {
            name: min(cell["coverage"][name]["coverage"] for cell in low_eer)
            for name in ("raw_normal", "floor_normal", "product_percentile",
                         "oracle_sd_normal", "product_basic_posthoc",
                         "product_symmetric_widest_tail_posthoc",
                         "q_2_981_raw_posthoc", "q_2_981_floor_posthoc")
        },
    }
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {args.out}")
    print("low-EER minimum coverage: " + ", ".join(
        f"{name}={value:.3f}"
        for name, value in output["low_eer_minimum_coverage"].items()))


if __name__ == "__main__":
    main()
