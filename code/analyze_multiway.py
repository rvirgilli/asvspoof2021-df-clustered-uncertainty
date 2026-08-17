"""EXP-105 real-data arm: explicit cell term and linearized multiway CRVE.

This script does not simulate coverage; it implements the first-principles gates
and the real 21DF comparison frozen in PREREG.md. Exact delete-one refits are
checkpointed by cluster and are safe to resume.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from numpy.lib.format import open_memmap


HERE = Path(__file__).resolve().parent
EXP101 = HERE
DERIVED = HERE.parent / "derived"
sys.path.insert(0, str(EXP101))
from m1_campaign import DF_SCORES, KEY, weighted_eer  # noqa: E402

RUN_ROOT = Path(os.environ.get("M1_MULTIWAY_RUN_ROOT",
                               HERE.parent / "regenerated/EXP-105-m1-multiway-correctness"))
H_DENSITY = 0.005
Z95 = 1.959963984540054
SEED = 20260825
REFIT_VERSION = "v2"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_data():
    meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(meta)
    labels = np.array([1 if meta[u][2] == "bonafide" else 0 for u in utts],
                      dtype=np.int8)
    spk_names, spk_idx = np.unique([meta[u][0] for u in utts], return_inverse=True)
    att_names, att_idx = np.unique([meta[u][1] for u in utts], return_inverse=True)
    scores = {}
    for name, path in DF_SCORES.items():
        raw = dict(line.split()[:2] for line in path.read_text().splitlines())
        if set(utts) - set(raw):
            raise ValueError(f"{name}: missing {len(set(utts)-set(raw))} eval trials")
        scores[name] = np.array([float(raw[u]) for u in utts])
    is_spoof = labels == 0
    cell_pairs, cell_idx_spoof = np.unique(
        np.column_stack([spk_idx[is_spoof], att_idx[is_spoof]]), axis=0,
        return_inverse=True)
    cell_idx = np.full(len(labels), -1, dtype=int)
    cell_idx[is_spoof] = cell_idx_spoof
    return (utts, labels, spk_names, spk_idx, att_names, att_idx,
            cell_pairs, cell_idx, scores)


def eer_details(scores, labels):
    order = np.argsort(scores)
    lab = labels[order]
    cb = np.cumsum(lab)
    cs = np.cumsum(1 - lab)
    frr = cb / cb[-1]
    far = 1.0 - cs / cs[-1]
    cut = int(np.argmin(np.abs(frr - far)))
    return {
        "order": order,
        "cut": cut,
        "threshold": float(scores[order[cut]]),
        "frr": float(frr[cut]),
        "far": float(far[cut]),
        "eer": float((frr[cut] + far[cut]) / 2),
    }


def quantile_density(values, p, h):
    lo, hi = max(0.0, p - h), min(1.0, p + h)
    qlo, qhi = np.quantile(values, [lo, hi])
    if qhi <= qlo:
        raise ValueError(f"zero quantile spacing at p={p:.6f}, h={h}")
    return float((hi - lo) / (qhi - qlo))


def influence(scores, labels, h=H_DENSITY):
    """First-order EER influence under a smooth crossing approximation.

    At F_bona(t) + F_spoof(t) = 1, contamination in bona fide is scaled by
    f_spoof/(f_bona+f_spoof), while spoof contamination is scaled by the
    complementary density ratio. Contributions include their empirical 1/n
    factors and sum to zero within numerical tolerance.
    """
    d = eer_details(scores, labels)
    t = d["threshold"]
    bona, spoof = labels == 1, labels == 0
    sb, ss = scores[bona], scores[spoof]
    pb = float(np.mean(sb <= t))
    ps = float(np.mean(ss <= t))
    fb = quantile_density(sb, pb, h)
    fs = quantile_density(ss, ps, h)
    alpha_b, alpha_s = fs / (fb + fs), fb / (fb + fs)
    psi = np.empty(len(labels), dtype=np.float64)
    err_b = (sb <= t).astype(np.float64)
    err_s = (ss > t).astype(np.float64)
    psi[bona] = alpha_b * (err_b - err_b.mean()) / len(sb)
    psi[spoof] = alpha_s * (err_s - err_s.mean()) / len(ss)
    d.update({
        "cdf_bona_at_threshold": pb,
        "cdf_spoof_at_threshold": ps,
        "density_bona": fb,
        "density_spoof": fs,
        "alpha_bona": alpha_b,
        "alpha_spoof": alpha_s,
        "influence_sum": float(psi.sum()),
    })
    # The full 533,928-element ordering is an internal computational object, not
    # an audit result and is not JSON serializable.
    d.pop("order")
    return psi, d


def group_sums(matrix, groups, mask=None):
    if mask is None:
        mask = np.ones(len(groups), dtype=bool)
    g = groups[mask]
    x = matrix[mask]
    levels, inv = np.unique(g, return_inverse=True)
    out = np.zeros((len(levels), matrix.shape[1]), dtype=np.float64)
    np.add.at(out, inv, x)
    return out, levels


def cluster_cov(sums):
    g = len(sums)
    centred = sums - sums.mean(axis=0, keepdims=True)
    return g / (g - 1) * centred.T @ centred


def jack_cov(refits):
    g = len(refits)
    centred = refits - refits.mean(axis=0, keepdims=True)
    return (g - 1) / g * centred.T @ centred


def contract(scores):
    files = {m: {"path": str(DF_SCORES[m]), "sha256": sha256(DF_SCORES[m])}
             for m in sorted(scores)}
    payload = {"key": {"path": str(KEY), "sha256": sha256(KEY)},
               "scores": files, "script_sha256": sha256(Path(__file__))}
    return payload, hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def refit_memmap(kind, masks, names, orders, labels, digest):
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    path = RUN_ROOT / f"delete_one_{kind}_{REFIT_VERSION}.npy"
    sidecar = path.with_suffix(".json")
    state = {"kind": kind, "refit_algorithm_version": REFIT_VERSION,
             "n_groups": len(masks), "systems": names,
             "provenance_sha256": digest}
    if path.exists() or sidecar.exists():
        if not (path.exists() and sidecar.exists()):
            raise RuntimeError(f"partial checkpoint state for {kind}")
        if json.loads(sidecar.read_text()) != state:
            raise RuntimeError(f"refusing to resume {kind} across changed inputs/code")
        out = np.load(path, mmap_mode="r+")
    else:
        out = open_memmap(path, mode="w+", dtype=np.float64,
                          shape=(len(masks), len(names)))
        out[:] = np.nan
        out.flush()
        sidecar.write_text(json.dumps(state, indent=2))
    pending = np.flatnonzero(np.isnan(out).any(axis=1))
    print(f"{kind}: {len(pending)}/{len(masks)} delete-one refits pending", flush=True)
    for done, g in enumerate(pending, 1):
        w = np.ones(len(labels), dtype=np.float64)
        w[masks[g]] = 0.0
        for j, name in enumerate(names):
            out[g, j] = 100 * weighted_eer(orders[name], labels, w)
        if done <= 3 or done % 25 == 0 or done == len(pending):
            out.flush()
            print(f"{kind}: {done}/{len(pending)} pending complete", flush=True)
    return np.asarray(out)


def deletion_prediction(psi, labels, groups, levels, spoof_only=False):
    """Predict exact delete-group changes, including class renormalization."""
    bona, spoof = labels == 1, labels == 0
    out = np.empty((len(levels), psi.shape[1]))
    for j, level in enumerate(levels):
        m = groups == level
        pred = np.zeros(psi.shape[1])
        if not spoof_only:
            frac = m[bona].mean()
            if frac < 1:
                pred -= psi[bona & m].sum(axis=0) / (1 - frac)
        frac = m[spoof].sum() / spoof.sum()
        if frac < 1:
            pred -= psi[spoof & m].sum(axis=0) / (1 - frac)
        out[j] = pred
    return out


def validation(pred, exact, pair_names):
    out = {}
    for j, name in enumerate(pair_names):
        p, e = pred[:, j], exact[:, j]
        corr = float(np.corrcoef(p, e)[0, 1])
        slope = float(np.dot(p, e) / np.dot(p, p)) if np.dot(p, p) else float("nan")
        out[name] = {"correlation": round(corr, 6), "slope": round(slope, 6),
                     "pass": bool(corr >= 0.99 and 0.95 <= slope <= 1.05)}
    return out


def pair_matrix(system_matrix, pairs, names):
    return np.column_stack([system_matrix[:, names.index(a)] - system_matrix[:, names.index(b)]
                            for a, b in pairs])


def nearest_psd(matrix):
    vals, vecs = np.linalg.eigh((matrix + matrix.T) / 2)
    clipped = np.maximum(vals, 0.0)
    return (vecs * clipped) @ vecs.T, vals


def gaussian_supt_q(cov, pairs, names, draws=200000):
    cov_psd, eig = nearest_psd(cov)
    rng = np.random.default_rng(SEED)
    x = rng.multivariate_normal(np.zeros(len(names)), cov_psd, size=draws,
                                check_valid="ignore")
    d = pair_matrix(x, pairs, names)
    sd = np.sqrt(np.maximum(np.diag(pair_cov(cov_psd, pairs, names)), 1e-18))
    q = float(np.percentile(np.max(np.abs(d) / sd, axis=1), 95))
    return q, eig


def pair_cov(cov, pairs, names):
    c = np.zeros((len(pairs), len(names)))
    for j, (a, b) in enumerate(pairs):
        c[j, names.index(a)] = 1
        c[j, names.index(b)] = -1
    return c @ cov @ c.T


def main():
    (utts, labels, spk_names, spk_idx, att_names, att_idx,
     cell_pairs, cell_idx, scores) = load_data()
    names = list(scores)
    orders = {m: np.argsort(scores[m]) for m in names}
    ones = np.ones(len(labels))
    point_system = np.array([100 * weighted_eer(orders[m], labels, ones) for m in names])
    provenance, digest = contract(scores)
    print(f"21DF: {len(utts):,} trials, {len(spk_names)} speakers, "
          f"{len(np.unique(att_idx[labels == 0]))} spoof attacks, "
          f"{len(cell_pairs)} observed spoof speaker×attack cells", flush=True)

    psi_system = np.empty((len(labels), len(names)))
    influence_details = {}
    for j, name in enumerate(names):
        psi_system[:, j], influence_details[name] = influence(scores[name], labels)
        if abs(psi_system[:, j].sum()) > 1e-10:
            raise AssertionError(f"{name}: influence contributions do not sum to zero")
    is_spoof = labels == 0
    spoof_att = att_idx.copy()
    spoof_cell = cell_idx.copy()
    us, spk_levels = group_sums(100 * psi_system, spk_idx)
    ua, att_levels = group_sums(100 * psi_system, spoof_att, is_spoof)
    uc, cell_levels = group_sums(100 * psi_system, spoof_cell, is_spoof)
    cov_spk, cov_att, cov_cell = cluster_cov(us), cluster_cov(ua), cluster_cov(uc)
    cov_crve_raw = cov_spk + cov_att - cov_cell

    spk_masks = [spk_idx == k for k in spk_levels]
    att_masks = [is_spoof & (att_idx == k) for k in att_levels]
    cell_masks = [is_spoof & (cell_idx == k) for k in cell_levels]
    ref_spk = refit_memmap("speaker", spk_masks, names, orders, labels, digest)
    ref_att = refit_memmap("attack", att_masks, names, orders, labels, digest)
    ref_cell = refit_memmap("speaker_attack_cell", cell_masks, names, orders, labels, digest)
    cov_jack_raw = jack_cov(ref_spk) + jack_cov(ref_att) - jack_cov(ref_cell)
    cov_jspk, cov_jatt, cov_jcell = jack_cov(ref_spk), jack_cov(ref_att), jack_cov(ref_cell)

    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    pair_names = [f"{a} vs {b}" for a, b in pairs]
    point_pair = np.array([point_system[names.index(a)] - point_system[names.index(b)]
                           for a, b in pairs])
    psi_pair = pair_matrix(100 * psi_system, pairs, names)
    pred_spk_system = deletion_prediction(100 * psi_system, labels, spk_idx,
                                           spk_levels, spoof_only=False)
    pred_att_system = deletion_prediction(100 * psi_system, labels, att_idx,
                                           att_levels, spoof_only=True)
    exact_spk = pair_matrix(ref_spk - point_system, pairs, names)
    exact_att = pair_matrix(ref_att - point_system, pairs, names)
    pred_spk = pair_matrix(pred_spk_system, pairs, names)
    pred_att = pair_matrix(pred_att_system, pairs, names)
    val_spk = validation(pred_spk, exact_spk, pair_names)
    val_att = validation(pred_att, exact_att, pair_names)

    sel = json.loads((DERIVED / "results_selection.json").read_text())["21df"]
    q_product = float(sel["supt_critical_value"])
    q_crve, eig_crve = gaussian_supt_q(cov_crve_raw, pairs, names)
    q_jack, eig_jack = gaussian_supt_q(cov_jack_raw, pairs, names)
    pcov_crve = pair_cov(cov_crve_raw, pairs, names)
    pcov_jack = pair_cov(cov_jack_raw, pairs, names)
    pcov_spk = pair_cov(cov_spk, pairs, names)
    pcov_att = pair_cov(cov_att, pairs, names)
    pcov_cell = pair_cov(cov_cell, pairs, names)
    pcov_jspk = pair_cov(cov_jspk, pairs, names)
    pcov_jatt = pair_cov(cov_jatt, pairs, names)
    pcov_jcell = pair_cov(cov_jcell, pairs, names)

    per_pair = {}
    for j, key in enumerate(pair_names):
        old = sel["pairs"].get(key) or sel["pairs"][" vs ".join(key.split(" vs ")[::-1])]
        old_se = (old["ci_jackknife"][1] - old["ci_jackknife"][0]) / (2 * Z95)
        v_crve_raw = float(pcov_crve[j, j])
        v_jack_raw = float(pcov_jack[j, j])
        v_spk = float(pcov_spk[j, j])
        v_att = float(pcov_att[j, j])
        v_cell = float(pcov_cell[j, j])
        v_crve_floor = max(v_crve_raw, v_spk, v_att, 0.0)
        # The explicit delete-cell estimator gets the same transparent floor.
        v_js = float(pcov_jspk[j, j])
        v_ja = float(pcov_jatt[j, j])
        v_jc = float(pcov_jcell[j, j])
        v_jack_floor = max(v_jack_raw, v_js, v_ja, 0.0)
        per_pair[key] = {
            "delta_eer_pts": round(float(point_pair[j]), 6),
            "current_iid_proxy_se": round(float(old_se), 6),
            "crve": {
                "V_speaker": v_spk, "V_attack": v_att,
                "V_speaker_attack_cell": v_cell,
                "V_raw_inclusion_exclusion": v_crve_raw,
                "V_psd_floor": v_crve_floor,
                "se_psd_floor": float(np.sqrt(v_crve_floor)),
                "resolved_pointwise": bool(abs(point_pair[j]) > Z95 * np.sqrt(v_crve_floor)),
                "resolved_simultaneous_product_q": bool(
                    abs(point_pair[j]) > q_product * np.sqrt(v_crve_floor)),
                "resolved_simultaneous_own_q": bool(
                    abs(point_pair[j]) > q_crve * np.sqrt(v_crve_floor)),
            },
            "explicit_cell_jackknife": {
                "V_speaker": v_js, "V_attack": v_ja,
                "V_speaker_attack_cell": v_jc,
                "V_raw_inclusion_exclusion": v_jack_raw,
                "V_psd_floor": v_jack_floor,
                "se_psd_floor": float(np.sqrt(v_jack_floor)),
                "resolved_pointwise": bool(abs(point_pair[j]) > Z95 * np.sqrt(v_jack_floor)),
                "resolved_simultaneous_product_q": bool(
                    abs(point_pair[j]) > q_product * np.sqrt(v_jack_floor)),
                "resolved_simultaneous_own_q": bool(
                    abs(point_pair[j]) > q_jack * np.sqrt(v_jack_floor)),
            },
            "linearization_gate": {"speaker": val_spk[key], "attack": val_att[key]},
            "product_bootstrap_resolved_simultaneous": old["resolved_simultaneous"],
        }

    baseline = {"RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"}
    baseline_keys = [k for k in pair_names if set(k.split(" vs ")) <= baseline]
    gate_linear = all(per_pair[k]["linearization_gate"][axis]["pass"]
                      for k in pair_names for axis in ("speaker", "attack"))
    result = {
        "experiment": "EXP-105-real-data",
        "provenance": provenance,
        "density_bandwidth_probability": H_DENSITY,
        "n_trials": len(labels), "n_speakers": len(spk_levels),
        "n_spoof_attacks": len(att_levels), "n_observed_spoof_cells": len(cell_levels),
        "cell_size": {
            "min": int(min(m.sum() for m in cell_masks)),
            "median": float(np.median([m.sum() for m in cell_masks])),
            "max": int(max(m.sum() for m in cell_masks)),
        },
        "system_influence": influence_details,
        "linearization_gate_all_pairs_pass": gate_linear,
        "crve_system_covariance_raw_eigenvalues": eig_crve.tolist(),
        "jackknife_system_covariance_raw_eigenvalues": eig_jack.tolist(),
        "q95_gaussian_crve_psd": q_crve,
        "q95_gaussian_explicit_cell_jackknife_psd": q_jack,
        "q95_product_bootstrap": q_product,
        "pairs": per_pair,
        "organizer_baseline_pairs": baseline_keys,
        "organizer_baseline_resolved": {
            "product_bootstrap": sum(per_pair[k]["product_bootstrap_resolved_simultaneous"]
                                     for k in baseline_keys),
            "crve_floor_product_q": sum(per_pair[k]["crve"]["resolved_simultaneous_product_q"]
                                        for k in baseline_keys),
            "explicit_cell_floor_product_q": sum(
                per_pair[k]["explicit_cell_jackknife"]["resolved_simultaneous_product_q"]
                for k in baseline_keys),
        },
    }
    out = DERIVED / "results_multiway_real.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {out}; linearization gate all-pairs={gate_linear}; "
          f"baseline resolved={result['organizer_baseline_resolved']}", flush=True)


if __name__ == "__main__":
    main()
