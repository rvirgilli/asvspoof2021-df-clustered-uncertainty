"""Strictly close EXP-105 from shards, corrected truth, and real-data gates."""

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


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def same_number(a, b, tolerance=1e-12):
    return abs(float(a) - float(b)) <= tolerance


def validate_shard(run_root, index, expected_hash):
    root = run_root / f"grid_{index:02d}"
    contract = json.loads((root / "contract.json").read_text())
    result = json.loads((root / "result.json").read_text())
    rows = [json.loads(line) for line in
            (root / "replicates.jsonl").read_text().splitlines() if line]
    regime, share, tail, delta = ci.grid_tuple(index)
    expected_spec = {"regime": regime, "interaction_share": share,
                     "tail": tail, "target_delta_pts": delta}
    if contract["script_sha256"] != expected_hash:
        raise RuntimeError(f"grid {index}: script hash mismatch")
    if contract["index"] != index:
        raise RuntimeError(f"grid {index}: contract index={contract['index']}")
    if any(contract["spec"][key] != value for key, value in expected_spec.items()):
        raise RuntimeError(f"grid {index}: grid specification mismatch")
    if not contract["include_product_bootstrap"] or contract["B_product"] != ci.B_PRODUCT:
        raise RuntimeError(f"grid {index}: product-bootstrap contract mismatch")
    if len(rows) != contract["R"] or result["R"] != contract["R"]:
        raise RuntimeError(f"grid {index}: row/R mismatch")
    if result["index"] != index or result["spec"] != contract["spec"]:
        raise RuntimeError(f"grid {index}: result/contract mismatch")
    checks = {
        "raw": sum(row["raw_cover"] for row in rows) / len(rows),
        "floor": sum(row["floor_cover"] for row in rows) / len(rows),
        "product": sum(row["product_cover"] for row in rows) / len(rows),
    }
    if any(not same_number(checks[name], result[name]["coverage"])
           for name in checks):
        raise RuntimeError(f"grid {index}: result coverage not reproduced from rows")
    raw_failure = sum(not np.isfinite(row["raw_width"]) for row in rows) / len(rows)
    if not same_number(raw_failure, result["raw"]["failure_rate"]):
        raise RuntimeError(f"grid {index}: raw failure rate mismatch")
    return {"contract_sha256": sha256(root / "contract.json"),
            "replicates_sha256": sha256(root / "replicates.jsonl"),
            "result_sha256": sha256(root / "result.json"),
            "n_rows": len(rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, default=ci.RUN_ROOT)
    parser.add_argument("--corrected", type=Path,
                        default=DERIVED / "results_coverage_interaction_recalibrated.json")
    parser.add_argument("--crosspath", type=Path,
                        default=DERIVED / "results_crosspath_gate.json")
    parser.add_argument("--out", type=Path,
                        default=DERIVED / "results_exp105_verified.json")
    args = parser.parse_args()

    corrected = json.loads(args.corrected.read_text())
    coverage_hash = corrected["coverage_script_sha256"]
    released_coverage_hash = sha256(HERE / "coverage_interaction.py")
    if coverage_hash not in {released_coverage_hash, HISTORICAL_COVERAGE_SHA256}:
        raise RuntimeError(
            "corrected truth names neither the historical campaign bytes nor "
            "the released path-adapted coverage code")
    gate = json.loads((args.run_root / "additive_gate.json").read_text())
    gate_contract = json.loads((args.run_root / "gate_additive/contract.json").read_text())
    gate_rows = sum(1 for line in
                    (args.run_root / "gate_additive/replicates.jsonl").read_text().splitlines()
                    if line)
    if not gate["pass"] or gate["R"] != ci.R_GATE or gate_rows != ci.R_GATE:
        raise RuntimeError("additive gate is absent, incomplete, or failed")
    if gate_contract["script_sha256"] != coverage_hash or gate_contract["R"] != ci.R_GATE:
        raise RuntimeError("additive gate contract differs from released coverage code")

    shards = {str(index): validate_shard(args.run_root, index, coverage_hash)
              for index in range(48)}
    original_path = DERIVED / "results_coverage_interaction.json"
    original = json.loads(original_path.read_text())
    if original["script_sha256"] != coverage_hash or len(original["grid"]) != 48:
        raise RuntimeError("original aggregate does not match the completed script/grid")
    for index, row in enumerate(original["grid"]):
        released = json.loads(
            (args.run_root / f"grid_{index:02d}/result.json").read_text())
        if row != released:
            raise RuntimeError(f"original aggregate differs from grid {index} result")

    if corrected["coverage_script_sha256"] != coverage_hash or len(corrected["grid"]) != 48:
        raise RuntimeError("corrected-truth result does not match coverage code/grid")
    if [row["index"] for row in corrected["grid"]] != list(range(48)):
        raise RuntimeError("corrected-truth grid indices are incomplete or reordered")
    crosspath = json.loads(args.crosspath.read_text())
    if not crosspath["pass"] or crosspath["scripts"]["coverage_interaction.py"] != coverage_hash:
        raise RuntimeError("cross-path real-data gate absent, failed, or stale")

    real_path = DERIVED / "results_multiway_real.json"
    real = json.loads(real_path.read_text())
    if real["linearization_gate_all_pairs_pass"]:
        raise RuntimeError("CRVE unexpectedly passes; closure assumptions changed")
    baseline = real["organizer_baseline_pairs"]
    q_jack = float(real["q95_gaussian_explicit_cell_jackknife_psd"])
    raw_resolved = 0
    floor_resolved = 0
    for key in baseline:
        pair = real["pairs"][key]
        delta = abs(float(pair["delta_eer_pts"]))
        exact = pair["explicit_cell_jackknife"]
        raw = float(exact["V_raw_inclusion_exclusion"])
        if raw > 0.0 and delta > q_jack * math.sqrt(raw):
            raw_resolved += 1
        floor_resolved += int(exact["resolved_simultaneous_own_q"])
    real_counts = {
        "product": int(real["organizer_baseline_resolved"]["product_bootstrap"]),
        "raw": raw_resolved,
        "floor": floor_resolved,
    }

    coverage_all_point = {
        name: bool(corrected[f"all_cells_{name}_inside_092_098"])
        for name in ("product", "raw", "floor")}
    # A pass may not depend on which high-precision truth-calibration repeat is
    # chosen.  Gaussian cells have a single exact truth and enter unchanged.
    coverage_all = {
        name: bool(corrected["all_cells_inside_092_098_under_truth_sensitivity"][name])
        for name in ("product", "raw", "floor")}
    confirmed_estimators = [name for name in coverage_all
                            if coverage_all[name] and real_counts[name] == 0]
    conclusion_invariant = all(value == 0 for value in real_counts.values())
    if confirmed_estimators:
        status = "confirmed"
    elif corrected["product_never_below_090"] and conclusion_invariant:
        status = "partially_confirmed"
    else:
        status = "refuted"

    output = {
        "experiment": "EXP-105-verified-closure",
        "status_under_preregistered_reading_rule": status,
        "confirmed_estimators": confirmed_estimators,
        "coverage_all_cells_inside_092_098_at_mean_truth": coverage_all_point,
        "coverage_all_cells_inside_092_098_under_truth_sensitivity": coverage_all,
        "minimum_corrected_coverage": corrected["minimum_coverage"],
        "minimum_corrected_coverage_under_truth_sensitivity":
            corrected["minimum_coverage_under_truth_sensitivity"],
        "organizer_baseline_pairs_resolved": real_counts,
        "six_pair_conclusion_invariant": conclusion_invariant,
        "linearized_crve_excluded_by_failed_gate": True,
        "additive_gate": {
            "R": gate["R"],
            "mean_raw_multiway_over_mc_variance":
                gate["mean_raw_multiway_over_mc_variance"],
            "pass": gate["pass"],
        },
        "input_hashes": {
            "coverage_interaction.py": coverage_hash,
            "released_path_adapted_coverage_interaction.py":
                released_coverage_hash,
            "power_curves.py": sha256(ci.pc.__file__),
            "key": sha256(ci.pc.KEY),
            "results_coverage_interaction.json":
                sha256(original_path),
            "results_coverage_interaction_recalibrated.json": sha256(args.corrected),
            "results_crosspath_gate.json": sha256(args.crosspath),
            "results_multiway_real.json": sha256(real_path),
        },
        "shards": shards,
        "known_scope_limits": [
            "interaction correlation is fixed at the frozen calibrated average, not varied",
            "finite-A speaker component does not identify a pure-speaker A-to-infinity floor",
            "the pairwise max(Vraw, Vs, Va) adjustment is not a coherent PSD covariance matrix",
        ],
    }
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {args.out}; status={status}; confirmed={confirmed_estimators}")


if __name__ == "__main__":
    main()
