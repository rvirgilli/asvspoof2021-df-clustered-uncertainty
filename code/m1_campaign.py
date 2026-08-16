"""EXP-101 cells 1-4: pairwise ΔEER inference on official score files.

21DF (eval phase): 8 systems, adjacent pairs of the sorted-EER ladder.
Schemes per pair (paired draws): naive i.i.d. percentile bootstrap; two-way
(speaker x attack) clustered percentile bootstrap; pigeonhole-corrected normal
(V = max(V_two - V_naive, V_naive)); two-way delete-one-cluster jackknife
normal; analytic i.i.d. z-test (Bengio-Mariethoz SE at the EER point,
Wang-Yamagishi practice); unclustered paired permutation test (per-trial
system-label swap). ITW: speaker-only, 4 systems.
Cell 2 diagnostics: variance components / ICC per (system, class, factor).
"""

import csv
import gzip
import json
import time
from math import erf, sqrt
import os
from pathlib import Path

import numpy as np

DATA = Path(os.environ.get("M1_DATA_ROOT",
                           Path.home() / "data/corpora/anti-spoofing"))
KEY = DATA / "DF-keys-full/keys/DF/CM/trial_metadata.txt"
OFF = DATA / "official-scores"
EXP001 = Path(os.environ.get(
    "M1_EXP001_SCORES",
    Path.home() / "projects/academic/icassp2027/experiments/EXP-001-scoring-campaign/scores"))
ITW_META = DATA / "release_in_the_wild/meta.csv"

DF_SCORES = {
    "XLSR-Mamba": OFF / "xlsr-mamba/Bmamba3_LA_WCE_1e-06_ES144_NE12.txt",
    "XLS-R+SLS": OFF / "xlsr-sls/scores_DF.txt",
    "XLSR-Conformer": OFF / "xlsr-conformer-rosello/Scores_Best_DF_Fixed_size_train.txt",
    "SSL-AASIST": Path(os.environ.get(
        "M1_SSL_AASIST_SCORES",
        Path.home() / "projects/academic/SSL_Anti-spoofing/Scores/DF/Scores_DF.txt")),
    "RawNet2": DATA / "DF-keys-full/keys/DF/CM/RawNet2/score.txt",
    "LFCC-LCNN": DATA / "DF-keys-full/keys/DF/CM/LFCC-LCNN/score.txt",
    "LFCC-GMM": DATA / "DF-keys-full/keys/DF/CM/LFCC-GMM/score.txt",
    "CQCC-GMM": DATA / "DF-keys-full/keys/DF/CM/CQCC-GMM/score.txt",
}
B = 1000
NPERM = 1000
SEED = 20260813
Z95 = 1.959963984540054


def weighted_eer(sort_idx, labels, weights):
    l = labels[sort_idx]
    w = weights[sort_idx].astype(np.float64)
    cb = np.cumsum(w * l)
    cs = np.cumsum(w * (1 - l))
    frr = cb / cb[-1]
    far = 1.0 - cs / cs[-1]
    i = np.argmin(np.abs(frr - far))
    return float((frr[i] + far[i]) / 2)


def plain_eer(scores, labels):
    return weighted_eer(np.argsort(scores), labels, np.ones(len(scores)))


def variance_components(s, labels, spk_idx, att_idx):
    """Per-class speaker/attack variance shares (ICC-style diagnostics)."""
    out = {}
    for cls, name in ((1, "bona"), (0, "spoof")):
        m = labels == cls
        sub = s[m]
        spk = np.unique(spk_idx[m], return_inverse=True)[1]
        tot = float(sub.var())
        spk_eff = np.bincount(spk, weights=sub - sub.mean()) / np.bincount(spk)
        entry = {"var_total": round(tot, 3), "icc_spk": round(float(spk_eff.var()) / tot, 3)}
        if cls == 0 and att_idx is not None:
            att = np.unique(att_idx[m], return_inverse=True)[1]
            att_eff = np.bincount(att, weights=sub - sub.mean()) / np.bincount(att)
            entry["icc_att"] = round(float(att_eff.var()) / tot, 3)
        out[name] = entry
    return out


def analytic_z(sa, sb, labels):
    """Unpaired i.i.d. z-test on EER difference (Bengio-Mariethoz SE)."""
    nb, ns = int(labels.sum()), int((1 - labels).sum())

    def se(scores):
        e = plain_eer(scores, labels)
        return sqrt(e * (1 - e) / ns + e * (1 - e) / nb) / 2

    d = plain_eer(sa, labels) - plain_eer(sb, labels)
    z = d / sqrt(se(sa) ** 2 + se(sb) ** 2)
    p = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return round(float(z), 2), round(float(p), 4)


def perm_test(rng, sa, sb, labels):
    d_obs = abs(plain_eer(sa, labels) - plain_eer(sb, labels))
    n = len(sa)
    hits = 0
    for _ in range(NPERM):
        swap = rng.random(n) < 0.5
        a = np.where(swap, sb, sa)
        b = np.where(swap, sa, sb)
        if abs(plain_eer(a, labels) - plain_eer(b, labels)) >= d_obs:
            hits += 1
    return round((hits + 1) / (NPERM + 1), 4)


def run_dataset(tag, scores, labels, spk_idx, att_idx, rng):
    """Full scheme battery; att_idx None => speaker-only clustering."""
    names = sorted(scores, key=lambda m: plain_eer(scores[m], labels))
    orders = {m: np.argsort(scores[m]) for m in names}
    eers = {m: round(100 * plain_eer(scores[m], labels), 3) for m in names}
    print(f"[{tag}] pooled EERs: {eers}", flush=True)
    n = len(labels)
    n_spk = spk_idx.max() + 1
    is_spoof = labels == 0
    has_att = att_idx is not None
    if has_att:
        spoof_atts = np.unique(att_idx[is_spoof])
        n_att = att_idx.max() + 1

    t0 = time.time()
    boot = {"naive": {m: np.empty(B) for m in names},
            "clustered": {m: np.empty(B) for m in names}}
    for scheme in boot:
        for i in range(B):
            if scheme == "naive":
                w = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64)
            else:
                cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
                w = cs[spk_idx].astype(np.float64)
                if has_att:
                    drawn = rng.choice(spoof_atts, size=len(spoof_atts), replace=True)
                    ca = np.bincount(drawn, minlength=n_att)
                    w[is_spoof] *= ca[att_idx[is_spoof]]
            for m in names:
                boot[scheme][m][i] = weighted_eer(orders[m], labels, w)
        print(f"[{tag}] {scheme} bootstrap done ({time.time()-t0:.0f}s)", flush=True)

    jack_spk = {m: np.empty(n_spk) for m in names}
    for k in range(n_spk):
        w = np.ones(n)
        w[spk_idx == k] = 0.0
        for m in names:
            jack_spk[m][k] = weighted_eer(orders[m], labels, w)
    if has_att:
        jack_att = {m: np.empty(len(spoof_atts)) for m in names}
        for j, k in enumerate(spoof_atts):
            w = np.ones(n)
            w[is_spoof & (att_idx == k)] = 0.0
            for m in names:
                jack_att[m][j] = weighted_eer(orders[m], labels, w)
    print(f"[{tag}] jackknife done ({time.time()-t0:.0f}s)", flush=True)

    pairs = {}
    for a, b in zip(names, names[1:]):
        d_hat = 100 * (plain_eer(scores[a], labels) - plain_eer(scores[b], labels))
        deltas = {s: 100 * (boot[s][a] - boot[s][b]) for s in boot}
        v_naive = float(np.var(deltas["naive"]))
        v_two = float(np.var(deltas["clustered"]))
        cis = {
            "naive": [float(np.percentile(deltas["naive"], 2.5)),
                      float(np.percentile(deltas["naive"], 97.5))],
            "twoway": [float(np.percentile(deltas["clustered"], 2.5)),
                       float(np.percentile(deltas["clustered"], 97.5))],
        }
        v_pig = max(v_two - v_naive, v_naive)
        cis["pigeonhole"] = [d_hat - Z95 * sqrt(v_pig), d_hat + Z95 * sqrt(v_pig)]
        js = 100 * (jack_spk[a] - jack_spk[b])
        v_spk = (n_spk - 1) / n_spk * float(np.sum((js - js.mean()) ** 2))
        if has_att:
            ja = 100 * (jack_att[a] - jack_att[b])
            na = len(ja)
            v_att = (na - 1) / na * float(np.sum((ja - ja.mean()) ** 2))
            v_jack = max(v_spk + v_att - v_naive, max(v_spk, v_att))
        else:
            v_jack = v_spk
        cis["jackknife"] = [d_hat - Z95 * sqrt(v_jack), d_hat + Z95 * sqrt(v_jack)]

        z, pz = analytic_z(scores[a], scores[b], labels)
        pperm = perm_test(rng, scores[a], scores[b], labels)
        consensus = all(not (lo <= 0 <= hi) for lo, hi in
                        (cis["twoway"], cis["pigeonhole"], cis["jackknife"]))
        pairs[f"{a} vs {b}"] = {
            "delta_eer_pts": round(d_hat, 3),
            **{k: [round(x, 3) for x in v] for k, v in cis.items()},
            "width_ratio_twoway": round((cis["twoway"][1] - cis["twoway"][0]) /
                                        (cis["naive"][1] - cis["naive"][0]), 2),
            "ztest": {"z": z, "p": pz},
            "perm_p": pperm,
            "fixed_set_resolved": bool(not (cis["naive"][0] <= 0 <= cis["naive"][1])),
            "generalization_resolved_consensus": bool(consensus),
        }
        print(f"[{tag}] {a} vs {b}: d={d_hat:.3f} ratio={pairs[f'{a} vs {b}']['width_ratio_twoway']} "
              f"gen_resolved={consensus}", flush=True)
    return {"pooled_eer": eers, "pairs": pairs}


def main():
    rng = np.random.default_rng(SEED)
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
    print(f"21DF eval: {len(utts)} trials, {labels.sum()} bona, "
          f"{spk_idx.max()+1} spk, {len(np.unique(att_idx[labels==0]))} attacks", flush=True)
    results["21df"] = run_dataset("21df", scores, labels, spk_idx, att_idx, rng)
    results["21df"]["variance_components"] = {
        m: variance_components(scores[m], labels, spk_idx, att_idx) for m in scores}

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
    print(f"ITW: {len(common)} trials, {labels_i.sum()} bona, {spk_i.max()+1} speakers", flush=True)
    results["itw"] = run_dataset("itw", sc_i, labels_i, spk_i, None, rng)
    results["itw"]["variance_components"] = {
        m: variance_components(sc_i[m], labels_i, spk_i, None) for m in sc_i}

    out = Path(__file__).parent / "results_pairs.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
