"""Post-process EXP-105 coverage against the population truth of the frozen DGP.

The original t(5) cells freeze ``mu_spoof`` from a finite Monte Carlo quantile
calibration, but their coverage flags compare against the nominal target.  This
script leaves every simulated dataset and interval untouched.  It estimates the
population EERs implied by the frozen locations at much higher precision and
recomputes coverage from the checkpointed JSONL rows.

Gaussian cells are exact analytically and retain their nominal truth.  For t(5)
cells, independent antithetic Monte Carlo repetitions preserve the bivariate DGP
coupling and provide an uncertainty/sensitivity audit for the corrected truth.
"""

import argparse
import hashlib
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import coverage_interaction as ci


HERE = Path(__file__).resolve().parent
DERIVED = HERE.parent / "derived"
Z95 = ci.Z95


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def quantile_sorted(values, p):
    """NumPy's default linear quantile for an already-sorted 1-D array."""
    position = float(p) * (len(values) - 1)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return float(values[lower] + fraction * (values[upper] - values[lower]))


def eer_from_zero_distributions(bona, spoof_zero, mu):
    """Solve Q_bona(e) = mu + Q_spoof_zero(1-e)."""
    lo, hi = 1e-7, 0.4999999
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        gap = (quantile_sorted(bona, mid) -
               mu - quantile_sorted(spoof_zero, 1.0 - mid))
        if gap < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def antithetic_pair(x0, x1):
    out0 = np.concatenate((x0, -x0))
    out1 = np.concatenate((x1, -x1))
    out0.sort()
    out1.sort()
    return out0, out1


def bona_samples(rng, spec, n_half):
    b = spec["calibration"]["bona"]
    u0, u1 = ci.bivariate_draw(rng, n_half, b["sd_grp0"], b["sd_grp1"],
                               b["rho_grp"], "t5")
    e0, e1 = ci.bivariate_draw(rng, n_half, b["sd_res0"], b["sd_res1"],
                               b["rho_res"], "gaussian")
    u0 += e0
    u1 += e1
    return antithetic_pair(u0, u1)


def spoof_samples(rng, spec, n_half):
    s = spec["calibration"]["spoof"]
    x0, x1 = ci.bivariate_draw(rng, n_half, spec["sd_spk"][0],
                               spec["sd_spk"][1], s["rho_spk"], "t5")
    for sd0, sd1, rho, tail in (
            (spec["sd_att"][0], spec["sd_att"][1], s["rho_att"], "t5"),
            (spec["sd_interaction"][0], spec["sd_interaction"][1],
             spec["rho_interaction"], "t5"),
            (s["sd_res0"], s["sd_res1"], s["rho_res"], "gaussian")):
        y0, y1 = ci.bivariate_draw(rng, n_half, sd0, sd1, rho, tail)
        x0 += y0
        x1 += y1
    return antithetic_pair(x0, x1)


def wilson(k, n):
    return ci.wilson(int(k), int(n))


def coverage_at(rows, truth):
    raw = [r for r in rows if r["v_raw"] > 0.0 and
           abs(r["d_hat"] - truth) <= Z95 * math.sqrt(r["v_raw"])]
    floor = [r for r in rows if
             abs(r["d_hat"] - truth) <= Z95 * math.sqrt(r["v_floor"])]
    product = [r for r in rows if r["product_lo"] <= truth <= r["product_hi"]]
    out = {}
    for name, covered in (("raw", raw), ("floor", floor), ("product", product)):
        k = len(covered)
        out[name] = {"covered": k, "coverage": k / len(rows),
                     "wilson95": wilson(k, len(rows))}
    out["raw"]["failure_rate"] = sum(r["v_raw"] <= 0.0 for r in rows) / len(rows)
    out["floor"]["failure_rate"] = 0.0
    out["product"]["failure_rate"] = 0.0
    return out


def load_cells(run_root):
    cells = {}
    for index in range(48):
        root = run_root / f"grid_{index:02d}"
        contract = json.loads((root / "contract.json").read_text())
        rows = [json.loads(line) for line in
                (root / "replicates.jsonl").read_text().splitlines() if line]
        if len(rows) != contract["R"]:
            raise RuntimeError(f"grid {index}: {len(rows)} rows, expected {contract['R']}")
        cells[index] = {"contract": contract, "rows": rows}
    return cells


def _estimate_repeat(by_spec, n_half, repeat):
    result = {}
    bona_cache = {}
    regimes = [regime for regime in ci.REGIMES
               if any(key[0] == regime for key in by_spec)]
    for regime in regimes:
        ridx = ci.REGIMES.index(regime)
        representative = next(spec for (r, _), group in by_spec.items() if r == regime
                              for _, spec in group.values())
        bona_rng = np.random.default_rng(np.random.SeedSequence(
            [ci.SEED, 5150, repeat, ridx, 0]))
        bona_cache[regime] = bona_samples(bona_rng, representative, n_half)
    for (regime, share), group in sorted(by_spec.items()):
        ridx = ci.REGIMES.index(regime)
        hidx = ci.INTERACTION_SHARES.index(share)
        representative = next(iter(group.values()))[1]
        spoof_rng = np.random.default_rng(np.random.SeedSequence(
            [ci.SEED, 5150, repeat, ridx, hidx, 1]))
        spoof0, spoof1 = spoof_samples(spoof_rng, representative, n_half)
        bona0, bona1 = bona_cache[regime]
        for _, (index, spec) in sorted(group.items()):
            eer0 = eer_from_zero_distributions(bona0, spoof0, spec["mu_spoof"][0])
            eer1 = eer_from_zero_distributions(bona1, spoof1, spec["mu_spoof"][1])
            result[index] = {"eer0": eer0, "eer1": eer1,
                             "delta": 100.0 * (eer0 - eer1)}
    return repeat, result


def estimate_t5_truths(cells, n_half, repeats, workers):
    by_spec = {}
    for index, cell in cells.items():
        spec = cell["contract"]["spec"]
        if spec["tail"] == "t5":
            key = (spec["regime"], spec["interaction_share"])
            by_spec.setdefault(key, {})[spec["target_delta_pts"]] = (index, spec)

    estimates = {index: {"eer0": [], "eer1": [], "delta": []}
                 for group in by_spec.values() for index, _ in group.values()}
    ctx = get_context("fork")
    completed = {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        futures = [pool.submit(_estimate_repeat, by_spec, n_half, repeat)
                   for repeat in range(repeats)]
        for future in as_completed(futures):
            repeat, result = future.result()
            completed[repeat] = result
            print(f"population-truth repeat {repeat + 1}/{repeats} complete", flush=True)
    # Restore deterministic repeat order irrespective of worker completion order.
    for repeat in range(repeats):
        for index, row in completed[repeat].items():
            for name in ("eer0", "eer1", "delta"):
                estimates[index][name].append(row[name])
    return estimates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=ci.RUN_ROOT)
    parser.add_argument("--n-half", type=int, default=2_500_000,
                        help="independent draws per antithetic half and repetition")
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--workers", type=int,
                        default=min(4, max(1, os.cpu_count() or 1)))
    parser.add_argument("--out", type=Path,
                        default=DERIVED / "results_coverage_interaction_recalibrated.json")
    args = parser.parse_args()
    if args.n_half < 100_000 or args.repeats < 2 or args.workers < 1:
        raise ValueError("production recalibration requires n_half>=100000 and repeats>=2")

    cells = load_cells(args.run_root)
    hashes = {cell["contract"]["script_sha256"] for cell in cells.values()}
    if len(hashes) != 1:
        raise RuntimeError(f"mixed coverage script hashes: {sorted(hashes)}")
    t5 = estimate_t5_truths(cells, args.n_half, args.repeats,
                             min(args.workers, args.repeats))

    output_cells = []
    for index in range(48):
        contract, rows = cells[index]["contract"], cells[index]["rows"]
        spec = contract["spec"]
        nominal = float(spec["true_delta_pts"])
        if spec["tail"] == "gaussian":
            truth_reps = [nominal]
            eers = None
        else:
            truth_reps = t5[index]["delta"]
            eers = {name: {"estimates": values,
                           "mean": float(np.mean(values)),
                           "sd": float(np.std(values, ddof=1)),
                           "se_mean": float(np.std(values, ddof=1) / math.sqrt(len(values)))}
                    for name, values in (("system0", t5[index]["eer0"]),
                                         ("system1", t5[index]["eer1"]))}
        truth = float(np.mean(truth_reps))
        corrected = coverage_at(rows, truth)
        sensitivity = [coverage_at(rows, value) for value in truth_reps]
        output_cells.append({
            "index": index,
            "spec": {k: spec[k] for k in
                     ("regime", "interaction_share", "tail", "target_delta_pts")},
            "nominal_truth_delta_pts": nominal,
            "population_truth_delta_pts": truth,
            "population_truth_repeat_estimates": truth_reps,
            "population_truth_sd": (float(np.std(truth_reps, ddof=1))
                                    if len(truth_reps) > 1 else 0.0),
            "population_truth_se_mean": (float(np.std(truth_reps, ddof=1) /
                                               math.sqrt(len(truth_reps)))
                                         if len(truth_reps) > 1 else 0.0),
            "population_eers": eers,
            "coverage": corrected,
            "truth_uncertainty_sensitivity": {
                name: {"coverage_min": min(x[name]["coverage"] for x in sensitivity),
                       "coverage_max": max(x[name]["coverage"] for x in sensitivity)}
                for name in ("raw", "floor", "product")},
        })

    def all_inside(name):
        return all(0.92 <= cell["coverage"][name]["coverage"] <= 0.98
                   for cell in output_cells)

    def min_coverage(name):
        return min(cell["coverage"][name]["coverage"] for cell in output_cells)

    def all_inside_sensitivity(name):
        return all(cell["truth_uncertainty_sensitivity"][name]["coverage_min"] >= 0.92 and
                   cell["truth_uncertainty_sensitivity"][name]["coverage_max"] <= 0.98
                   for cell in output_cells)

    def min_coverage_sensitivity(name):
        return min(cell["truth_uncertainty_sensitivity"][name]["coverage_min"]
                   for cell in output_cells)

    output = {
        "experiment": "EXP-105-population-truth-recalibration",
        "coverage_script_sha256": next(iter(hashes)),
        "recalibration_script_sha256": sha256(Path(__file__)),
        "run_root": str(args.run_root),
        "t5_population_mc": {"antithetic_total_per_repeat": 2 * args.n_half,
                             "independent_repeats": args.repeats,
                             "workers": min(args.workers, args.repeats)},
        "grid": output_cells,
        "all_cells_raw_inside_092_098": all_inside("raw"),
        "all_cells_floor_inside_092_098": all_inside("floor"),
        "all_cells_product_inside_092_098": all_inside("product"),
        "all_cells_inside_092_098_under_truth_sensitivity": {
            name: all_inside_sensitivity(name)
            for name in ("raw", "floor", "product")},
        "minimum_coverage": {name: min_coverage(name)
                             for name in ("raw", "floor", "product")},
        "minimum_coverage_under_truth_sensitivity": {
            name: min_coverage_sensitivity(name)
            for name in ("raw", "floor", "product")},
        "product_never_below_090": min_coverage_sensitivity("product") >= 0.90,
    }
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {args.out}")
    print("all cells [0.92,0.98]: " + ", ".join(
        f"{name}={output[f'all_cells_{name}_inside_092_098']}"
        for name in ("raw", "floor", "product")))
    print("minimum coverage: " + ", ".join(
        f"{name}={output['minimum_coverage'][name]:.3f}"
        for name in ("raw", "floor", "product")))


if __name__ == "__main__":
    main()
