"""EXP-116: simultaneous max-t bands under each registered weighting rule.

Reuses EXP-108's score-blind weight builder and score loader so the 12 rules are exactly
the frozen ones, and gates the estimator on reproducing EXP-108's full-data contrasts
before any resampling. See PREREG.md.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EXP108 = HERE.parent / "code" / "exp108"  # public path-adapted copy; private FREEZE.sha256 binds the original
sys.path.insert(0, str(EXP108))

from analyze import SCORE_PATHS, SYSTEMS, PAIRS, load_scores  # noqa: E402
from build_contract import (  # noqa: E402
    DEFAULT_METADATA,
    POLICIES,
    build_policy_weights,
    load_trials,
    sha256_bytes,
    sha256_file,
    validate_policy,
)

B = 5000
BASE_SEED = 20260909
LAWS = ("trial", "pw")
MODERN = set(SYSTEMS[:4])
PAIR_NAMES = [f"{a} vs {b}" for a, b in PAIRS]


def pair_block(a: str, b: str) -> str:
    if (a in MODERN) != (b in MODERN):
        return "cross"
    return "within_ssl" if a in MODERN else "within_baseline"


BLOCKS = [pair_block(a, b) for a, b in PAIRS]

# Process-global data, populated once in the parent before forking.
G: dict[str, object] = {}


def weighted_eer_sorted(order: np.ndarray, labels: np.ndarray, w: np.ndarray) -> float:
    l = labels[order]
    ws = w[order]
    cb = np.cumsum(ws * l)
    cs = np.cumsum(ws * (1 - l))
    frr = cb / cb[-1]
    far = 1.0 - cs / cs[-1]
    i = int(np.argmin(np.abs(frr - far)))
    return float((frr[i] + far[i]) / 2.0)


def contrasts(w: np.ndarray) -> np.ndarray:
    eers = {m: 100.0 * weighted_eer_sorted(G["orders"][m], G["labels"], w) for m in SYSTEMS}
    return np.array([eers[a] - eers[b] for a, b in PAIRS])


def run_cell(task: tuple[int, int]) -> dict[str, object]:
    k, ell = task
    rule = POLICIES[k]
    law = LAWS[ell]
    seed = BASE_SEED + 100 * k + ell
    rng = np.random.default_rng(seed)
    w0 = G["policies"][rule]
    labels = G["labels"]
    spk = G["spk_idx"]
    att = G["att_idx"]
    is_spoof = labels == 0
    is_bona = ~is_spoof
    n_spk = int(spk.max()) + 1
    spoof_atts = np.unique(att[is_spoof])
    n_att = int(att.max()) + 1
    bona_pos = np.flatnonzero(is_bona)
    spoof_pos = np.flatnonzero(is_spoof)
    t0 = time.time()
    reps = np.empty((B, len(PAIRS)))
    for b in range(B):
        if law == "trial":
            c = np.zeros(len(labels))
            c[bona_pos] = np.bincount(rng.integers(0, len(bona_pos), len(bona_pos)), minlength=len(bona_pos))
            c[spoof_pos] = np.bincount(rng.integers(0, len(spoof_pos), len(spoof_pos)), minlength=len(spoof_pos))
            w = w0 * c
        else:
            cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
            w = w0 * cs[spk]
            drawn = rng.choice(spoof_atts, size=len(spoof_atts), replace=True)
            ca = np.bincount(drawn, minlength=n_att)
            w[is_spoof] *= ca[att[is_spoof]]
        reps[b] = contrasts(w)
    hat = G["hat"][rule]
    s = reps.std(axis=0, ddof=1)
    z = np.abs(reps - reps.mean(axis=0)) / s
    q = float(np.percentile(z.max(axis=1), 95))
    lo, hi = hat - q * s, hat + q * s
    ind = ~((lo <= 0) & (0 <= hi))
    pairs = {
        name: {
            "delta_hat": float(hat[i]),
            "band": [float(lo[i]), float(hi[i])],
            "sd": float(s[i]),
            "separated": bool(ind[i]),
            "block": BLOCKS[i],
        }
        for i, name in enumerate(PAIR_NAMES)
    }
    counts = {
        blk: {"separated": int(sum(ind[i] for i in range(len(PAIRS)) if BLOCKS[i] == blk)),
              "total": BLOCKS.count(blk)}
        for blk in ("cross", "within_ssl", "within_baseline")
    }
    return {
        "rule": rule, "law": law, "seed": seed, "B": B, "q95": q,
        "wall_seconds": round(time.time() - t0, 1), "counts": counts, "pairs": pairs,
    }


def main() -> None:
    out_path = HERE / "RESULTS.json"
    if out_path.exists():
        raise SystemExit("RESULTS.json exists; refusing to overwrite a result of record")
    t_start = time.time()
    metadata = DEFAULT_METADATA
    rows = load_trials(metadata)
    labels = np.asarray([1 if r.label == "bonafide" else 0 for r in rows], dtype=np.int8)
    policies = build_policy_weights(rows)
    contract = json.loads((EXP108 / "contract.json").read_text())
    for name in POLICIES:
        v = validate_policy(rows, name, policies[name])
        if v["sha256_float64_le"] != contract["policies"][name]["sha256_float64_le"]:
            raise RuntimeError(f"policy contract drift: {name}")
    scores, _alignment = load_scores(rows, metadata)
    spk_idx = np.unique([r.speaker for r in rows], return_inverse=True)[1]
    att_idx = np.unique([r.attack for r in rows], return_inverse=True)[1]
    G.update(
        labels=labels, spk_idx=spk_idx, att_idx=att_idx,
        orders={m: np.argsort(scores[m]) for m in SYSTEMS},
        policies={name: np.asarray(policies[name], dtype=np.float64) for name in POLICIES},
    )
    # Estimator gate: full-data contrasts must reproduce EXP-108 to 1e-9 for every rule.
    exp108 = json.loads((EXP108 / "results.json").read_text())
    hat: dict[str, np.ndarray] = {}
    worst = 0.0
    for name in POLICIES:
        h = contrasts(G["policies"][name])
        ref = np.array([exp108["policies"][name]["delta_eer_pct_points"][p] for p in PAIR_NAMES])
        worst = max(worst, float(np.max(np.abs(h - ref))))
        hat[name] = h
    if worst > 1e-9:
        raise RuntimeError(f"estimator gate failed: max |delta - EXP-108| = {worst}")
    G["hat"] = hat
    print(f"estimator gate passed: max deviation {worst:.3e} points over 12 rules x 28 pairs", flush=True)

    tasks = [(k, ell) for k in range(len(POLICIES)) for ell in range(len(LAWS))]
    n_proc = int(os.environ.get("EXP116_PROCS", "12"))
    with mp.get_context("fork").Pool(n_proc) as pool:
        cells = pool.map(run_cell, tasks, chunksize=1)

    cross = [(c["rule"], c["law"], n) for c in cells for n, p in c["pairs"].items()
             if p["block"] == "cross" and not p["separated"]]
    n_cross_total = sum(c["counts"]["cross"]["total"] for c in cells)
    n_cross_sep = sum(c["counts"]["cross"]["separated"] for c in cells)
    reading = ("all_cross_cohort_pairs_separated_under_all_rules_and_laws"
               if n_cross_sep == n_cross_total else "narrowed_wording_required")
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              cwd=HERE).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                           cwd=HERE).stdout
    result = {
        "experiment": "EXP-116-m1-policy-bands",
        "prereg_sha256": sha256_file(HERE / "PREREG.md"),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "producer_git_head": git_head,
        "working_tree_dirty_paths": sorted({l[3:] for l in dirty.splitlines()}),
        "input_sha256": {
            "trial_metadata": sha256_file(metadata),
            "exp108_contract": sha256_file(EXP108 / "contract.json"),
            "exp108_results": sha256_file(EXP108 / "results.json"),
            **{f"scores/{m}": sha256_file(p) for m, p in SCORE_PATHS.items()},
        },
        "estimator_gate_max_abs_deviation_points": worst,
        "B": B, "base_seed": BASE_SEED, "laws": list(LAWS), "rules": list(POLICIES),
        "cross_cohort_indicators": {"separated": n_cross_sep, "total": n_cross_total},
        "cross_cohort_failures": [{"rule": r, "law": l, "pair": n} for r, l, n in cross],
        "registered_reading": reading,
        "cells": cells,
        "wall_seconds_total": round(time.time() - t_start, 1),
    }
    out_path.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("cross_cohort_indicators", "registered_reading",
                                              "cross_cohort_failures", "wall_seconds_total")}, indent=1))
    for c in cells:
        print(f"{c['rule']:<6} {c['law']:<5} q95={c['q95']:.3f} cross {c['counts']['cross']['separated']}/16 "
              f"within_ssl {c['counts']['within_ssl']['separated']}/6 "
              f"within_baseline {c['counts']['within_baseline']['separated']}/6 [{c['wall_seconds']}s]")
    print(f"wrote {out_path} sha256={sha256_bytes(out_path.read_bytes())}")


if __name__ == "__main__":
    main()
