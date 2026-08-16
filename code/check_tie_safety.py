"""Is the EER sweep tie-safe? Compare position-wise sweep against a tie-aware one.

The released estimator sweeps sorted POSITIONS and takes argmin|FRR-FAR|. Where
scores tie, positions inside a tie block are not realizable thresholds: a real
decision rule must accept or reject all trials sharing a score. This evaluates
FRR/FAR only at distinct-score boundaries and reports the difference.
"""
import numpy as np
from m1_campaign import DF_SCORES, KEY, weighted_eer

u2 = {}
for l in KEY.read_text().splitlines():
    p = l.split()
    if p[7] == "eval":
        u2[p[1]] = (p[0], p[4], p[5])
utts = sorted(u2)
lab = np.array([1 if u2[u][2] == "bonafide" else 0 for u in utts])
w = np.ones(len(lab))

def tie_aware_eer(scores, labels, weights):
    o = np.argsort(scores, kind="mergesort")
    s, l, ww = scores[o], labels[o], weights[o].astype(np.float64)
    cb = np.cumsum(ww * l)
    cs = np.cumsum(ww * (1 - l))
    frr = cb / cb[-1]
    far = 1.0 - cs / cs[-1]
    # keep only the LAST position of each run of equal scores -> realizable thresholds
    last = np.r_[s[1:] != s[:-1], True]
    frr, far = frr[last], far[last]
    i = np.argmin(np.abs(frr - far))
    return float((frr[i] + far[i]) / 2)

print("tie prevalence (trials sitting in a tie group, i.e. sharing a score):")
for m in ["XLSR-Mamba", "XLS-R+SLS"]:
    d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
    sc = np.array([float(d[u]) for u in utts])
    _, cnt = np.unique(sc, return_counts=True)
    print("  %-14s %.1f%% in a tie group, largest block %d"
          % (m, 100 * cnt[cnt > 1].sum() / len(sc), cnt.max()))

print()
print("%-18s %12s %12s %10s" % ("system", "released", "tie-aware", "diff(pts)"))
worst = 0.0
vals = {}
for m in ["XLSR-Mamba","XLS-R+SLS","XLSR-Conformer","SSL-AASIST",
          "RawNet2","LFCC-LCNN","LFCC-GMM","CQCC-GMM"]:
    d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
    sc = np.array([float(d[u]) for u in utts])
    a = 100 * weighted_eer(np.argsort(sc), lab, w)
    b = 100 * tie_aware_eer(sc, lab, w)
    vals[m] = (a, b)
    worst = max(worst, abs(a - b))
    print("%-18s %12.4f %12.4f %10.4f" % (m, a, b, a - b))
print("\nmax |diff| = %.4f EER points" % worst)
assert worst < 0.001, "EER sweep is not tie-safe on these score files"

print("\npaired deltas (the quantity the paper actually reports):")
names = list(vals)
mx = 0.0
for i, x in enumerate(names):
    for y in names[i+1:]:
        da = vals[x][0] - vals[x][1]
        dd = (vals[x][0]-vals[y][0]) - (vals[x][1]-vals[y][1])
        mx = max(mx, abs(dd))
print("  max |change in any pairwise delta| = %.4f EER points" % mx)
assert mx < 0.001, "pairwise deltas move under tie-aware thresholding"
print("\nPASS: tie handling does not affect any reported quantity.")
