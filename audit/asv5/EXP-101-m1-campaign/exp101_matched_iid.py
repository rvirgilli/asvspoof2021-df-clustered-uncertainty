"""Matched trial-i.i.d. versus speaker-by-attack sensitivity diagnostic.

Both arms recompute the same non-interpolated weighted EER threshold in every
replicate and use the same all-28-pair sup-t construction.  The result is a
fixed-data perturbation comparison, not population inference; see
MATCHED-IID-DIAGNOSTIC.md.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from exp101_selection import clustered_eer_replicates, load_21df
from m1_campaign import DF_SCORES, KEY, plain_eer, weighted_eer


B = 5000
SEED = 2026081604
HERE = Path(__file__).resolve().parent
PLAN = HERE / "MATCHED-IID-DIAGNOSTIC.md"
OUT = HERE / "results_matched_iid.json"
BASELINES = ("RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trial_iid_replicates(
    rng: np.random.Generator,
    scores: dict[str, np.ndarray],
    labels: np.ndarray,
    names: list[str],
) -> np.ndarray:
    """Class-stratified trial multinomial perturbations with threshold refits."""

    n = len(labels)
    bona = np.flatnonzero(labels == 1)
    spoof = np.flatnonzero(labels == 0)
    if not len(bona) or not len(spoof):
        raise ValueError("both classes are required")
    orders = {name: np.argsort(scores[name]) for name in names}
    out = np.empty((B, len(names)), dtype=np.float64)
    for replicate in range(B):
        weights = np.zeros(n, dtype=np.float64)
        np.add.at(weights, rng.choice(bona, size=len(bona), replace=True), 1.0)
        np.add.at(weights, rng.choice(spoof, size=len(spoof), replace=True), 1.0)
        if weights[bona].sum() != len(bona) or weights[spoof].sum() != len(spoof):
            raise AssertionError("class-stratified multinomial totals changed")
        for system, name in enumerate(names):
            out[replicate, system] = 100.0 * weighted_eer(
                orders[name], labels, weights
            )
    return out


def summarize(
    replicates: np.ndarray,
    point: np.ndarray,
    names: list[str],
) -> dict[str, object]:
    pairs = [(a, b) for index, a in enumerate(names) for b in names[index + 1 :]]
    deltas = np.column_stack(
        [replicates[:, names.index(a)] - replicates[:, names.index(b)] for a, b in pairs]
    )
    hats = np.asarray(
        [point[names.index(a)] - point[names.index(b)] for a, b in pairs]
    )
    sd = deltas.std(axis=0, ddof=1)
    if np.any(~np.isfinite(sd)) or np.any(sd <= 0):
        raise AssertionError("nonpositive or nonfinite pairwise bootstrap SD")
    centered = np.abs(deltas - deltas.mean(axis=0)) / sd
    q = float(np.percentile(centered.max(axis=1), 95.0))
    result_pairs: dict[str, object] = {}
    resolved_all = 0
    resolved_baselines = 0
    for index, (a, b) in enumerate(pairs):
        pointwise = np.percentile(deltas[:, index], [2.5, 97.5])
        simultaneous = np.asarray([hats[index] - q * sd[index], hats[index] + q * sd[index]])
        resolved = bool(not (simultaneous[0] <= 0.0 <= simultaneous[1]))
        is_baseline = a in BASELINES and b in BASELINES
        resolved_all += int(resolved)
        resolved_baselines += int(resolved and is_baseline)
        result_pairs[f"{a} vs {b}"] = {
            "delta_eer_pts": round(float(hats[index]), 6),
            "sd_pts": round(float(sd[index]), 6),
            "pointwise_percentile": [round(float(x), 6) for x in pointwise],
            "simultaneous": [round(float(x), 6) for x in simultaneous],
            "resolved_simultaneous": resolved,
            "organizer_baseline_pair": is_baseline,
        }
    return {
        "supt_critical_value": round(q, 6),
        "n_resolved_all_28": resolved_all,
        "n_resolved_organizer_6": resolved_baselines,
        "pairs": result_pairs,
    }


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite existing diagnostic: {OUT}")
    scores, labels, spk_idx, att_idx = load_21df()
    names = sorted(scores, key=lambda name: plain_eer(scores[name], labels))
    if len(names) != 8 or len(labels) != 533_928:
        raise AssertionError("unexpected 21DF system or trial count")
    point = np.asarray([100.0 * plain_eer(scores[name], labels) for name in names])
    ones = np.ones(len(labels), dtype=np.float64)
    for index, name in enumerate(names):
        exact = 100.0 * weighted_eer(
            np.argsort(scores[name]), labels, ones
        )
        if not np.isclose(exact, point[index], rtol=0.0, atol=1e-12):
            raise AssertionError(f"plain/weighted EER mismatch for {name}")

    iid_rng, clustered_rng = [
        np.random.default_rng(child)
        for child in np.random.SeedSequence(SEED).spawn(2)
    ]
    iid = trial_iid_replicates(iid_rng, scores, labels, names)
    clustered = clustered_eer_replicates(
        clustered_rng, scores, labels, spk_idx, att_idx, names
    )
    iid_summary = summarize(iid, point, names)
    clustered_summary = summarize(clustered, point, names)

    previous = json.loads((HERE / "results_selection.json").read_text())["21df"]
    previous_labels = {
        key: bool(value["resolved_simultaneous"])
        for key, value in previous["pairs"].items()
    }
    current_labels = {
        key: bool(value["resolved_simultaneous"])
        for key, value in clustered_summary["pairs"].items()
    }
    if current_labels != previous_labels:
        differing = sorted(
            key for key in current_labels if current_labels[key] != previous_labels.get(key)
        )
        raise AssertionError(f"clustered labels differ from saved selection: {differing}")

    width_ratios: dict[str, float] = {}
    for key, iid_pair in iid_summary["pairs"].items():
        clustered_pair = clustered_summary["pairs"][key]
        iid_width = iid_pair["simultaneous"][1] - iid_pair["simultaneous"][0]
        clustered_width = clustered_pair["simultaneous"][1] - clustered_pair["simultaneous"][0]
        width_ratios[key] = round(float(clustered_width / iid_width), 6)

    payload = {
        "status": "post-audit descriptive diagnostic; not population inference",
        "question": "effect of perturbation unit with identical EER threshold refit and all-pair sup-t construction",
        "B": B,
        "seed": SEED,
        "systems": names,
        "n_trials": int(len(labels)),
        "n_speakers": int(spk_idx.max() + 1),
        "n_attacks": int(len(np.unique(att_idx[labels == 0]))),
        "threshold_rule": "same non-interpolated position-wise weighted_eer recomputed in every replicate; separate tie-boundary audit changes reported pair deltas <0.001 point",
        "iid": iid_summary,
        "speaker_attack": clustered_summary,
        "clustered_over_iid_simultaneous_width_ratio": width_ratios,
        "saved_clustered_labels_reproduced": True,
        "sha256": {
            "plan": sha256(PLAN),
            "script": sha256(Path(__file__)),
            "protocol_key": sha256(KEY),
            "score_files": {name: sha256(DF_SCORES[name]) for name in names},
            "results_selection": sha256(HERE / "results_selection.json"),
        },
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        "matched diagnostic:",
        f"iid organizer={iid_summary['n_resolved_organizer_6']}/6",
        f"clustered organizer={clustered_summary['n_resolved_organizer_6']}/6",
        f"iid all={iid_summary['n_resolved_all_28']}/28",
        f"clustered all={clustered_summary['n_resolved_all_28']}/28",
    )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
