"""EXP-101 post-selection analysis: full-family inference over all pairs.

Adjacency on the observed-EER ladder is a selected comparison, so per-pair
intervals are post-selection quantities. This script removes the objection by
inferring over the complete family instead:

  - all C(K,2) pairs from one clustered bootstrap (21DF: 28, ITW: 6);
  - sup-t simultaneous bands (Montiel Olea & Plagborg-Moller): the 95th
    percentile of max_p |Delta_b^p - mean_b Delta^p| / sd^p, applied to every
    pair, so the whole family holds jointly at 95%;
  - Holm-Bonferroni over the full family (percentile bootstrap p-values);
  - rank intervals built from the simultaneous verdicts, which inherit the sup-t
    family's joint validity (a bootstrap rank percentile is a stability interval,
    not a confidence set, and is reported separately under that name).

Certified variants after the correctness audit: two-way percentile and two-way
delete-one-cluster jackknife (the pigeonhole variant is withdrawn).
"""

import csv
import gzip
import json
from pathlib import Path

import numpy as np

from m1_campaign import DF_SCORES, EXP001, ITW_META, KEY, OFF, plain_eer, weighted_eer

B = 5000
SEED = 20260817


def clustered_eer_replicates(rng, scores, labels, spk_idx, att_idx, names):
    """B x K matrix of EERs under the two-way (or speaker-only) clustered scheme."""
    n, n_spk = len(labels), spk_idx.max() + 1
    is_spoof = labels == 0
    has_att = att_idx is not None
    orders = {m: np.argsort(scores[m]) for m in names}
    if has_att:
        spoof_atts = np.unique(att_idx[is_spoof])
        n_att = att_idx.max() + 1
    out = np.empty((B, len(names)))
    for i in range(B):
        cs = np.bincount(rng.integers(0, n_spk, n_spk), minlength=n_spk)
        w = cs[spk_idx].astype(np.float64)
        if has_att:
            drawn = rng.choice(spoof_atts, size=len(spoof_atts), replace=True)
            ca = np.bincount(drawn, minlength=n_att)
            w[is_spoof] *= ca[att_idx[is_spoof]]
        for k, m in enumerate(names):
            out[i, k] = 100 * weighted_eer(orders[m], labels, w)
    return out


def jackknife_cis(rng, scores, labels, spk_idx, att_idx, names, pairs, hat):
    """Delete-one-cluster jackknife normal CI per pair (the second certified variant).

    Same estimator as the campaign's per-pair analysis (audited as a correct
    Cameron-Gelbach-Miller two-way form): V = V_spk + V_att - V_intersection,
    with the intersection term approximated by the i.i.d. bootstrap variance and
    the whole floored at max(V_spk, V_att).
    """
    n, n_spk = len(labels), spk_idx.max() + 1
    is_spoof = labels == 0
    has_att = att_idx is not None
    orders = {m: np.argsort(scores[m]) for m in names}

    def eers(w):
        return np.array([weighted_eer(orders[m], labels, w) for m in names]) * 100

    boot_iid = np.empty((B, len(names)))
    for i in range(B):
        w = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64)
        boot_iid[i] = eers(w)

    jack_spk = np.empty((n_spk, len(names)))
    for k in range(n_spk):
        w = np.ones(n)
        w[spk_idx == k] = 0.0
        jack_spk[k] = eers(w)
    if has_att:
        atts = np.unique(att_idx[is_spoof])
        jack_att = np.empty((len(atts), len(names)))
        for j, k in enumerate(atts):
            w = np.ones(n)
            w[is_spoof & (att_idx == k)] = 0.0
            jack_att[j] = eers(w)
    out = {}
    for idx, (a, b) in enumerate(pairs):
        ia, ib = names.index(a), names.index(b)
        v_naive = float(np.var(boot_iid[:, ia] - boot_iid[:, ib]))
        ds = jack_spk[:, ia] - jack_spk[:, ib]
        v = (n_spk - 1) / n_spk * float(np.sum((ds - ds.mean()) ** 2))
        if has_att:
            da = jack_att[:, ia] - jack_att[:, ib]
            na = len(da)
            v_att = (na - 1) / na * float(np.sum((da - da.mean()) ** 2))
            v = max(v + v_att - v_naive, max(v, v_att))
        se = np.sqrt(v)
        lo, hi = hat[idx] - 1.959963984540054 * se, hat[idx] + 1.959963984540054 * se
        out[f"{a} vs {b}"] = {"ci_jackknife": [round(float(lo), 3), round(float(hi), 3)],
                              "resolved_jackknife": bool(not (lo <= 0 <= hi))}
    return out


def holm(pvals):
    order = sorted(pvals, key=pvals.get)
    m, adj, running = len(order), {}, 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * pvals[k]))
        adj[k] = round(running, 4)
    return adj


def analyse(tag, scores, labels, spk_idx, att_idx):
    names = sorted(scores, key=lambda m: plain_eer(scores[m], labels))
    point = {m: 100 * plain_eer(scores[m], labels) for m in names}
    rng = np.random.default_rng(SEED)
    reps = clustered_eer_replicates(rng, scores, labels, spk_idx, att_idx, names)
    K = len(names)

    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    deltas = np.empty((B, len(pairs)))
    hat = np.empty(len(pairs))
    for j, (a, b) in enumerate(pairs):
        ia, ib = names.index(a), names.index(b)
        deltas[:, j] = reps[:, ia] - reps[:, ib]
        hat[j] = point[a] - point[b]
    sd = deltas.std(axis=0, ddof=1)
    centred = np.abs(deltas - deltas.mean(axis=0)) / np.maximum(sd, 1e-12)
    q_sup = float(np.percentile(centred.max(axis=1), 95))

    per_pair, pvals = {}, {}
    for j, (a, b) in enumerate(pairs):
        d = deltas[:, j]
        lo, hi = float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))
        slo, shi = hat[j] - q_sup * sd[j], hat[j] + q_sup * sd[j]
        p_lo = float(np.mean(d <= 0))
        p = min(1.0, 2 * min(p_lo, 1 - p_lo) + 1 / B)
        key = f"{a} vs {b}"
        pvals[key] = p
        per_pair[key] = {
            "delta_eer_pts": round(float(hat[j]), 3),
            "boot_sd": round(float(sd[j]), 3),
            "ci_pointwise": [round(lo, 3), round(hi, 3)],
            "ci_simultaneous": [round(float(slo), 3), round(float(shi), 3)],
            "resolved_pointwise": bool(not (lo <= 0 <= hi)),
            "resolved_simultaneous": bool(not (slo <= 0 <= shi)),
            "p_raw": round(p, 4),
            "adjacent": bool(abs(names.index(a) - names.index(b)) == 1),
        }
    adj = holm(pvals)
    jack = jackknife_cis(rng, scores, labels, spk_idx, att_idx, names, pairs, hat)
    for key in per_pair:
        per_pair[key]["p_holm_family"] = adj[key]
        per_pair[key]["resolved_holm_family"] = bool(adj[key] <= 0.05)
        per_pair[key].update(jack[key])
        per_pair[key]["certified_agree"] = bool(
            per_pair[key]["resolved_pointwise"] == per_pair[key]["resolved_jackknife"])

    # Rank intervals from the SIMULTANEOUS verdicts. The sup-t family is jointly
    # valid at 95%, so
    #     rank_i in [1 + #{j significantly better than i}, K - #{j : i sig. better}]
    # inherits that joint validity. The bootstrap-percentile alternative is a
    # *stability* interval (challengeR-style): marginal, no simultaneity, and the
    # bootstrap is inconsistent for ranks near ties -- it is retained alongside,
    # named for what it is, never called a confidence set.
    ranks = np.argsort(np.argsort(reps, axis=1), axis=1) + 1
    better, worse = {m: 0 for m in names}, {m: 0 for m in names}
    for (a, b) in pairs:
        v = per_pair[f"{a} vs {b}"]
        if not v["resolved_simultaneous"]:
            continue
        hi, lo = (a, b) if v["delta_eer_pts"] < 0 else (b, a)  # lower EER = better
        better[lo] += 1
        worse[hi] += 1
    K = len(names)
    rank_sets = {
        m: {"point_rank": int(np.argsort(np.argsort([point[x] for x in names]))[i] + 1),
            "rank_ci95_simultaneous": [1 + better[m], K - worse[m]],
            "bootstrap_rank_stability_interval": [
                int(np.floor(np.percentile(ranks[:, i], 2.5))),
                int(np.ceil(np.percentile(ranks[:, i], 97.5)))],
            "pooled_eer": round(point[m], 3)}
        for i, m in enumerate(names)
    }

    n_res = {
        "pointwise": sum(v["resolved_pointwise"] for v in per_pair.values()),
        "simultaneous": sum(v["resolved_simultaneous"] for v in per_pair.values()),
        "holm_family": sum(v["resolved_holm_family"] for v in per_pair.values()),
        "jackknife_pointwise": sum(v["resolved_jackknife"] for v in per_pair.values()),
    }
    n_res["certified_variants_agree_on"] = sum(v["certified_agree"] for v in per_pair.values())
    print(f"[{tag}] {K} systems, {len(pairs)} pairs, sup-t crit {q_sup:.2f}; "
          f"resolved: pointwise {n_res['pointwise']}, Holm {n_res['holm_family']}, "
          f"sup-t {n_res['simultaneous']}, jackknife {n_res['jackknife_pointwise']}; "
          f"two certified variants agree on {n_res['certified_variants_agree_on']}/{len(pairs)}",
          flush=True)
    for m, v in rank_sets.items():
        print(f"   {m:<16} EER {v['pooled_eer']:6.2f}  rank {v['point_rank']} "
              f"simultaneous {v['rank_ci95_simultaneous']}  "
              f"(bootstrap-stability {v['bootstrap_rank_stability_interval']})", flush=True)
    return {"systems": names, "n_pairs": len(pairs), "supt_critical_value": round(q_sup, 3),
            "n_resolved": n_res, "rank_sets": rank_sets, "pairs": per_pair}


def load_21df():
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
    return scores, labels, spk_idx, att_idx


def load_itw():
    spk = {}
    with open(ITW_META) as f:
        for r in csv.DictReader(f):
            spk[Path(r["file"]).stem] = r["speaker"]
    raw = {}
    for m, path in (("XLSR-Mamba", OFF / "xlsr-mamba/Bmamba5_In-the-Wild_WCE_1e-06_ES144_NE12.txt"),
                    ("XLS-R+SLS", OFF / "xlsr-sls/scores_Wild.txt")):
        raw[m] = {Path(k).stem: v for k, v in
                  (l.split()[:2] for l in path.read_text().splitlines())}
    for m, tag in (("SSL-AASIST", "ssl"), ("AASIST", "aasist")):
        with gzip.open(EXP001 / f"{tag}_itw.csv.gz", "rt") as f:
            raw[m] = {r["utt_id"]: r["score"] for r in csv.DictReader(f)}
    common = sorted(set.intersection(*(set(v) for v in raw.values())) & set(spk))
    with gzip.open(EXP001 / "ssl_itw.csv.gz", "rt") as f:
        lab = {r["utt_id"]: r["label"] for r in csv.DictReader(f)}
    labels = np.array([1 if lab[u] == "bonafide" else 0 for u in common])
    spk_idx = np.unique([spk[u] for u in common], return_inverse=True)[1]
    scores = {m: np.array([float(raw[m][u]) for u in common]) for m in raw}
    return scores, labels, spk_idx, None


def main():
    results = {"B": B, "seed": SEED,
               "note": "certified variants after audit: two-way percentile + two-way jackknife"}
    results["21df"] = analyse("21df", *load_21df())
    results["itw"] = analyse("itw", *load_itw())
    out = Path(__file__).parent.parent / "derived" / "results_selection.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
