"""EXP-101 correction: proper intra-class correlations for the cluster diagnostic.

The released `variance_components` (m1_campaign.py) divided the *unweighted*
variance of group means by the trial-level total variance. That is not an ICC:
it ignores group sizes and its numerator carries within-group noise, which is
how the artifact came to contain icc_spk = 1.099 (structurally impossible).

Replaced here by the textbook one-way random-effects ANOVA estimator
(Searle, Casella & McCulloch 1992):

    SSB = sum_i n_i (ybar_i - ybar)^2         MSB = SSB / (k - 1)
    SSW = sum_i sum_j (y_ij - ybar_i)^2       MSW = SSW / (N - k)
    n0  = (N - sum_i n_i^2 / N) / (k - 1)
    sigma2_b = (MSB - MSW) / n0               ICC = sigma2_b / (sigma2_b + MSW)

Negative variance estimates (possible when the true component is near zero) are
reported as 0.0 with the raw value retained. Computed per factor on the class
that carries it: attack ICC on spoof trials only (bona fide trials have no
attack label), speaker ICC per class.
"""

import csv
import gzip
import json
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, EXP001, ITW_META, KEY, OFF


def icc_oneway(y, group):
    """One-way random-effects ICC with the ANOVA (Searle) estimator."""
    g = np.unique(group, return_inverse=True)[1]
    k = g.max() + 1
    N = len(y)
    if k < 2 or N <= k:
        return None
    n = np.bincount(g)
    means = np.bincount(g, weights=y) / n
    grand = y.mean()
    ssb = float(np.sum(n * (means - grand) ** 2))
    ssw = float(np.sum((y - means[g]) ** 2))
    msb, msw = ssb / (k - 1), ssw / (N - k)
    n0 = (N - np.sum(n.astype(np.float64) ** 2) / N) / (k - 1)
    sigma2_b = (msb - msw) / n0
    icc = sigma2_b / (sigma2_b + msw)
    return {"k_groups": int(k), "n_trials": int(N), "n0": round(float(n0), 2),
            "sigma2_between": round(float(sigma2_b), 4), "sigma2_within": round(float(msw), 4),
            "icc": round(float(max(icc, 0.0)), 4),
            "icc_raw": round(float(icc), 4)}


def main():
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk = np.array([utt2meta[u][0] for u in utts])
    att = np.array([utt2meta[u][1] for u in utts])
    spoof = labels == 0

    results = {"estimator": "one-way random-effects ANOVA ICC (Searle et al. 1992)",
               "supersedes": "m1_campaign.variance_components in results_pairs.json "
                             "(unweighted group-mean variance / total variance; not an ICC)",
               "21df": {}}
    for m, path in DF_SCORES.items():
        d = dict(l.split()[:2] for l in path.read_text().splitlines())
        s = np.array([float(d[u]) for u in utts])
        results["21df"][m] = {
            "attack_icc_spoof": icc_oneway(s[spoof], att[spoof]),
            "speaker_icc_spoof": icc_oneway(s[spoof], spk[spoof]),
            "speaker_icc_bona": icc_oneway(s[~spoof], spk[~spoof]),
        }
        r = results["21df"][m]
        print(f"{m:<16} attack-ICC(spoof) {r['attack_icc_spoof']['icc']:.3f}  "
              f"speaker-ICC(spoof) {r['speaker_icc_spoof']['icc']:.3f}  "
              f"speaker-ICC(bona) {r['speaker_icc_bona']['icc']:.3f}", flush=True)

    spk_itw = {}
    with open(ITW_META) as f:
        for r in csv.DictReader(f):
            spk_itw[Path(r["file"]).stem] = r["speaker"]
    raw = {}
    for m, path in (("XLSR-Mamba", OFF / "xlsr-mamba/Bmamba5_In-the-Wild_WCE_1e-06_ES144_NE12.txt"),
                    ("XLS-R+SLS", OFF / "xlsr-sls/scores_Wild.txt")):
        raw[m] = {Path(k).stem: v for k, v in
                  (l.split()[:2] for l in path.read_text().splitlines())}
    for m, tag in (("SSL-AASIST", "ssl"), ("AASIST", "aasist")):
        with gzip.open(EXP001 / f"{tag}_itw.csv.gz", "rt") as f:
            raw[m] = {r["utt_id"]: r["score"] for r in csv.DictReader(f)}
    common = sorted(set.intersection(*(set(v) for v in raw.values())) & set(spk_itw))
    with gzip.open(EXP001 / "ssl_itw.csv.gz", "rt") as f:
        lab = {r["utt_id"]: r["label"] for r in csv.DictReader(f)}
    y_lab = np.array([1 if lab[u] == "bonafide" else 0 for u in common])
    g = np.array([spk_itw[u] for u in common])
    results["itw"] = {}
    for m in raw:
        s = np.array([float(raw[m][u]) for u in common])
        results["itw"][m] = {
            "speaker_icc_spoof": icc_oneway(s[y_lab == 0], g[y_lab == 0]),
            "speaker_icc_bona": icc_oneway(s[y_lab == 1], g[y_lab == 1]),
        }
        r = results["itw"][m]
        print(f"ITW {m:<12} speaker-ICC(spoof) {r['speaker_icc_spoof']['icc']:.3f}  "
              f"(bona) {r['speaker_icc_bona']['icc']:.3f}", flush=True)

    att_iccs = [v["attack_icc_spoof"]["icc"] for v in results["21df"].values()]
    ssl_era = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
    results["summary"] = {
        "attack_icc_all": [round(min(att_iccs), 3), round(max(att_iccs), 3)],
        "attack_icc_ssl_era": [round(min(results["21df"][m]["attack_icc_spoof"]["icc"] for m in ssl_era), 3),
                               round(max(results["21df"][m]["attack_icc_spoof"]["icc"] for m in ssl_era), 3)],
        "attack_icc_organizer_era": [round(min(results["21df"][m]["attack_icc_spoof"]["icc"]
                                               for m in results["21df"] if m not in ssl_era), 3),
                                     round(max(results["21df"][m]["attack_icc_spoof"]["icc"]
                                               for m in results["21df"] if m not in ssl_era), 3)],
    }
    print("summary:", results["summary"], flush=True)
    out = Path(__file__).parent / "results_icc.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
