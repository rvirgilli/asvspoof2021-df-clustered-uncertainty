"""EXP-118: pooled versus class-stratified trial bootstrap on SpoofCeleb (see PREREG.md)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EXP101 = HERE.parent / "EXP-101-m1-campaign"
EXP114 = HERE.parent / "EXP-114-m1-spoofceleb-confirmation"
sys.path.insert(0, str(EXP101))
from m1_campaign import weighted_eer  # noqa: E402

INPUTS = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "inputs"
SYSTEMS = ("aasist", "ssl_aasist", "sls", "xlsr_mamba")
B = 5000
SEED_POOLED = 20_260_829
SEED_STRATIFIED = 20_260_909
MANIFEST_SHA = "008371adaeb300401357a58035d3c4ac9e1c440abe804ceab8ccd1bdc84b2544"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load():
    manifest = INPUTS / "inputs" / "spoofceleb_evaluation.csv"
    if sha(manifest) != MANIFEST_SHA:
        raise SystemExit("manifest hash differs from the EXP-114 manifest of record")
    with manifest.open(newline="") as f:
        rows = list(csv.DictReader(f))
    utts = [r["utt"] for r in rows]
    labels = np.array([1 if r["label"] == "bonafide" else 0 for r in rows], dtype=np.int64)
    scores = {}
    for s in SYSTEMS:
        with (INPUTS / "scores" / f"{s}.tsv").open(newline="") as f:
            m = {r["utt"]: float(r["score"]) for r in csv.DictReader(f, delimiter="\t")}
        scores[s] = np.array([m[u] for u in utts])
    return labels, scores


def arm(labels, orders, law: str, seed: int):
    rng = np.random.default_rng(seed)
    n = len(labels)
    bona, spoof = np.flatnonzero(labels == 1), np.flatnonzero(labels == 0)
    reps = np.empty((B, len(SYSTEMS)))
    for b in range(B):
        if law == "pooled":
            w = np.bincount(rng.integers(0, n, size=n), minlength=n).astype(np.float64)
        else:
            w = np.zeros(n)
            w[bona] = np.bincount(rng.integers(0, len(bona), len(bona)), minlength=len(bona))
            w[spoof] = np.bincount(rng.integers(0, len(spoof), len(spoof)), minlength=len(spoof))
        reps[b] = [100.0 * weighted_eer(orders[s], labels, w) for s in SYSTEMS]
    return reps


def summarize(reps, point):
    pairs = [(i, j) for i in range(len(SYSTEMS)) for j in range(i + 1, len(SYSTEMS))]
    d = np.column_stack([reps[:, i] - reps[:, j] for i, j in pairs])
    sd = d.std(axis=0, ddof=1)
    q = float(np.quantile((np.abs(d - d.mean(axis=0)) / sd).max(axis=1), 0.95))
    out = {}
    for k, (i, j) in enumerate(pairs):
        hat = point[i] - point[j]
        lo, hi = hat - q * sd[k], hat + q * sd[k]
        out[f"{SYSTEMS[i]} vs {SYSTEMS[j]}"] = {"delta": float(hat), "band": [float(lo), float(hi)],
                                                "separated": bool(lo > 0 or hi < 0)}
    return {"q95": q, "pairs": out, "separated": sum(v["separated"] for v in out.values())}


def main():
    out_path = HERE / "RESULTS.json"
    if out_path.exists():
        raise SystemExit("RESULTS.json exists")
    t0 = time.time()
    labels, scores = load()
    orders = {s: np.argsort(scores[s], kind="mergesort") for s in SYSTEMS}
    unit = np.ones(len(labels))
    point = np.array([100.0 * weighted_eer(orders[s], labels, unit) for s in SYSTEMS])
    pooled = summarize(arm(labels, orders, "pooled", SEED_POOLED), point)
    ref = json.loads((EXP114 / "RESULTS.json").read_text())["arm_a_trial_iid"]
    worst = 0.0
    refpairs = ref["pairs"]
    for name, row in pooled["pairs"].items():
        r = refpairs[name]
        rb = r.get("simultaneous_max_t") or r.get("simultaneous") or r.get("band")
        worst = max(worst, abs(row["band"][0] - rb[0]), abs(row["band"][1] - rb[1]))
    if worst > 1e-5 or any(pooled["pairs"][k]["separated"] != refpairs[k]["simultaneous_excludes_zero"] for k in pooled["pairs"]):
        raise SystemExit(f"estimator gate failed: max band deviation {worst} or indicator mismatch")
    print(f"estimator gate passed: pooled arm reproduces EXP-114 arm A, max deviation {worst:.2e}", flush=True)
    strat = summarize(arm(labels, orders, "stratified", SEED_STRATIFIED), point)
    same = all(strat["pairs"][k]["separated"] == pooled["pairs"][k]["separated"] for k in pooled["pairs"])
    result = {
        "experiment": "EXP-118-m1-spoofceleb-trial-law", "B": B,
        "seeds": {"pooled": SEED_POOLED, "stratified": SEED_STRATIFIED},
        "prereg_sha256": sha(HERE / "PREREG.md"), "script_sha256": sha(Path(__file__).resolve()),
        "input_sha256": {"manifest": MANIFEST_SHA, **{f"scores/{s}": sha(INPUTS / "scores" / f"{s}.tsv") for s in SYSTEMS}},
        "producer_git_head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip(),
        "point_eer_percent": dict(zip(SYSTEMS, map(float, point))),
        "estimator_gate_max_band_deviation_points": worst,
        "pooled": pooled, "stratified": strat,
        "registered_reading": "exception_declared_and_numerically_immaterial" if (same and strat["separated"] == 6) else "exception_material",
        "wall_seconds": round(time.time() - t0, 1),
    }
    out_path.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("registered_reading", "wall_seconds")}), "pooled", pooled["separated"], "stratified", strat["separated"])
    for k in pooled["pairs"]:
        print(f"  {k:<28} pooled {pooled['pairs'][k]['band']} strat {strat['pairs'][k]['band']}")
    print(f"wrote {out_path} sha256={sha(out_path)}")


if __name__ == "__main__":
    main()
