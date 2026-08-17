"""EXP-101: finite-A speaker component and per-pair variance decomposition.

Replaces the withdrawn A^-0.2 power-law claim. Subsampling attacks holds
the 93 speakers fixed, so the attack component of the paired Delta-EER variance
shrinks with A. The measured V_spk at A=110 is a finite-A component: under a
two-way random-effects decomposition it contains speaker-by-attack interaction
divided by A. The observed width 2*z_.975*sqrt(V_spk) therefore must not be
interpreted as an A-to-infinity floor unless that interaction is identified.

The output names the quantity directly as a finite-A speaker-component width. No
local slope or maximum attainable narrowing is reported because neither follows
without identifying how the interaction changes with A.

The same decomposition answers a separate question the paper raises but must not
guess at: why four baselines spanning 3.18 EER points are mutually unresolved while
a 0.97-point gap between modern systems resolves. Reported here as measured
variance components rather than asserted as a mechanism.

Writes results_floor.json. Modifies nothing.
"""

import hashlib
import json
from pathlib import Path

import numpy as np


def input_provenance(*paths):
    """sha256 of every input artifact, recorded in the output.

    Derived artifacts silently disagree with their inputs when an upstream file is
    re-run: this file's measured widths came from a selection run that was later
    regenerated at a different B, and nothing in the tree flagged it. Recording the
    input digests makes the staleness detectable instead of invisible.
    """
    out = {}
    for p in paths:
        p = Path(p)
        out[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    return out

from m1_campaign import DF_SCORES, KEY, plain_eer, weighted_eer

Z95 = 1.959963984540054
SSL_ERA = ["XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"]
BASELINE = ["RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"]


def main():
    utt2meta = {}
    for line in KEY.read_text().splitlines():
        p = line.split()
        if p[7] == "eval":
            utt2meta[p[1]] = (p[0], p[4], p[5])
    utts = sorted(utt2meta)
    labels = np.array([1 if utt2meta[u][2] == "bonafide" else 0 for u in utts])
    spk_idx = np.unique([utt2meta[u][0] for u in utts], return_inverse=True)[1]
    att_idx = np.unique([utt2meta[u][1] for u in utts], return_inverse=True)[1]
    n, is_spoof = len(labels), labels == 0
    n_spk = spk_idx.max() + 1
    spoof_atts = np.unique(att_idx[is_spoof])

    names = SSL_ERA + BASELINE
    scores, orders = {}, {}
    for m in names:
        d = dict(l.split()[:2] for l in DF_SCORES[m].read_text().splitlines())
        scores[m] = np.array([float(d[u]) for u in utts])
        orders[m] = np.argsort(scores[m])

    def eers(w):
        return np.array([100 * weighted_eer(orders[m], labels, w) for m in names])

    print(f"jackknifing {n_spk} speakers + {len(spoof_atts)} attacks over {len(names)} systems",
          flush=True)
    jack_spk = np.empty((n_spk, len(names)))
    for k in range(n_spk):
        w = np.ones(n)
        w[spk_idx == k] = 0.0
        jack_spk[k] = eers(w)
    jack_att = np.empty((len(spoof_atts), len(names)))
    for j, k in enumerate(spoof_atts):
        w = np.ones(n)
        w[is_spoof & (att_idx == k)] = 0.0
        jack_att[j] = eers(w)
    point = eers(np.ones(n))
    print("jackknife done", flush=True)

    derived = Path(__file__).parent.parent / "derived"
    sel_path = derived / "results_selection.json"
    sel = json.load(open(sel_path))["21df"]["pairs"]
    results = {
        "_input_provenance_sha256": input_provenance(sel_path),
        "measured_width_source": "results_selection.json pointwise CI (B=5000); the "
                                 "subsampling run in results_widths.json reports the same "
                                 "full-set widths to within ~2%",
        "estimator": "delete-one-cluster jackknife components of paired Delta-EER at "
                     "the observed A=110; width = 2*1.96*sqrt(V_spk)",
        "n_speakers": int(n_spk), "n_attacks": int(len(spoof_atts)),
        "identification_note": "V_spk contains speaker-by-attack interaction divided "
                               "by A. It is a finite-A component, not an A-to-infinity "
                               "floor; no counterfactual attack-budget claim is made.",
        "pairs": {},
    }
    na = len(spoof_atts)
    for block, group in (("within-modern", SSL_ERA), ("within-baseline", BASELINE)):
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                ia, ib = names.index(a), names.index(b)
                ds = jack_spk[:, ia] - jack_spk[:, ib]
                da = jack_att[:, ia] - jack_att[:, ib]
                v_spk = (n_spk - 1) / n_spk * float(np.sum((ds - ds.mean()) ** 2))
                v_att = (na - 1) / na * float(np.sum((da - da.mean()) ** 2))
                component_w = 2 * Z95 * np.sqrt(v_spk)
                key = f"{a} vs {b}"
                hit = sel.get(key) or sel.get(f"{b} vs {a}")
                meas_w = hit["ci_pointwise"][1] - hit["ci_pointwise"][0]
                results["pairs"][key] = {
                    "block": block,
                    "delta_eer_pts": round(float(point[ia] - point[ib]), 3),
                    "V_spk": round(v_spk, 4), "V_att": round(v_att, 4),
                    "speaker_fraction_of_two_marginal_components":
                        round(v_spk / (v_spk + v_att), 3),
                    "finite_A_speaker_component_width_pts": round(float(component_w), 3),
                    "measured_width_pts_A110": round(meas_w, 3),
                    "resolved_simultaneous": hit["resolved_simultaneous"],
                }
                r = results["pairs"][key]
                print(f"  [{block:<16}] {key:<34} d={r['delta_eer_pts']:7.3f} "
                      f"V_spk={r['V_spk']:7.4f} V_att={r['V_att']:7.4f} "
                      f"finite-A component={r['finite_A_speaker_component_width_pts']:6.3f} "
                      f"vs measured={r['measured_width_pts_A110']:6.3f}", flush=True)

    mod = [v for v in results["pairs"].values() if v["block"] == "within-modern"]
    base = [v for v in results["pairs"].values() if v["block"] == "within-baseline"]
    results["summary"] = {
        "speaker_fraction_of_two_marginal_components_within_modern": [
            round(min(v["speaker_fraction_of_two_marginal_components"] for v in mod), 3),
            round(max(v["speaker_fraction_of_two_marginal_components"] for v in mod), 3)],
        "speaker_fraction_of_two_marginal_components_within_baseline": [
            round(min(v["speaker_fraction_of_two_marginal_components"] for v in base), 3),
            round(max(v["speaker_fraction_of_two_marginal_components"] for v in base), 3)],
    }
    print("\nsummary:", json.dumps(results["summary"], indent=1), flush=True)
    out = derived / "results_floor.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
