"""EXP-101: how much of the speaker floor is between SOURCE CORPUS, not between speaker?

Raised by external review. The 21DF bona-fide pool is not one homogeneous speaker
sample: column 4 of the metadata records three source corpora (asvspoof, vcc2018,
vcc2020), with different recording provenance. If a large share of the speaker
variance is really between corpora, two things follow and they cut opposite ways:

  1. "collect more speakers" would not shrink the between-corpus part, so the floor
     asymptotes above zero even in speakers -- the prescription becomes "collect
     across more recording conditions", a different and more useful statement;
  2. if the honest exchangeable unit on the bona-fide side is nearer the corpus
     (3 levels) than the speaker (93), our own intervals are ANTI-conservative.

Method: the delete-one-speaker jackknife already gives one influence value per
speaker for each pair. Group those by the speaker's source corpus and split the
sum of squares into between- and within-corpus parts. No new data, no simulation.

Writes results_source.json. Modifies nothing.
"""

import json
from pathlib import Path

import numpy as np

from exp101_floor import input_provenance
from m1_campaign import DF_SCORES, KEY, weighted_eer

Z95 = 1.959963984540054
SSL_ERA = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
BASELINE = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]


def main():
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5], p[3])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk_names, spk_idx = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)
    n, n_spk = len(labels), len(spk_names)
    is_bona = labels == 1

    # A speaker's source corpus is defined by its bona-fide trials: on a spoof trial
    # the speaker field is the VC/TTS TARGET speaker, and only 62 of the 93 appear
    # there at all, so the bona-fide side is the one with a well-defined provenance.
    spk_source = {}
    for u in utts:
        s, _, lab, src = utt2meta[u]
        if lab == "bonafide":
            spk_source.setdefault(s, src)
    sources = sorted(set(spk_source.values()))
    src_of_spk = np.array([spk_source.get(s, "none") for s in spk_names])
    n_spoof_spk = len({utt2meta[u][0] for u in utts if utt2meta[u][2] != "bonafide"})

    names = SSL_ERA + BASELINE
    orders = {}
    for m in names:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        orders[m] = np.argsort(np.array([float(d[u]) for u in utts]))

    def eers(w):
        return np.array([100 * weighted_eer(orders[m], labels, w) for m in names])

    print(f"{n_spk} bona-fide speakers over {len(sources)} source corpora; "
          f"{n_spoof_spk} distinct speaker ids on the spoof side", flush=True)
    for s in sources:
        k = int((src_of_spk == s).sum())
        t = int(sum(1 for u in utts if utt2meta[u][3] == s and utt2meta[u][2] == "bonafide"))
        print(f"  {s:<10} {k:3d} speakers, {t:6d} bona-fide trials", flush=True)

    jack = np.empty((n_spk, len(names)))
    for k in range(n_spk):
        w = np.ones(n)
        w[spk_idx == k] = 0.0
        jack[k] = eers(w)

    fl_path = Path(__file__).parent / "results_floor.json"
    fl = json.load(open(fl_path))["pairs"]
    results = {
        "_input_provenance_sha256": input_provenance(fl_path),
        "question": "what share of the delete-one-speaker sum of squares is BETWEEN "
                    "source corpus rather than between speaker within corpus",
        "n_bonafide_speakers": int(n_spk),
        "n_spoof_side_speaker_ids": int(n_spoof_spk),
        "sources": {s: {"n_speakers": int((src_of_spk == s).sum())} for s in sources},
        "pairs": {},
    }

    for key, v in fl.items():
        a, b = key.split(" vs ")
        ia, ib = names.index(a), names.index(b)
        d = jack[:, ia] - jack[:, ib]
        grand = d.mean()
        ss_tot = float(np.sum((d - grand) ** 2))
        ss_bet = 0.0
        for s in sources:
            m = src_of_spk == s
            if m.sum():
                ss_bet += float(m.sum()) * (float(d[m].mean()) - grand) ** 2
        share = ss_bet / ss_tot if ss_tot > 0 else float("nan")
        # The floor scales as sqrt(V_spk). Adding speakers WITHIN these three corpora
        # shrinks only the within-corpus part, so the floor tends to sqrt(share) of
        # its current value rather than to zero.
        results["pairs"][key] = {
            "block": v["block"],
            "between_source_share_of_speaker_ss": round(share, 3),
            "floor_width_pts": v["floor_width_pts"],
            "floor_limit_if_speakers_added_within_these_corpora":
                round(v["floor_width_pts"] * float(np.sqrt(share)), 3),
        }
        print(f"  {key:<34} between-source {100*share:5.1f}%  "
              f"floor {v['floor_width_pts']:6.3f} -> asymptote "
              f"{results['pairs'][key]['floor_limit_if_speakers_added_within_these_corpora']:6.3f}",
              flush=True)

    # Is the between-corpus share larger than chance? Under no corpus effect the
    # expected share of a sum of squares split into k groups of n items is
    # (k-1)/(n-1); with k=3, n=93 that is 2.2%. A permutation over speaker labels
    # gives the null distribution exactly, so this stops being a description and
    # becomes a tested claim. Three corpora is only 2 degrees of freedom, which is
    # precisely why the null has to be computed rather than eyeballed.
    rng = np.random.default_rng(20260822)
    B_PERM = 20000
    exp_null = (len(sources) - 1) / (n_spk - 1)
    perm = {}
    for key, v in results["pairs"].items():
        a, b = key.split(" vs ")
        ia, ib = names.index(a), names.index(b)
        d = jack[:, ia] - jack[:, ib]
        e = d - d.mean()
        ss_tot = float(np.sum(e ** 2))
        counts = np.array([int((src_of_spk == s).sum()) for s in sources])
        null = np.empty(B_PERM)
        for t in range(B_PERM):
            perm_idx = rng.permutation(n_spk)
            pos, ss_b = 0, 0.0
            for c in counts:
                grp = e[perm_idx[pos:pos + c]]
                ss_b += c * (float(grp.mean()) ** 2)
                pos += c
            null[t] = ss_b / ss_tot
        obs = v["between_source_share_of_speaker_ss"]
        perm[key] = {
            "observed": obs,
            "null_mean": round(float(null.mean()), 4),
            "null_p95": round(float(np.percentile(null, 95)), 4),
            "p_value": round(float((null >= obs).mean()), 5),
        }
        print(f"  perm {key:<34} obs {obs:.3f}  null mean {null.mean():.3f}  p={perm[key]['p_value']:.4f}",
              flush=True)
    results["permutation_null"] = {
        "B": B_PERM, "seed": 20260822,
        "analytic_expected_share_under_no_effect": round(exp_null, 4),
        "note": "share of the delete-one-speaker sum of squares falling between corpora "
                "when speaker labels are permuted; (k-1)/(n-1) with k=3, n=93",
        "pairs": perm,
        "n_pairs_p_below_0.05": int(sum(1 for v in perm.values() if v["p_value"] < 0.05)),
    }

    # Leave-one-corpus-out. The concession "if the corpus is the exchangeable unit our
    # intervals are anti-conservative" names a direction without a magnitude, which reads
    # as conceding our own numbers are wrong. Clustering on 3 corpora is not estimable
    # (2 df), so instead we drop each corpus in turn and refit on the remaining two: if
    # no single provenance drives a verdict, the corpus effect does not change what the
    # paper concludes, and that is a bound rather than a concession.
    Q = 2.98
    ALL_PAIRS = [f"{a} vs {b}" for i, a in enumerate(names) for b in names[i + 1:]]
    att_idx_all = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    is_spoof = labels == 0
    spoof_atts = np.unique(att_idx_all[is_spoof])
    loco = {}
    for drop in sources:
        keep_spk = src_of_spk != drop
        keep_trial = keep_spk[spk_idx]
        w0 = keep_trial.astype(np.float64)
        base = eers(w0)
        ks = np.where(keep_spk)[0]
        js = np.empty((len(ks), len(names)))
        for i, k in enumerate(ks):
            w = w0.copy(); w[spk_idx == k] = 0.0
            js[i] = eers(w)
        ja = np.empty((len(spoof_atts), len(names)))
        for i, k in enumerate(spoof_atts):
            w = w0.copy(); w[is_spoof & (att_idx_all == k)] = 0.0
            ja[i] = eers(w)
        ns, na = len(ks), len(spoof_atts)
        ent = {}
        for key in ALL_PAIRS:
            a, b = key.split(" vs ")
            ia, ib = names.index(a), names.index(b)
            ds, da = js[:, ia] - js[:, ib], ja[:, ia] - ja[:, ib]
            v = ((ns - 1) / ns * float(np.sum((ds - ds.mean()) ** 2))
                 + (na - 1) / na * float(np.sum((da - da.mean()) ** 2)))
            ent[key] = {"delta_eer_pts": round(float(base[ia] - base[ib]), 3),
                        "resolved": bool(abs(base[ia] - base[ib]) > Q * np.sqrt(v))}
        loco[drop] = {"n_speakers_kept": int(ns), "pairs": ent}
        print(f"  LOCO drop {drop:<9} kept {ns:2d} speakers, "
              f"{sum(e['resolved'] for e in ent.values())}/28 pairs resolved", flush=True)

    full = {k: (SEL := None) for k in ()}
    sel_full = json.load(open(Path(__file__).parent / "results_selection.json"))["21df"]["pairs"]
    flips = []
    for key in ALL_PAIRS:
        a, b = key.split(" vs ")
        ref = (sel_full.get(key) or sel_full[f"{b} vs {a}"])["resolved_simultaneous"]
        for drop in sources:
            if loco[drop]["pairs"][key]["resolved"] != ref:
                flips.append({"pair": key, "dropped_corpus": drop,
                              "full_data": ref, "refit": loco[drop]["pairs"][key]["resolved"]})
    results["leave_one_corpus_out"] = {
        "critical_value": Q,
        "note": "drop each source corpus, refit the paired Delta-EER and its two-way "
                "jackknife SE on the remaining two; a verdict that survives all three "
                "refits is not driven by any single provenance",
        "by_corpus": loco,
        "verdict_flips_vs_full_data": flips,
        "n_flips": len(flips),
    }
    print(f"  LOCO: {len(flips)} verdict flip(s) across 3 refits x 28 pairs",
          flush=True)
    for f in flips:
        print(f"    {f['pair']} flips {f['full_data']} -> {f['refit']} when dropping {f['dropped_corpus']}",
              flush=True)

    shares = [p["between_source_share_of_speaker_ss"] for p in results["pairs"].values()]
    results["summary"] = {
        "between_source_share_range": [round(min(shares), 3), round(max(shares), 3)],
        "median": round(float(np.median(shares)), 3),
        "reading": "a substantial share of what the paper calls speaker variance is "
                   "between three recording provenances. Adding speakers within these "
                   "corpora cannot shrink it, so the prescription is 'more sources', "
                   "not 'more speakers'; and if the corpus is the honest exchangeable "
                   "unit on the bona-fide side then our intervals are anti-conservative.",
    }
    print("\nsummary:", json.dumps(results["summary"], indent=1), flush=True)
    out = Path(__file__).parent / "results_source.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
