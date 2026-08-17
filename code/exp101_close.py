"""EXP-101 closing analyses: Holm-adjusted verdicts + empirical subsample check.

(a) Holm-Bonferroni over adjacent-pair families (7 on 21DF, 3 on ITW), from
    two-way clustered bootstrap percentile p-values, B=1000, seed 20260813
    (fresh rng stream; same methodology/draw budget as cell 3 per the
    pre-committed addendum policy).
(b) Cell-6 empirical cross-check: subsample real attacks (A in {10, 40, 110})
    from the RawNet2/LFCC-LCNN official scores, two-way CI width vs the
    calibrated simulator's mean width at matching grid points.
"""

import csv
import gzip
import json
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, EXP001, ITW_META, KEY, OFF, weighted_eer

B = 1000
SEED = 20260813


def boot_deltas(rng, scores, labels, spk_idx, att_idx, names):
    n, n_spk = len(labels), spk_idx.max() + 1
    is_spoof = labels == 0
    has_att = att_idx is not None
    orders = {m: np.argsort(scores[m]) for m in names}
    if has_att:
        spoof_atts = np.unique(att_idx[is_spoof])
        n_att = att_idx.max() + 1
    boot = {m: np.empty(B) for m in names}
    for i in range(B):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        w = cs[spk_idx].astype(np.float64)
        if has_att:
            drawn = rng.choice(spoof_atts, size=len(spoof_atts), replace=True)
            ca = np.bincount(drawn, minlength=n_att)
            w[is_spoof] *= ca[att_idx[is_spoof]]
        for m in names:
            boot[m][i] = weighted_eer(orders[m], labels, w)
    return boot


def holm(pairs_p):
    order = sorted(pairs_p, key=pairs_p.get)
    m = len(order)
    adj, running = {}, 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * pairs_p[k]))
        adj[k] = round(running, 4)
    return adj


def family(tag, scores, labels, spk_idx, att_idx):
    names = sorted(scores, key=lambda m: weighted_eer(
        np.argsort(scores[m]), labels, np.ones(len(labels))))
    rng = np.random.default_rng(SEED)
    boot = boot_deltas(rng, scores, labels, spk_idx, att_idx, names)
    out = {}
    for a, b in zip(names, names[1:]):
        d = 100 * (boot[a] - boot[b])
        p_lo = float(np.mean(d <= 0))
        p = min(1.0, 2 * min(p_lo, 1 - p_lo) + 1 / B)
        out[f"{a} vs {b}"] = round(p, 4)
    adj = holm(out)
    print(f"[{tag}] raw p: {out}")
    print(f"[{tag}] holm: {adj}", flush=True)
    return {"raw_p": out, "holm_adjusted": adj,
            "unresolved_after_holm": [k for k, v in adj.items() if v > 0.05]}


def subsample_check():
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk_idx = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    att_names, att_idx = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)
    scores = {}
    for m in ("RawNet2", "LFCC-LCNN"):
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        scores[m] = np.array([float(d[u]) for u in utts])
    spoof_atts = np.unique(att_idx[labels == 0])
    rng = np.random.default_rng(SEED)
    out = {}
    for A in (10, 40, 110):
        widths = []
        for rep in range(20):
            keep_atts = rng.choice(spoof_atts, A, replace=False) if A < len(spoof_atts) else spoof_atts
            mask = (labels == 1) | np.isin(att_idx, keep_atts)
            sub = np.where(mask)[0]
            l, s_i = labels[sub], np.unique(spk_idx[sub], return_inverse=True)[1]
            a_i = np.unique(att_idx[sub], return_inverse=True)[1]
            sc = {m: scores[m][sub] for m in scores}
            boot = boot_deltas(np.random.default_rng(SEED + rep), sc, l, s_i,
                               a_i, list(sc))
            d = 100 * (boot["RawNet2"] - boot["LFCC-LCNN"])
            d = d[np.isfinite(d)]  # degenerate crossed resamples (all-zero spoof weight) occur at few clusters
            widths.append(float(np.percentile(d, 97.5) - np.percentile(d, 2.5)))
        out[f"A{A}"] = {"mean_width_real_subsample": round(float(np.mean(widths)), 3),
                        "n_reps": len(widths)}
        print(f"subsample A={A}: width {out[f'A{A}']}", flush=True)
    return out


def main():
    results = {}
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk_idx = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    att_idx = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    scores = {}
    for m, path in DF_SCORES.items():
        d = dict(l.split()[:2] for l in path.read_text().splitlines())
        scores[m] = np.array([float(d[u]) for u in utts])
    results["holm_21df"] = family("21df", scores, labels, spk_idx, att_idx)

    spk = {}
    with open(ITW_META) as f:
        for r in csv.DictReader(f):
            spk[Path(r["file"]).stem] = r["speaker"]
    itw_scores = {}
    for m, path in (("XLSR-Mamba", OFF / "xlsr-mamba/Bmamba5_In-the-Wild_WCE_1e-06_ES144_NE12.txt"),
                    ("XLS-R+SLS", OFF / "xlsr-sls/scores_Wild.txt")):
        itw_scores[m] = {Path(k).stem: v for k, v in
                         (l.split()[:2] for l in path.read_text().splitlines())}
    for m, tag in (("SSL-AASIST", "ssl"), ("AASIST", "aasist")):
        with gzip.open(EXP001 / f"{tag}_itw.csv.gz", "rt") as f:
            itw_scores[m] = {r["utt_id"]: r["score"] for r in csv.DictReader(f)}
    common = sorted(set.intersection(*(set(v) for v in itw_scores.values())) & set(spk))
    with gzip.open(EXP001 / "ssl_itw.csv.gz", "rt") as f:
        itw_label = {r["utt_id"]: r["label"] for r in csv.DictReader(f)}
    labels_i = np.array([1 if itw_label[u] == "bonafide" else 0 for u in common])
    spk_i = np.unique([spk[u] for u in common], return_inverse=True)[1]
    sc_i = {m: np.array([float(itw_scores[m][u]) for u in common]) for m in itw_scores}
    results["holm_itw"] = family("itw", sc_i, labels_i, spk_i, None)

    results["subsample_check"] = subsample_check()

    out = Path(__file__).parent.parent / "derived" / "results_close.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
