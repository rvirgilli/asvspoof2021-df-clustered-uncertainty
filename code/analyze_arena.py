"""EXP-104: provenance-stratified Speech DF Arena replication.

All eleven Arena re-scores are analysed as one separate provenance layer. The
high-provenance author/organizer pool is never mixed into the rank family. The
bootstrap is resumable at the replicate level and uses deterministic per-index
seeds, so interruption and resumption are bit-for-bit equivalent to one run.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from numpy.lib.format import open_memmap


B_FROZEN = 5000
SEED = 20260823
Z95 = 1.959963984540054
HERE = Path(__file__).resolve().parent
DERIVED = HERE.parent / "derived"
DATA = Path(os.environ.get("M1_DATA_ROOT",
                           HERE.parent / "inputs/anti-spoofing"))
KEY = DATA / "DF-keys-full/keys/DF/CM/trial_metadata.txt"
ARENA = Path(os.environ.get("M1_ARENA_SCORES",
                            DATA / "speech-df-arena/asvspoof2021-df"))
RUN_ROOT = Path(os.environ.get("M1_ARENA_RUN_ROOT",
                               HERE.parent / "regenerated/EXP-104-m1-arena-replication"))

DISPLAY = {
    "aasist": "AASIST-Arena",
    "hubert_ecapa": "HuBERT-ECAPA-Arena",
    "rawgat_st": "RawGAT-ST-Arena",
    "rawnet_2": "RawNet2-Arena",
    "resemble_ai": "Resemble-AI-Arena",
    "tcm_add": "TCM-ADD-Arena",
    "wav2vec2_ecapa": "Wav2Vec2-ECAPA-Arena",
    "wavlm_ecapa": "WavLM-ECAPA-Arena",
    "whisper_mesonet": "Whisper-MesoNet-Arena",
    "xlsr_mamba": "XLSR-Mamba-Arena",
    "xlsr_sls": "XLS-R+SLS-Arena",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def weighted_eer(order, labels, weights):
    lab = labels[order]
    w = weights[order].astype(np.float64, copy=False)
    cb = np.cumsum(w * lab)
    cs = np.cumsum(w * (1 - lab))
    if cb[-1] <= 0 or cs[-1] <= 0:
        raise ValueError("bootstrap replicate lost one class")
    frr = cb / cb[-1]
    far = 1.0 - cs / cs[-1]
    k = int(np.argmin(np.abs(frr - far)))
    return float((frr[k] + far[k]) / 2)


def load_key():
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
    return utts, labels, spk_names, spk_idx, att_names, att_idx


def score_id(raw):
    return Path(raw).stem


def load_scores(utts):
    expected = set(utts)
    scores, paths, digests = {}, {}, {}
    for slug, name in sorted(DISPLAY.items()):
        path = ARENA / slug / "asvspoof_2021_df.txt"
        if not path.exists():
            raise FileNotFoundError(path)
        vals = {}
        duplicate = None
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                p = line.split()
                if len(p) < 2:
                    raise ValueError(f"{path}:{lineno}: expected path and score")
                utt = score_id(p[0])
                if utt in vals:
                    duplicate = utt
                    break
                vals[utt] = float(p[1])
        if duplicate:
            raise ValueError(f"{path}: duplicate trial {duplicate}")
        got = set(vals)
        if got != expected:
            raise ValueError(f"{path}: trial intersection mismatch: "
                             f"missing={len(expected-got)} extra={len(got-expected)}")
        scores[name] = np.array([vals[u] for u in utts], dtype=np.float64)
        paths[name] = path
        digests[name] = sha256(path)

    vector_hash = {m: hashlib.sha256(v.tobytes()).hexdigest() for m, v in scores.items()}
    by_hash = {}
    for m, h in vector_hash.items():
        by_hash.setdefault(h, []).append(m)
    aliases = [v for v in by_hash.values() if len(v) > 1]
    if aliases:
        retained = {group[0] for group in aliases}
        dropped = {m for group in aliases for m in group[1:]}
        scores = {m: v for m, v in scores.items() if m not in dropped}
    else:
        retained, dropped = set(), set()
    return scores, paths, digests, vector_hash, aliases, sorted(retained), sorted(dropped)


def provenance(paths, digests, vector_hash, aliases, retained, dropped):
    return {
        "key": {"path": str(KEY), "sha256": sha256(KEY)},
        "script_sha256": sha256(Path(__file__)),
        "score_files": {m: {"path": str(paths[m]), "sha256": digests[m],
                             "score_vector_sha256": vector_hash[m]}
                        for m in sorted(paths)},
        "exact_duplicate_groups": aliases,
        "aliases_retained": retained,
        "aliases_dropped": dropped,
    }


def prepare_memmap(scheme, b, names, provenance_digest):
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    path = RUN_ROOT / f"eers_{scheme}_B{b}.npy"
    sidecar = path.with_suffix(".json")
    contract = {"scheme": scheme, "B": b, "seed": SEED, "systems": names,
                "provenance_sha256": provenance_digest}
    if path.exists() or sidecar.exists():
        if not (path.exists() and sidecar.exists()):
            raise RuntimeError(f"incomplete resumability state for {scheme}")
        if json.loads(sidecar.read_text()) != contract:
            raise RuntimeError(f"refusing to resume {scheme} across a changed contract")
        out = np.load(path, mmap_mode="r+")
        if out.shape != (b, len(names)):
            raise RuntimeError(f"wrong memmap shape for {scheme}: {out.shape}")
    else:
        out = open_memmap(path, mode="w+", dtype=np.float64, shape=(b, len(names)))
        out[:] = np.nan
        out.flush()
        sidecar.write_text(json.dumps(contract, indent=2) + "\n")
    return out


def bootstrap(scheme, b, scores, labels, spk_idx, att_idx, provenance_digest):
    names = sorted(scores)
    orders = {m: np.argsort(scores[m]) for m in names}
    out = prepare_memmap(scheme, b, names, provenance_digest)
    n = len(labels)
    n_spk = int(spk_idx.max()) + 1
    is_spoof = labels == 0
    spoof_atts = np.unique(att_idx[is_spoof])
    n_att = int(att_idx.max()) + 1
    pending = np.flatnonzero(np.isnan(out).any(axis=1))
    print(f"{scheme}: {len(pending)}/{b} replicates pending", flush=True)
    for done, i in enumerate(pending, 1):
        rng = np.random.default_rng(np.random.SeedSequence(
            [SEED, 0 if scheme == "iid" else 1, int(i)]))
        if scheme == "iid":
            w = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64)
        elif scheme == "clustered":
            cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
            ca = np.bincount(rng.choice(spoof_atts, len(spoof_atts), replace=True),
                             minlength=n_att)
            w = cs[spk_idx].astype(np.float64)
            w[is_spoof] *= ca[att_idx[is_spoof]]
        else:
            raise ValueError(scheme)
        for j, m in enumerate(names):
            out[i, j] = 100 * weighted_eer(orders[m], labels, w)
        if done <= 3 or done % 25 == 0 or done == len(pending):
            out.flush()
            print(f"{scheme}: completed {done}/{len(pending)} pending "
                  f"(absolute replicate {i+1}/{b})", flush=True)
    return np.asarray(out), names


def scheme_analysis(reps, names, point):
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    deltas = np.column_stack([reps[:, names.index(a)] - reps[:, names.index(b)]
                              for a, b in pairs])
    hat = np.array([point[a] - point[b] for a, b in pairs])
    sd = deltas.std(axis=0, ddof=1)
    centred = np.abs(deltas - deltas.mean(axis=0)) / np.maximum(sd, 1e-12)
    q = float(np.percentile(centred.max(axis=1), 95))
    out = {}
    for j, (a, b) in enumerate(pairs):
        lo, hi = np.percentile(deltas[:, j], [2.5, 97.5])
        slo, shi = hat[j] - q * sd[j], hat[j] + q * sd[j]
        out[f"{a} vs {b}"] = {
            "delta_eer_pts": round(float(hat[j]), 6),
            "bootstrap_sd": round(float(sd[j]), 6),
            "ci95_pointwise": [round(float(lo), 6), round(float(hi), 6)],
            "ci95_simultaneous": [round(float(slo), 6), round(float(shi), 6)],
            "resolved_pointwise": bool(not (lo <= 0 <= hi)),
            "resolved_simultaneous": bool(not (slo <= 0 <= shi)),
            "mde95_simultaneous_pts": round(float(q * sd[j]), 6),
        }
    better, worse = {m: 0 for m in names}, {m: 0 for m in names}
    for key, v in out.items():
        if not v["resolved_simultaneous"]:
            continue
        a, b = key.split(" vs ")
        best, worst = (a, b) if v["delta_eer_pts"] < 0 else (b, a)
        better[worst] += 1
        worse[best] += 1
    ranks = {m: [1 + better[m], len(names) - worse[m]] for m in names}
    return {"supt_critical_value": round(q, 6), "pairs": out,
            "rank_ci95_simultaneous": ranks,
            "n_resolved_pointwise": sum(v["resolved_pointwise"] for v in out.values()),
            "n_resolved_simultaneous": sum(v["resolved_simultaneous"] for v in out.values())}


def cross_layer_sensitivity(utts, labels, arena_scores):
    # These comparisons diagnose implementation/provenance sensitivity only and
    # never enter the Arena rank family.
    from m1_campaign import DF_SCORES  # pylint: disable=import-outside-toplevel

    mapping = {"XLSR-Mamba-Arena": "XLSR-Mamba",
               "XLS-R+SLS-Arena": "XLS-R+SLS",
               "RawNet2-Arena": "RawNet2"}
    out = {}
    ones = np.ones(len(labels))
    for arena_name, primary_name in mapping.items():
        raw = dict(line.split()[:2] for line in DF_SCORES[primary_name].read_text().splitlines())
        primary = np.array([float(raw[u]) for u in utts])
        a, p = arena_scores[arena_name], primary
        out[f"{arena_name} vs {primary_name}"] = {
            "arena_eer": round(100 * weighted_eer(np.argsort(a), labels, ones), 6),
            "primary_eer": round(100 * weighted_eer(np.argsort(p), labels, ones), 6),
            "score_pearson": round(float(np.corrcoef(a, p)[0, 1]), 6),
            "note": "implementation/provenance sensitivity; excluded from rank family",
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--b", type=int, default=B_FROZEN)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--output", type=Path, default=DERIVED / "results_arena.json")
    args = ap.parse_args()
    if args.output == DERIVED / "results_arena.json" and args.b != B_FROZEN:
        raise SystemExit("the registered result requires B=5000; use another --output for smoke runs")

    utts, labels, spk_names, spk_idx, att_names, att_idx = load_key()
    scores, paths, digests, vector_hash, aliases, retained, dropped = load_scores(utts)
    prov = provenance(paths, digests, vector_hash, aliases, retained, dropped)
    prov_digest = hashlib.sha256(json.dumps(prov, sort_keys=True).encode()).hexdigest()
    ones = np.ones(len(labels))
    point = {m: 100 * weighted_eer(np.argsort(v), labels, ones) for m, v in scores.items()}
    print(f"loaded {len(scores)} Arena systems on {len(utts):,} identical trials; "
          f"{len(spk_names)} speakers, {len(np.unique(att_idx[labels == 0]))} spoof attacks",
          flush=True)
    print("pooled EERs (seen during the pre-freeze audit):", flush=True)
    for m in sorted(point, key=point.get):
        print(f"  {m:<26} {point[m]:8.4f}", flush=True)
    if args.check_only:
        return

    schemes = {}
    for scheme in ("iid", "clustered"):
        reps, names = bootstrap(scheme, args.b, scores, labels, spk_idx, att_idx,
                                prov_digest)
        schemes[scheme] = scheme_analysis(reps, names, point)
    names = sorted(scores, key=point.get)
    adjacent = [f"{a} vs {b}" for a, b in zip(names, names[1:])]
    ratios = {}
    flips = []
    for key in schemes["clustered"]["pairs"]:
        vc = schemes["clustered"]["pairs"][key]
        vi = schemes["iid"]["pairs"][key]
        ratios[key] = vc["bootstrap_sd"] / vi["bootstrap_sd"]
        if key in adjacent and vi["resolved_simultaneous"] and not vc["resolved_simultaneous"]:
            flips.append(key)
    result = {
        "experiment": "EXP-104",
        "B": args.b,
        "seed": SEED,
        "provenance": prov,
        "n_trials": len(utts),
        "n_speakers": len(spk_names),
        "n_spoof_attacks": int(len(np.unique(att_idx[labels == 0]))),
        "systems_sorted_by_eer": names,
        "pooled_eer": {m: round(point[m], 6) for m in names},
        "schemes": schemes,
        "adjacent_edges": adjacent,
        "adjacent_iid_resolved_clustered_unresolved": flips,
        "width_ratio_clustered_over_iid": {k: round(v, 6) for k, v in ratios.items()},
        "median_width_ratio": round(float(np.median(list(ratios.values()))), 6),
        "cross_layer_sensitivity": cross_layer_sensitivity(utts, labels, scores),
    }
    c1, c2 = bool(flips), result["median_width_ratio"] >= 3
    result["reading"] = ("confirmed" if c1 and c2 else
                         "partially_confirmed" if c1 or c2 else "refuted")
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {args.output}: {result['reading']}; adjacent flips={len(flips)}, "
          f"median width ratio={result['median_width_ratio']:.2f}", flush=True)


if __name__ == "__main__":
    main()
