"""EXP-101: sampling uncertainty of the RESOLUTION COUNTS.

"18 of 28 resolve", and the block counts 16/16, 2/6, 0/6, are counts of intervals
excluding zero. A count over a threshold looks like data but is a point estimate of
a step function, which is exactly where an unquantified interval hides -- the same
object that just cost the floor claim its "eight of ten". So we measure it.

Outer bootstrap over the sampling units the paper claims to generalise over:
resample speakers and attacks with replacement, recompute the paired Delta-EER and
its two-way delete-one-cluster jackknife SE (the second certified variant, chosen
here because it needs no inner bootstrap), and call a pair resolved when
|Delta| > q * SE with q fixed at the well-estimated sup-t critical value 2.98
(2.963 at B=1000, 2.981 at B=5000, so its own MC error is small relative to the
quantity under test). Recount per block per replicate.

Complements results_floor_ci.json, which held the gap fixed and resampled the
width; this holds the critical value fixed and resamples both gap and width.

Known bias, recorded rather than hidden: a bootstrap resample of C clusters holds
only ~63% of them distinct, so the SE estimated inside a replicate comes from
fewer effective clusters than the real design carries and runs large. Every count
here is therefore biased DOWN relative to how often the real design resolves a
pair, and never reads as a calibrated probability that a verdict is correct.

The bias is reported PER BLOCK, because it is not common across them: the means
are close but the right tail is much heavier within SSL. A pooled
ratio would assert the comparability that a between-block contrast depends on
instead of measuring it. For that reason the primary evidence is the studentized
margin at the point estimate, |Delta| / (q*SE), also recorded here: it states the
same thing directly, needs no resampling and so carries no bias to disclose, and
the survival counts largely restate it.

Writes results_verdict_ci.json. Modifies nothing.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, KEY, weighted_eer

Q_SUPT = 2.98
R = int(sys.argv[1]) if len(sys.argv) > 1 else 60
SEED = 20260821
SSL_ERA = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
BASELINE = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]


def main():
    t0 = time.time()
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk_idx = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    att_idx = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    n, n_spk = len(labels), spk_idx.max() + 1
    is_spoof = labels == 0
    spoof_atts = np.unique(att_idx[is_spoof])
    n_att = att_idx.max() + 1

    names = SSL_ERA + BASELINE
    orders = {}
    for m in names:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        orders[m] = np.argsort(np.array([float(d[u]) for u in utts]))
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]

    def eers(w):
        return np.array([100 * weighted_eer(orders[m], labels, w) for m in names])

    def block(a, b):
        sa, sb = a in SSL_ERA, b in SSL_ERA
        return "cross" if sa != sb else ("within_ssl" if sa else "within_baseline")

    def verdicts(w0):
        """(per-pair resolved flags, block counts) under |Delta| > q*SE_jackknife."""
        base = eers(w0)
        jack_spk = np.empty((n_spk, len(names)))
        for k in range(n_spk):
            w = w0.copy()
            w[spk_idx == k] = 0.0
            jack_spk[k] = eers(w) if w.sum() > 0 else base
        jack_att = np.empty((len(spoof_atts), len(names)))
        for j, k in enumerate(spoof_atts):
            w = w0.copy()
            w[is_spoof & (att_idx == k)] = 0.0
            jack_att[j] = eers(w) if (w * (1 - labels)).sum() > 0 else base
        na = len(spoof_atts)
        flags, ses, deltas = {}, {}, {}
        c = {k: 0 for k in ("all", "cross", "within_ssl", "within_baseline")}
        for a, b in pairs:
            ia, ib = names.index(a), names.index(b)
            ds = jack_spk[:, ia] - jack_spk[:, ib]
            da = jack_att[:, ia] - jack_att[:, ib]
            v = ((n_spk - 1) / n_spk * float(np.sum((ds - ds.mean()) ** 2))
                 + (na - 1) / na * float(np.sum((da - da.mean()) ** 2)))
            res = bool(abs(base[ia] - base[ib]) > Q_SUPT * np.sqrt(v))
            flags[f"{a} vs {b}"] = res
            ses[f"{a} vs {b}"] = float(np.sqrt(v))
            deltas[f"{a} vs {b}"] = float(base[ia] - base[ib])
            c["all"] += res
            c[block(a, b)] += res
        return flags, c, ses, deltas

    # The rule below approximates the campaign's (percentile bootstrap AND jackknife
    # must both exclude zero) with a single studentized test. Approximating one rule
    # by another is only safe if it decides the observed data identically, so that is
    # checked before any resampling: a distribution built on a rule that disagreed at
    # the point estimate would measure the substitution, not the sampling.
    point_flags, point_counts, point_ses, point_deltas = verdicts(np.ones(n))
    sel = json.load(open(Path(__file__).parent / "results_selection.json"))["21df"]["pairs"]
    disagree = [k for k, v in point_flags.items()
                if v != (sel.get(k) or sel[" vs ".join(k.split(" vs ")[::-1])])["resolved_simultaneous"]]
    assert not disagree, f"proxy rule disagrees with campaign verdicts on: {disagree}"
    assert point_counts == {"all": 18, "cross": 16, "within_ssl": 2, "within_baseline": 0}, point_counts
    print(f"point-estimate check: {point_counts}, 0/28 disagreements with the campaign", flush=True)

    rng = np.random.default_rng(SEED)
    counts = {k: [] for k in ("all", "cross", "within_ssl", "within_baseline")}
    per_pair_res = {f"{a} vs {b}": 0 for a, b in pairs}
    se_ratio = {f"{a} vs {b}": [] for a, b in pairs}

    for r in range(R):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        drawn = rng.choice(spoof_atts, size=len(spoof_atts), replace=True)
        ca = np.bincount(drawn, minlength=n_att)
        w0 = cs[spk_idx].astype(np.float64)
        w0[is_spoof] *= ca[att_idx[is_spoof]]
        if w0.sum() == 0 or (w0 * labels).sum() == 0 or (w0 * (1 - labels)).sum() == 0:
            continue
        flags, c, ses, _ = verdicts(w0)
        for k, res in flags.items():
            per_pair_res[k] += int(res)
            se_ratio[k].append(ses[k] / point_ses[k])
        for k in counts:
            counts[k].append(c[k])
        if r < 3 or (r + 1) % 10 == 0:
            print(f"  replicate {r+1}/{R}: all={c['all']} cross={c['cross']} "
                  f"ssl={c['within_ssl']} base={c['within_baseline']} "
                  f"[{(time.time()-t0)/60:.1f} min]", flush=True)

    results = {"R": len(counts["all"]), "q_supt_fixed": Q_SUPT, "seed": SEED,
               "method": "outer bootstrap over speakers and attacks; two-way jackknife SE; "
                         "resolved iff |Delta| > q*SE",
               "point_estimates": point_counts,
               "point_estimate_check": "proxy rule reproduces the campaign's resolved/"
                                       "unresolved verdict on all 28 pairs (asserted, not asserted-to)",
               "blocks": {}}
    for k, v in counts.items():
        v = np.array(v)
        results["blocks"][k] = {
            "median": int(np.median(v)),
            "ci95": [int(np.percentile(v, 2.5)), int(np.percentile(v, 97.5))],
            "mean": round(float(v.mean()), 2),
            "distribution": {int(i): int(cc) for i, cc in
                             enumerate(np.bincount(v, minlength=1)) if cc},
        }
    # A bootstrap resample of C clusters contains only ~63% of them distinct, so the
    # jackknife SE computed inside a replicate is estimated from fewer effective
    # clusters than the real data carries and runs systematically large. Every count
    # above is therefore biased DOWN as an estimate of how often the real design
    # resolves a pair.
    #
    # Reported PER BLOCK, not pooled. An earlier version flattened all 28 pairs into a
    # single ratio, which asserted that the bias is common across blocks at exactly the
    # point where the paper leans on a between-block comparison -- an assumption the
    # pooled number cannot test and in fact conceals, since the inflation is heavier in
    # the blocks whose verdicts die.
    def stats(rs):
        rs = np.array(rs)
        return {"mean": round(float(rs.mean()), 3),
                "median": round(float(np.median(rs)), 3),
                "p95": round(float(np.percentile(rs, 95)), 3),
                "pct_inflated": round(100 * float((rs > 1).mean()), 1)}

    by_block = {b: [] for b in ("cross", "within_ssl", "within_baseline")}
    for a, b in pairs:
        by_block[block(a, b)].extend(se_ratio[f"{a} vs {b}"])
    results["se_inflation_diagnostic"] = {
        "note": "ratio > 1 means the resampled design is harder to resolve on than the "
                "real one. NOT common across blocks -- the means are close but the tails "
                "differ markedly, so compare the per-block entries before reading any "
                "between-block contrast as robustness.",
        "pooled": stats([r for v in se_ratio.values() for r in v]),
        "by_block": {b: stats(v) for b, v in by_block.items()},
    }
    # The margin each pair must clear at the point estimate, |Delta| / (q*SE). This is
    # the direct statement of the same evidence: it needs no resampling, so it carries
    # no bias to disclose, and the survival counts above largely restate it.
    results["studentized_margin_point_estimate"] = {
        f"{a} vs {b}": round(abs(point_deltas[f"{a} vs {b}"])
                             / (Q_SUPT * point_ses[f"{a} vs {b}"]), 3)
        for a, b in pairs}
    results["margin_by_block"] = {}
    for b in ("cross", "within_ssl", "within_baseline"):
        m = sorted(results["studentized_margin_point_estimate"][f"{x} vs {y}"]
                   for x, y in pairs if block(x, y) == b)
        results["margin_by_block"][b] = {"min": m[0], "max": m[-1], "n": len(m)}
    results["per_pair_p_resolved"] = {
        k: round(c / len(counts["all"]), 3) for k, c in per_pair_res.items()}
    print("\n" + json.dumps(results["blocks"], indent=1), flush=True)
    out = Path(__file__).parent / "results_verdict_ci.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out} in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
