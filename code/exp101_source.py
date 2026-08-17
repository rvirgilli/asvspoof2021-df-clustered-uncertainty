"""EXP-101: how much of the speaker floor is between SOURCE CORPUS, not between speaker?

The 21DF bona-fide pool is not one homogeneous speaker sample: column 4 of the metadata records three source corpora (asvspoof, vcc2018,
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
import sys
from pathlib import Path

import numpy as np

from exp101_floor import input_provenance
from m1_campaign import DF_SCORES, KEY, weighted_eer

EXP105 = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP105))
from coverage_interaction import exact_refits, jack_var  # noqa: E402

Z95 = 1.959963984540054
Q_DRAWS = 200000
SSL_ERA = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
BASELINE = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]


def jack_cov(refits):
    g = len(refits)
    centred = refits - refits.mean(axis=0, keepdims=True)
    return (g - 1.0) / g * centred.T @ centred


def nearest_psd(matrix):
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2.0)
    return (vectors * np.maximum(values, 0.0)) @ vectors.T, values


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
    score_vectors = {}
    for m in names:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        score_vectors[m] = np.array([float(d[u]) for u in utts])
        orders[m] = np.argsort(score_vectors[m])

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

    derived = Path(__file__).parent.parent / "derived"
    fl_path = derived / "results_floor.json"
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
        # This is a decomposition of the measured finite-A delete-speaker term. It
        # is not an A-to-infinity or S-to-infinity variance decomposition because
        # speaker-by-attack interaction remains inside the term.
        results["pairs"][key] = {
            "block": v["block"],
            "between_source_share_of_speaker_ss": round(share, 3),
            "finite_A_speaker_component_width_pts":
                v["finite_A_speaker_component_width_pts"],
            "descriptive_between_source_width_component_pts":
                round(v["finite_A_speaker_component_width_pts"] * float(np.sqrt(share)), 3),
            "asymptotic_interpretation": "none; speaker-by-attack interaction is not separated",
        }
        print(f"  {key:<34} between-source {100*share:5.1f}%  "
              f"finite-A component {v['finite_A_speaker_component_width_pts']:6.3f}; "
              f"descriptive between-source "
              f"component {results['pairs'][key]['descriptive_between_source_width_component_pts']:6.3f}",
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
        exceedances = int(np.sum(null >= obs))
        perm[key] = {
            "observed": obs,
            "null_mean": round(float(null.mean()), 4),
            "null_p95": round(float(np.percentile(null, 95)), 4),
            "exceedances": exceedances,
            "p_value": round((exceedances + 1) / (B_PERM + 1), 5),
        }
        print(f"  perm {key:<34} obs {obs:.3f}  null mean {null.mean():.3f}  p={perm[key]['p_value']:.4f}",
              flush=True)
    results["permutation_null"] = {
        "B": B_PERM, "seed": 20260822,
        "p_value_rule": "(number of permuted statistics >= observed + 1) / (B + 1)",
        "analytic_expected_share_under_no_effect": round(exp_null, 4),
        "note": "share of the delete-one-speaker sum of squares falling between corpora "
                "when speaker labels are permuted; (k-1)/(n-1) with k=3, n=93",
        "pairs": perm,
        "n_pairs_p_below_0.05": int(sum(1 for v in perm.values() if v["p_value"] < 0.05)),
    }

    # Leave-one-corpus-out. Clustering on 3 corpora is not stably estimable (2 df),
    # so drop each corpus and recompute the exact observed-cell multiway jackknife.
    # This supersedes the earlier V_speaker + V_attack implementation, which called
    # itself two-way while omitting the inclusion-exclusion intersection term.
    ALL_PAIRS = [f"{a} vs {b}" for i, a in enumerate(names) for b in names[i + 1:]]
    contrast = np.zeros((len(ALL_PAIRS), len(names)))
    for i, key in enumerate(ALL_PAIRS):
        a, b = key.split(" vs ")
        contrast[i, names.index(a)] = 1.0
        contrast[i, names.index(b)] = -1.0
    att_idx_all = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    loco = {}
    for drop in sources:
        keep_spk = src_of_spk != drop
        keep_trial = keep_spk[spk_idx]
        sub_labels = labels[keep_trial]
        _, sub_spk = np.unique(spk_idx[keep_trial], return_inverse=True)
        sub_spoof = sub_labels == 0
        sub_att = np.full(len(sub_labels), -1, dtype=np.int32)
        _, sub_att[sub_spoof] = np.unique(att_idx_all[keep_trial][sub_spoof],
                                          return_inverse=True)
        sub_cell = np.full(len(sub_labels), -1, dtype=np.int32)
        _, sub_cell[sub_spoof] = np.unique(
            np.column_stack([sub_spk[sub_spoof], sub_att[sub_spoof]]), axis=0,
            return_inverse=True)
        ns, na, nc = sub_spk.max() + 1, sub_att.max() + 1, sub_cell.max() + 1
        base = np.empty(len(names))
        ref_s = np.empty((ns, len(names)))
        ref_a = np.empty((na, len(names)))
        ref_c = np.empty((nc, len(names)))
        for j, name in enumerate(names):
            scores = score_vectors[name][keep_trial]
            order = np.argsort(scores)
            base[j] = 100 * weighted_eer(order, sub_labels, np.ones(len(sub_labels)))
            ref_s[:, j] = 100 * exact_refits(scores, sub_labels, sub_spk, ns, order=order)
            ref_a[:, j] = 100 * exact_refits(scores, sub_labels, sub_att, na, order=order)
            ref_c[:, j] = 100 * exact_refits(scores, sub_labels, sub_cell, nc, order=order)
        cov_s, cov_a, cov_c = jack_cov(ref_s), jack_cov(ref_a), jack_cov(ref_c)
        cov_raw = cov_s + cov_a - cov_c
        cov_psd, raw_eigenvalues = nearest_psd(cov_raw)
        pair_cov_psd = contrast @ cov_psd @ contrast.T
        q_seed = [20260822, 900, sources.index(drop)]
        rng_q = np.random.default_rng(np.random.SeedSequence(q_seed))
        system_draws = rng_q.multivariate_normal(
            np.zeros(len(names)), cov_psd, size=Q_DRAWS, check_valid="ignore")
        pair_draws = system_draws @ contrast.T
        q = float(np.percentile(
            np.max(np.abs(pair_draws) /
                   np.sqrt(np.maximum(np.diag(pair_cov_psd), 1e-18)), axis=1), 95))
        ent = {}
        for pair_index, key in enumerate(ALL_PAIRS):
            a, b = key.split(" vs ")
            ia, ib = names.index(a), names.index(b)
            c = contrast[pair_index]
            vs = float(c @ cov_s @ c)
            va = float(c @ cov_a @ c)
            vc = float(c @ cov_c @ c)
            raw = vs + va - vc
            v = max(raw, vs, va, 0.0)
            ent[key] = {"delta_eer_pts": round(float(base[ia] - base[ib]), 3),
                        "V_speaker": vs, "V_attack": va,
                        "V_speaker_attack_cell": vc,
                        "V_raw_inclusion_exclusion": raw,
                        "V_psd_floor": v,
                        "resolved": bool(abs(base[ia] - base[ib]) > q * np.sqrt(v))}
        loco[drop] = {"n_speakers_kept": int(ns),
                      "n_attacks_kept": int(na),
                      "n_observed_cells_kept": int(nc),
                      "q95_gaussian_exact_cell_max_t": q,
                      "q_draws": Q_DRAWS,
                      "q_seed_components": q_seed,
                      "raw_system_covariance_eigenvalues": raw_eigenvalues.tolist(),
                      "pairs": ent}
        print(f"  LOCO drop {drop:<9} kept {ns:2d} speakers, "
              f"{sum(e['resolved'] for e in ent.values())}/28 pairs resolved", flush=True)

    full = {k: (SEL := None) for k in ()}
    sel_full = json.load(open(derived / "results_selection.json"))["21df"]["pairs"]
    flips = []
    for key in ALL_PAIRS:
        a, b = key.split(" vs ")
        ref = (sel_full.get(key) or sel_full[f"{b} vs {a}"])["resolved_simultaneous"]
        for drop in sources:
            if loco[drop]["pairs"][key]["resolved"] != ref:
                flips.append({"pair": key, "dropped_corpus": drop,
                              "full_data": ref, "refit": loco[drop]["pairs"][key]["resolved"]})
    results["leave_one_corpus_out"] = {
        "estimator": "exact delete-one V_speaker + V_attack - V_observed_speaker_attack_cell, "
                     "with transparent max(raw, V_speaker, V_attack, 0) floor",
        "multiplicity": "a separately recomputed Gaussian max-t band over all 28 pairs "
                        "for each leave-one-corpus-out covariance",
        "note": "drop each source corpus, refit paired Delta-EER and the exact-cell "
                "multiway jackknife on the remaining two; a verdict that survives all "
                "three refits is not driven by any single provenance",
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
        "reading": "a substantial share of the measured finite-A delete-speaker sum of "
                   "squares is between three recording provenances. This is descriptive: "
                   "speaker-by-attack interaction is not separated and no speaker-count or "
                   "attack-count asymptote is inferred.",
    }
    print("\nsummary:", json.dumps(results["summary"], indent=1), flush=True)
    out = derived / "results_source.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
