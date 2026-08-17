"""EXP-105 exact-cell coverage campaign on the real 21DF incidence.

The analytic path uses exact delete-one EER refits implemented with grouped
rank searches. It is intentionally independent of the smooth influence path
that failed the real-data linearization gate.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path
from statistics import NormalDist

import numpy as np
from numba import njit


HERE = Path(__file__).resolve().parent
EXP101 = HERE
DERIVED = HERE.parent / "derived"
sys.path.insert(0, str(EXP101))
import power_curves as pc  # noqa: E402

SEED = 20260824
R_GRID = 1000
R_GATE = 2000
B_PRODUCT = 500
Z95 = 1.959963984540054
INTERACTION_SHARES = (0.0, 0.25, 0.50, 0.75)
TAILS = ("gaussian", "t5")
DELTAS = (0.0, 0.5, 2.0)
REGIMES = ("organizer", "low_eer")
BASE_EER = {"organizer": 22.383342 / 100.0, "low_eer": 0.03}
POP_N = 4_000_000
POP_VALID_N = 1_000_000
RUN_ROOT = Path(os.environ.get(
    "M1_MULTIWAY_COVERAGE_ROOT",
    HERE.parent / "regenerated/EXP-105-m1-multiway-correctness/coverage"))


def script_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def load_incidence():
    meta = {}
    for line in pc.KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(meta)
    labels = np.array([1 if meta[u][2] == "bonafide" else 0 for u in utts],
                      dtype=np.int8)
    _, spk = np.unique([meta[u][0] for u in utts], return_inverse=True)
    spoof = labels == 0
    attack_name = np.array([meta[u][1] for u in utts])
    _, compact_attack = np.unique(attack_name[spoof], return_inverse=True)
    attack = np.full(len(labels), -1, dtype=np.int32)
    attack[spoof] = compact_attack
    cell = np.full(len(labels), -1, dtype=np.int32)
    _, cell[spoof] = np.unique(
        np.column_stack([spk[spoof], attack[spoof]]), axis=0,
        return_inverse=True)
    return (labels, spk.astype(np.int32), attack, cell,
            int(spk.max() + 1), int(attack.max() + 1), int(cell.max() + 1))


def standard_draw(rng, n, tail):
    z = rng.standard_normal(n)
    if tail == "gaussian":
        return z
    # A standardized t(5): z/sqrt(chi2/5) has variance 5/3.
    return z / np.sqrt(rng.chisquare(5, n) / 5.0) * math.sqrt(3.0 / 5.0)


def bivariate_draw(rng, n, sd0, sd1, rho, tail):
    rho = float(np.clip(rho, -0.999, 0.999))
    z0, z1 = rng.standard_normal(n), rng.standard_normal(n)
    out0 = z0
    out1 = rho * z0 + math.sqrt(1.0 - rho * rho) * z1
    if tail == "t5":
        scale = np.sqrt(rng.chisquare(5, n) / 5.0)
        norm = math.sqrt(3.0 / 5.0)
        out0, out1 = norm * out0 / scale, norm * out1 / scale
    return sd0 * out0, sd1 * out1


def calibration(regime):
    key = "high_icc_organizer" if regime == "organizer" else "low_eer_sota"
    cal, _ = pc.calibrate(pc.PAIRS[key])
    # JSON-safe plain floats make the frozen cell specification auditable.
    return {arm: {k: float(v) for k, v in values.items()}
            for arm, values in cal.items()}


def cell_spec(regime, interaction_share, tail, delta):
    cal = calibration(regime)
    b, s = cal["bona"], cal["spoof"]
    cluster_var = [s[f"sd_spk{k}"] ** 2 + s[f"sd_att{k}"] ** 2
                   for k in (0, 1)]
    remain = 1.0 - interaction_share
    spec = {
        "regime": regime, "interaction_share": interaction_share,
        "tail": tail, "target_delta_pts": delta, "calibration": cal,
        "sd_spk": [math.sqrt(remain) * s[f"sd_spk{k}"] for k in (0, 1)],
        "sd_att": [math.sqrt(remain) * s[f"sd_att{k}"] for k in (0, 1)],
        "sd_interaction": [math.sqrt(interaction_share * cluster_var[k])
                           for k in (0, 1)],
        "rho_interaction": float(np.clip(
            0.5 * (s["rho_spk"] + s["rho_att"]), -0.999, 0.999)),
    }
    # Fix each marginal population EER by a large, seed-frozen quantile draw.
    # For higher-is-bona scores, target e is obtained by
    # mu_spoof = Q_bona(e) - Q_spoof_zero(1-e).
    ridx = REGIMES.index(regime)
    hidx = INTERACTION_SHARES.index(interaction_share)
    tidx = TAILS.index(tail)
    rng = np.random.default_rng(np.random.SeedSequence(
        [SEED, 991, ridx, hidx, tidx]))
    mu_spoof, achieved = [], []
    targets = [BASE_EER[regime], BASE_EER[regime] - delta / 100.0]
    if targets[1] <= 0.0005:
        raise ValueError(f"invalid low-EER target for delta={delta}")
    for k, target in enumerate(targets):
        def draw_marginals(n):
            bona_draw = (b[f"sd_grp{k}"] * standard_draw(rng, n, tail) +
                         b[f"sd_res{k}"] * rng.standard_normal(n))
            spoof_draw = (spec["sd_spk"][k] * standard_draw(rng, n, tail) +
                          spec["sd_att"][k] * standard_draw(rng, n, tail) +
                          spec["sd_interaction"][k] * standard_draw(rng, n, tail) +
                          s[f"sd_res{k}"] * rng.standard_normal(n))
            return bona_draw, spoof_draw

        if tail == "gaussian":
            sd_bona = math.sqrt(b[f"sd_grp{k}"] ** 2 + b[f"sd_res{k}"] ** 2)
            sd_spoof = math.sqrt(spec["sd_spk"][k] ** 2 +
                                 spec["sd_att"][k] ** 2 +
                                 spec["sd_interaction"][k] ** 2 +
                                 s[f"sd_res{k}"] ** 2)
            q = NormalDist().inv_cdf(target)
            # Q_b(e) - Q_s(1-e), with Q_s(1-e)=-sd_s*Q(e).
            mu = float((sd_bona + sd_spoof) * q)
        else:
            bona_zero, spoof_zero = draw_marginals(POP_N)
            mu = float(np.quantile(bona_zero, target) -
                       np.quantile(spoof_zero, 1.0 - target))
        mu_spoof.append(mu)
        bona_val, spoof_val = draw_marginals(POP_VALID_N)
        val_labels = np.concatenate([np.ones(POP_VALID_N, dtype=np.int8),
                                     np.zeros(POP_VALID_N, dtype=np.int8)])
        val_scores = np.concatenate([bona_val, spoof_val + mu])
        val_eer = point_eer(np.argsort(val_scores), val_labels)
        error_pts = 100.0 * (val_eer - target)
        if abs(error_pts) > 0.10:
            raise RuntimeError(f"population calibration error {error_pts:.4f} points")
        achieved.append({"target": target, "independent_validation_eer": val_eer,
                         "validation_error_pts": error_pts,
                         "calibration_method": ("analytic_normal" if tail == "gaussian"
                                                else f"quantile_mc_n{POP_N}")})
    spec["mu_spoof"] = mu_spoof
    spec["population_calibration"] = achieved
    spec["true_delta_pts"] = 100.0 * (targets[0] - targets[1])
    return spec


def generate(rng, spec, labels, spk, attack, cell, n_spk, n_att, n_cell):
    cal = spec["calibration"]
    b, s = cal["bona"], cal["spoof"]
    tail = spec["tail"]
    bona, spoof = labels == 1, labels == 0
    ub0, ub1 = bivariate_draw(rng, n_spk, b["sd_grp0"], b["sd_grp1"],
                              b["rho_grp"], tail)
    us0, us1 = bivariate_draw(rng, n_spk, spec["sd_spk"][0],
                              spec["sd_spk"][1], s["rho_spk"], tail)
    va0, va1 = bivariate_draw(rng, n_att, spec["sd_att"][0],
                              spec["sd_att"][1], s["rho_att"], tail)
    wi0, wi1 = bivariate_draw(rng, n_cell, spec["sd_interaction"][0],
                              spec["sd_interaction"][1],
                              spec["rho_interaction"], tail)
    eb0, eb1 = bivariate_draw(rng, int(bona.sum()), b["sd_res0"],
                              b["sd_res1"], b["rho_res"], "gaussian")
    es0, es1 = bivariate_draw(rng, int(spoof.sum()), s["sd_res0"],
                              s["sd_res1"], s["rho_res"], "gaussian")
    out0, out1 = np.empty(len(labels)), np.empty(len(labels))
    out0[bona] = ub0[spk[bona]] + eb0
    out1[bona] = ub1[spk[bona]] + eb1
    out0[spoof] = (spec["mu_spoof"][0] + us0[spk[spoof]] +
                   va0[attack[spoof]] + wi0[cell[spoof]] + es0)
    out1[spoof] = (spec["mu_spoof"][1] + us1[spk[spoof]] +
                   va1[attack[spoof]] + wi1[cell[spoof]] + es1)
    return out0, out1


def point_eer(order, labels):
    lab = labels[order]
    cb, cs = np.cumsum(lab), np.cumsum(1 - lab)
    frr, far = cb / cb[-1], 1.0 - cs / cs[-1]
    k = int(np.argmin(np.abs(frr - far)))
    return float((frr[k] + far[k]) / 2.0)


def grouped_positions(order, labels, groups, n_groups):
    """CSR arrays of rank positions by group and class."""
    lab = labels[order]
    grp = groups[order]
    result = []
    for target in (1, 0):
        valid = (grp >= 0) & (lab == target)
        positions = np.flatnonzero(valid).astype(np.int64)
        g = grp[valid]
        idx = np.lexsort((positions, g))
        positions = positions[idx]
        counts = np.bincount(g, minlength=n_groups)
        offsets = np.concatenate([[0], np.cumsum(counts)]).astype(np.int64)
        result.extend([positions, offsets])
    return tuple(result)


@njit(cache=True)
def _upper_bound(values, start, end, target):
    lo, hi = start, end
    while lo < hi:
        mid = (lo + hi) // 2
        if values[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo - start


@njit(cache=True)
def delete_one_eers(labels_order, bona_pos, bona_off, spoof_pos, spoof_off):
    n_groups = len(bona_off) - 1
    n = len(labels_order)
    cb = np.cumsum(labels_order)
    cs = np.cumsum(1 - labels_order)
    total_b, total_s = cb[-1], cs[-1]
    out = np.empty(n_groups)
    for g in range(n_groups):
        gb = bona_off[g + 1] - bona_off[g]
        gs = spoof_off[g + 1] - spoof_off[g]
        rem_b, rem_s = total_b - gb, total_s - gs
        lo, hi = 0, n - 1
        while lo < hi:
            mid = (lo + hi) // 2
            db = _upper_bound(bona_pos, bona_off[g], bona_off[g + 1], mid)
            ds = _upper_bound(spoof_pos, spoof_off[g], spoof_off[g + 1], mid)
            diff = (cb[mid] - db) / rem_b + (cs[mid] - ds) / rem_s - 1.0
            if diff < 0.0:
                lo = mid + 1
            else:
                hi = mid
        best_gap = 1e300
        best_eer = 0.0
        for k in (lo - 1, lo):
            if k < 0 or k >= n:
                continue
            db = _upper_bound(bona_pos, bona_off[g], bona_off[g + 1], k)
            ds = _upper_bound(spoof_pos, spoof_off[g], spoof_off[g + 1], k)
            frr = (cb[k] - db) / rem_b
            far = 1.0 - (cs[k] - ds) / rem_s
            gap = abs(frr - far)
            if gap < best_gap:
                best_gap = gap
                best_eer = 0.5 * (frr + far)
        out[g] = best_eer
    return out


def exact_refits(scores, labels, groups, n_groups, order=None):
    if order is None:
        order = np.argsort(scores)
    arrays = grouped_positions(order, labels, groups, n_groups)
    return delete_one_eers(labels[order], *arrays)


def jack_var(values):
    g = len(values)
    return (g - 1.0) / g * float(np.sum((values - values.mean()) ** 2))


@njit(cache=True)
def product_two_eers(order0, order1, labels, spk, attack, cs_weight,
                     ca_weight, bona_counts, cell_spk, cell_attack, cell_counts):
    total_b = 0.0
    for s in range(len(bona_counts)):
        total_b += cs_weight[s] * bona_counts[s]
    total_s = 0.0
    for c in range(len(cell_counts)):
        total_s += (cell_counts[c] * cs_weight[cell_spk[c]] *
                    ca_weight[cell_attack[c]])
    if total_b <= 0.0 or total_s <= 0.0:
        return np.nan, np.nan
    cb0 = cs0 = cb1 = cs1 = 0.0
    best_gap0 = best_gap1 = 1e300
    best_eer0 = best_eer1 = 0.0
    for k in range(len(labels)):
        i0 = order0[k]
        w0 = cs_weight[spk[i0]]
        if labels[i0] == 1:
            cb0 += w0
        else:
            w0 *= ca_weight[attack[i0]]
            cs0 += w0
        frr0 = cb0 / total_b
        far0 = 1.0 - cs0 / total_s
        gap0 = abs(frr0 - far0)
        if gap0 < best_gap0:
            best_gap0 = gap0
            best_eer0 = 0.5 * (frr0 + far0)

        i1 = order1[k]
        w1 = cs_weight[spk[i1]]
        if labels[i1] == 1:
            cb1 += w1
        else:
            w1 *= ca_weight[attack[i1]]
            cs1 += w1
        frr1 = cb1 / total_b
        far1 = 1.0 - cs1 / total_s
        gap1 = abs(frr1 - far1)
        if gap1 < best_gap1:
            best_gap1 = gap1
            best_eer1 = 0.5 * (frr1 + far1)
    return best_eer0, best_eer1


def product_interval(rng, order0, order1, labels, spk, attack, cell,
                     n_spk, n_att, n_cell):
    bona_counts = np.bincount(spk[labels == 1], minlength=n_spk).astype(np.int64)
    spoof = labels == 0
    cell_counts = np.bincount(cell[spoof], minlength=n_cell).astype(np.int64)
    first = np.full(n_cell, -1, dtype=np.int64)
    for i in np.flatnonzero(spoof):
        c = cell[i]
        if first[c] < 0:
            first[c] = i
    if np.any(first < 0):
        raise RuntimeError("empty compact speaker-attack cell")
    cell_spk = spk[first].astype(np.int64)
    cell_attack = attack[first].astype(np.int64)
    draws = np.empty(B_PRODUCT)
    for b in range(B_PRODUCT):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        ca = np.bincount(rng.integers(0, n_att, n_att), minlength=n_att)
        eer0, eer1 = product_two_eers(
            order0, order1, labels, spk, attack, cs, ca, bona_counts,
            cell_spk, cell_attack, cell_counts)
        if not np.isfinite(eer0 + eer1):
            raise RuntimeError("product bootstrap replicate lost one class")
        draws[b] = 100.0 * (eer0 - eer1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def one_replicate(rep, spec, incidence, include_product=True):
    labels, spk, attack, cell, n_spk, n_att, n_cell = incidence
    ridx = REGIMES.index(spec["regime"])
    hidx = INTERACTION_SHARES.index(spec["interaction_share"])
    tidx = TAILS.index(spec["tail"])
    didx = DELTAS.index(spec["target_delta_pts"])
    rng = np.random.default_rng(np.random.SeedSequence(
        [SEED, ridx, hidx, tidx, didx, rep]))
    s0, s1 = generate(rng, spec, *incidence)
    order0, order1 = np.argsort(s0), np.argsort(s1)
    d_hat = 100.0 * (point_eer(order0, labels) - point_eer(order1, labels))
    components = {}
    for name, groups, count in (("speaker", spk, n_spk),
                                ("attack", attack, n_att),
                                ("cell", cell, n_cell)):
        r0 = exact_refits(s0, labels, groups, count, order=order0)
        r1 = exact_refits(s1, labels, groups, count, order=order1)
        components[name] = jack_var(100.0 * (r0 - r1))
    raw = components["speaker"] + components["attack"] - components["cell"]
    floor = max(raw, components["speaker"], components["attack"])
    truth = spec["true_delta_pts"]
    raw_valid = raw > 0.0
    raw_width = 2.0 * Z95 * math.sqrt(raw) if raw_valid else math.nan
    floor_width = 2.0 * Z95 * math.sqrt(floor)
    result = {
        "d_hat": d_hat, **{f"v_{k}": v for k, v in components.items()},
        "v_raw": raw, "v_floor": floor,
        "raw_cover": bool(raw_valid and abs(d_hat - truth) <= Z95 * math.sqrt(raw)),
        "floor_cover": bool(abs(d_hat - truth) <= Z95 * math.sqrt(floor)),
        "raw_width": raw_width, "floor_width": floor_width,
    }
    if include_product:
        boot_rng = np.random.default_rng(np.random.SeedSequence(
            [SEED, ridx, hidx, tidx, didx, rep, 777]))
        lo, hi = product_interval(boot_rng, order0, order1, labels, spk, attack,
                                  cell, n_spk, n_att, n_cell)
        result.update({"product_lo": lo, "product_hi": hi,
                       "product_cover": bool(lo <= truth <= hi),
                       "product_width": hi - lo})
    return result


def wilson(k, n, z=Z95):
    p = k / n
    den = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / den
    return [centre - half, centre + half]


def grid_tuple(index):
    grid = [(r, h, t, d) for r in REGIMES for h in INTERACTION_SHARES
            for t in TAILS for d in DELTAS]
    return grid[index]


def run_cell(index, R, include_product=True, namespace="grid"):
    regime, share, tail, delta = grid_tuple(index)
    spec = cell_spec(regime, share, tail, delta)
    incidence = load_incidence()
    outdir = (RUN_ROOT / f"grid_{index:02d}" if namespace == "grid"
              else RUN_ROOT / namespace)
    outdir.mkdir(parents=True, exist_ok=True)
    state_path = outdir / "replicates.jsonl"
    meta_path = outdir / "contract.json"
    contract = {"script_sha256": script_hash(), "seed": SEED, "R": R,
                "index": index, "spec": spec,
                "include_product_bootstrap": include_product,
                "B_product": B_PRODUCT if include_product else 0,
                "incidence": {"n_trials": len(incidence[0]),
                              "n_speakers": incidence[4],
                              "n_attacks": incidence[5],
                              "n_cells": incidence[6]}}
    if meta_path.exists():
        if json.loads(meta_path.read_text()) != contract:
            raise RuntimeError(f"grid {index}: checkpoint contract changed")
    else:
        meta_path.write_text(json.dumps(contract, indent=2) + "\n")
    rows = []
    if state_path.exists():
        rows = [json.loads(line) for line in state_path.read_text().splitlines() if line]
    if len(rows) > R:
        raise RuntimeError(f"grid {index}: checkpoint has {len(rows)} rows > R={R}")
    t0 = time.time()
    for rep in range(len(rows), R):
        row = one_replicate(rep, spec, incidence, include_product=include_product)
        with open(state_path, "a") as f:
            f.write(json.dumps(row) + "\n")
        rows.append(row)
        if rep < 2 or (rep + 1) % 25 == 0 or rep + 1 == R:
            print(f"grid {index:02d} {regime} h={share} {tail} d={delta}: "
                  f"{rep+1}/{R} ({(time.time()-t0)/60:.1f} min)", flush=True)
    raw_k = sum(r["raw_cover"] for r in rows)
    floor_k = sum(r["floor_cover"] for r in rows)
    result = {
        "index": index, "spec": spec, "R": R,
        "raw": {"coverage": raw_k / R, "wilson95": wilson(raw_k, R),
                "median_width": float(np.nanmedian([r["raw_width"] for r in rows])),
                "failure_rate": sum(not np.isfinite(r["raw_width"]) for r in rows) / R},
        "floor": {"coverage": floor_k / R, "wilson95": wilson(floor_k, R),
                  "median_width": float(np.median([r["floor_width"] for r in rows])),
                  "failure_rate": 0.0},
        "mc_variance": float(np.var([r["d_hat"] for r in rows], ddof=1)),
        "mean_components": {key: float(np.mean([r[key] for r in rows]))
                            for key in ("v_speaker", "v_attack", "v_cell",
                                        "v_raw", "v_floor")},
    }
    if include_product:
        product_k = sum(r["product_cover"] for r in rows)
        result["product"] = {
            "B": B_PRODUCT, "coverage": product_k / R,
            "wilson95": wilson(product_k, R),
            "median_width": float(np.median([r["product_width"] for r in rows])),
            "failure_rate": 0.0,
        }
    (outdir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run_gate(R):
    # Organizer-like, Gaussian, additive, Delta=0 is grid index 0.
    result = run_cell(0, R, include_product=False, namespace="gate_additive")
    ratio = result["mean_components"]["v_raw"] / result["mc_variance"]
    gate = {"R": R, "mean_raw_multiway_over_mc_variance": ratio,
            "pass": bool(0.90 <= ratio <= 1.10), "cell_result": result}
    (RUN_ROOT / "additive_gate.json").write_text(json.dumps(gate, indent=2) + "\n")
    print(f"additive gate ratio={ratio:.4f}: {'PASS' if gate['pass'] else 'FAIL'}",
          flush=True)
    return gate


def aggregate(R):
    results = []
    for index in range(48):
        path = RUN_ROOT / f"grid_{index:02d}/result.json"
        if not path.exists():
            raise RuntimeError(f"missing {path}")
        row = json.loads(path.read_text())
        if row["R"] != R:
            raise RuntimeError(f"grid {index} has R={row['R']}, expected {R}")
        results.append(row)
    floor_ok = all(0.92 <= row["floor"]["coverage"] <= 0.98 for row in results)
    raw_ok = all(row["raw"]["failure_rate"] == 0 and
                 0.92 <= row["raw"]["coverage"] <= 0.98 for row in results)
    product_ok = all(0.92 <= row["product"]["coverage"] <= 0.98
                     for row in results)
    output = {"experiment": "EXP-105", "seed": SEED, "R": R,
              "script_sha256": script_hash(), "grid": results,
              "all_cells_floor_inside_092_098": floor_ok,
              "all_cells_raw_inside_092_098": raw_ok,
              "all_cells_product_inside_092_098": product_ok}
    out = DERIVED / "results_coverage_interaction.json"
    out.write_text(json.dumps(output, indent=2) + "\n")
    print(f"wrote {out}; raw_all={raw_ok}, floor_all={floor_ok}, "
          f"product_all={product_ok}", flush=True)


def self_check():
    labels = np.array([1, 0, 1, 0, 1, 0, 1, 0], dtype=np.int8)
    groups = np.array([0, 0, 0, 1, 1, 1, 2, 2], dtype=np.int32)
    scores = np.array([.9, .1, .8, .2, .7, .3, .6, .4])
    fast = exact_refits(scores, labels, groups, 3)
    slow = []
    order = np.argsort(scores)
    for g in range(3):
        w = (groups != g).astype(float)
        slow.append(pc.weighted_eer(order, labels, w))
    if not np.allclose(fast, slow, atol=1e-15):
        raise AssertionError((fast, slow))
    # The compiled product kernel must reproduce the released weighted-EER
    # implementation for the same shared cluster weights, including zero-weight
    # plateaus and its deterministic first-minimum tie rule.
    spk = np.array([0, 0, 1, 1, 2, 2, 3, 3], dtype=np.int32)
    attack = np.array([-1, 0, -1, 1, -1, 0, -1, 1], dtype=np.int32)
    cell = np.array([-1, 0, -1, 1, -1, 2, -1, 3], dtype=np.int32)
    order0 = np.argsort(scores)
    order1 = np.argsort(scores[::-1])
    bona_counts = np.bincount(spk[labels == 1], minlength=4).astype(np.int64)
    cell_counts = np.bincount(cell[labels == 0], minlength=4).astype(np.int64)
    cell_spk = np.array([0, 1, 2, 3], dtype=np.int64)
    cell_attack = np.array([0, 1, 0, 1], dtype=np.int64)
    rng = np.random.default_rng(91)
    for _ in range(20):
        csw = np.bincount(rng.integers(0, 4, 4), minlength=4)
        caw = np.bincount(rng.integers(0, 2, 2), minlength=2)
        w = csw[spk].astype(float)
        w[labels == 0] *= caw[attack[labels == 0]]
        if w[labels == 1].sum() == 0 or w[labels == 0].sum() == 0:
            continue
        got = product_two_eers(order0, order1, labels, spk, attack, csw, caw,
                               bona_counts, cell_spk, cell_attack, cell_counts)
        want = (pc.weighted_eer(order0, labels, w),
                pc.weighted_eer(order1, labels, w))
        if not np.allclose(got, want, atol=1e-15):
            raise AssertionError((got, want))
    incidence = load_incidence()
    print(f"self-check PASS; real incidence={len(incidence[0]):,} trials, "
          f"{incidence[4]} speakers, {incidence[5]} attacks, {incidence[6]} cells")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--grid-index", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--R", type=int, default=R_GRID)
    ap.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    args = ap.parse_args()
    if args.self_check:
        self_check()
        return
    expected_r = R_GATE if args.gate else R_GRID
    if (args.R != expected_r and
            RUN_ROOT == HERE.parent / "regenerated/EXP-105-m1-multiway-correctness/coverage"):
        raise RuntimeError(f"R={args.R} may not write to the official run root; "
                           f"this mode is frozen at R={expected_r}")
    if args.gate:
        run_gate(args.R)
    elif args.grid_index is not None:
        run_cell(args.grid_index, args.R)
    elif args.all:
        gate_path = RUN_ROOT / "additive_gate.json"
        if not gate_path.exists() or not json.loads(gate_path.read_text())["pass"]:
            raise RuntimeError("additive gate must pass before the interaction grid")
        # Warm JIT before forking; workers then share compiled machine code.
        self_check()
        ctx = get_context("fork")
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx) as pool:
            futures = {pool.submit(run_cell, i, args.R): i for i in range(48)}
            for future in as_completed(futures):
                future.result()
    elif args.aggregate:
        aggregate(args.R)
    else:
        ap.error("choose --self-check, --gate, --grid-index, --all, or --aggregate")


if __name__ == "__main__":
    main()
