#!/usr/bin/env python3
"""Independent verifier for EXP-108 secondary v2 constructive witnesses.

Imports neither search_witnesses_v2 nor analyze/build_contract.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SYSTEMS = (
    "XLSR-Mamba",
    "XLS-R+SLS",
    "XLSR-Conformer",
    "SSL-AASIST",
    "RawNet2",
    "LFCC-LCNN",
    "LFCC-GMM",
    "CQCC-GMM",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(value, dtype="<f8").tobytes()).hexdigest()


def close(left: float, right: float, tolerance: float = 1e-8) -> None:
    if abs(left - right) > tolerance:
        raise AssertionError(f"numeric mismatch {left} != {right}")


def read_metadata(path: Path, bona_groups, spoof_groups):
    rows = []
    phases = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        field = line.split()
        if len(field) < 10:
            raise AssertionError(f"short metadata line {line_number}")
        if field[1] in phases:
            raise AssertionError(f"duplicate metadata ID {field[1]}")
        phases[field[1]] = field[7]
        if field[7] != "eval":
            continue
        stratum = "asvspoof" if field[3] == "asvspoof" else f"{field[3]}/{field[9]}"
        rows.append((field[1], field[5], field[3], stratum))
    rows.sort()
    labels = np.asarray([1 if row[1] == "bonafide" else 0 for row in rows], dtype=np.int8)
    b_lookup = {group: index for index, group in enumerate(bona_groups)}
    s_lookup = {group: index for index, group in enumerate(spoof_groups)}
    bidx = np.asarray([b_lookup[row[2]] if row[1] == "bonafide" else -1 for row in rows])
    sidx = np.asarray([s_lookup[row[3]] if row[1] == "spoof" else -1 for row in rows])
    return rows, labels, bidx, sidx, phases


def load_scores(rows, phases, score_contract):
    ids = [row[0] for row in rows]
    wanted = set(ids)
    output = {}
    for system, entry in score_contract.items():
        path = Path(entry["path"])
        if sha(path) != entry["sha256"]:
            raise AssertionError(f"score hash drift {system}")
        mapping = {}
        for line in path.read_text().splitlines():
            field = line.split()
            if field[0] in mapping:
                raise AssertionError(f"duplicate score {system} {field[0]}")
            mapping[field[0]] = float(field[1])
        missing = wanted - set(mapping)
        extras = set(mapping) - wanted
        if missing or not extras <= set(phases):
            raise AssertionError(f"score roster mismatch {system}")
        if any(phases[utterance] == "eval" for utterance in extras):
            raise AssertionError(f"eval release-only ID {system}")
        output[system] = np.asarray([mapping[utterance] for utterance in ids])
    return output


class IndependentBackends:
    def __init__(self, scores, labels, bidx, sidx):
        self.labels = labels
        self.bidx = bidx
        self.sidx = sidx
        self.bt = np.bincount(bidx[labels == 1], minlength=3)
        self.st = np.bincount(sidx[labels == 0], minlength=5)
        self.default_order = np.argsort(scores)
        lab = labels[self.default_order]
        bo = bidx[self.default_order]
        so = sidx[self.default_order]
        self.bc = np.vstack(
            [np.cumsum(((lab == 1) & (bo == group)).astype(np.int32)) for group in range(3)]
        )
        self.sc = np.vstack(
            [np.cumsum(((lab == 0) & (so == group)).astype(np.int32)) for group in range(5)]
        )
        stable = np.argsort(scores, kind="stable")
        stable_scores = scores[stable]
        self.stable_order = stable
        self.tie_ends = np.r_[
            np.flatnonzero(stable_scores[1:] != stable_scores[:-1]), len(scores) - 1
        ]

    def weights(self, qb, qs):
        weight = np.empty(len(self.labels), dtype=np.float64)
        bona = self.labels == 1
        spoof = ~bona
        weight[bona] = qb[self.bidx[bona]] / self.bt[self.bidx[bona]]
        weight[spoof] = qs[self.sidx[spoof]] / self.st[self.sidx[spoof]]
        return weight

    @staticmethod
    def from_arrays(bona, spoof):
        frr = bona / bona[-1]
        far = 1 - spoof / spoof[-1]
        index = int(np.argmin(np.abs(frr - far)))
        return float((frr[index] + far[index]) / 2)

    def direct(self, qb, qs):
        weight = self.weights(qb, qs)[self.default_order]
        lab = self.labels[self.default_order]
        return self.from_arrays(np.cumsum(weight * lab), np.cumsum(weight * (1 - lab)))

    def tie_safe(self, qb, qs):
        weight = self.weights(qb, qs)[self.stable_order]
        lab = self.labels[self.stable_order]
        bona = np.cumsum(weight * lab)[self.tie_ends]
        spoof = np.cumsum(weight * (1 - lab))[self.tie_ends]
        return self.from_arrays(bona, spoof)

    def canonical(self, qb, qs):
        lo, hi = 0, self.bc.shape[1]

        def values(index):
            frr = float((self.bc[:, index] / self.bt) @ qb)
            far = 1 - float((self.sc[:, index] / self.st) @ qs)
            return frr - far, 0.5 * (frr + far)

        while lo < hi:
            middle = (lo + hi) // 2
            gap, _ = values(middle)
            if gap < 0:
                lo = middle + 1
            else:
                hi = middle
        upper = min(lo, self.bc.shape[1] - 1)
        candidates = [upper - 1, upper] if upper else [upper]
        selected = candidates[0]
        best_gap, best_eer = values(selected)
        for candidate in candidates[1:]:
            candidate_gap, candidate_eer = values(candidate)
            if abs(candidate_gap) < abs(best_gap):
                selected, best_gap, best_eer = candidate, candidate_gap, candidate_eer
        return float(best_eer)


def distance(qb, qs, pb, ps):
    tv = max(0.5 * np.abs(qb - pb).sum(), 0.5 * np.abs(qs - ps).sum())
    ratio = np.r_[qb / pb, qs / ps]
    odds = max(ratio.max(), (1 / ratio).max())
    return float(tv), float(odds)


def verify_consensus(witness, pair, empirical_sign, endpoint_qb, endpoint_qs, pb, ps, backends):
    if not witness.get("accepted"):
        return
    grid_index = int(witness["grid_index"])
    lam = grid_index / 10_000
    close(lam, witness["lambda"], 1e-15)
    qb = (1 - lam) * pb + lam * endpoint_qb
    qs = (1 - lam) * ps + lam * endpoint_qs
    if np.max(np.abs(qb - np.asarray(witness["q_bona"]))) > 1e-12:
        raise AssertionError("bona path identity mismatch")
    if np.max(np.abs(qs - np.asarray(witness["q_spoof"]))) > 1e-12:
        raise AssertionError("spoof path identity mismatch")
    left, right = pair
    deltas = {
        "count_canonical": 100 * (backends[left].canonical(qb, qs) - backends[right].canonical(qb, qs)),
        "direct_per_trial": 100 * (backends[left].direct(qb, qs) - backends[right].direct(qb, qs)),
        "tie_safe_threshold": 100 * (backends[left].tie_safe(qb, qs) - backends[right].tie_safe(qb, qs)),
    }
    for backend, value in deltas.items():
        close(value, witness["deltas"][backend])
        if int(np.sign(value)) == 0 or int(np.sign(value)) == empirical_sign:
            raise AssertionError(f"non-consensus accepted witness {left} vs {right} {backend}")
    tv, odds = distance(qb, qs, pb, ps)
    close(tv, witness["r_TV"], 1e-12)
    close(odds, witness["odds_factor"], 1e-10)
    if sha_array(np.r_[qb, qs]) != witness["group_mass_sha256_float64_le"]:
        raise AssertionError("group hash mismatch")
    if sha_array(backends[left].weights(qb, qs)) != witness["trial_mass_sha256_float64_le"]:
        raise AssertionError("trial hash mismatch")


def verify():
    result_path = HERE / "secondary_v2_results.json"
    result = json.loads(result_path.read_text())
    contract = json.loads((HERE / "secondary_v2_contract.json").read_text())
    if sha(HERE / "secondary_v2_contract.json") != result["preoutput_contract_sha256"]:
        raise AssertionError("contract hash mismatch")
    if sha(HERE / "results.json") != contract["primary_results_sha256"]:
        raise AssertionError("primary results changed")
    for filename, expected in contract["code"].items():
        if sha(HERE / filename) != expected:
            raise AssertionError(f"v2 code changed {filename}")

    metadata = Path(contract["metadata"]["path"])
    if sha(metadata) != contract["metadata"]["sha256"]:
        raise AssertionError("metadata hash drift")
    rows, labels, bidx, sidx, phases = read_metadata(
        metadata, result["bona_groups"], result["spoof_groups"]
    )
    scores = load_scores(rows, phases, contract["score_files"])
    backends = {
        system: IndependentBackends(scores[system], labels, bidx, sidx) for system in SYSTEMS
    }
    pb = np.asarray(result["empirical_bona_mass"])
    ps = np.asarray(result["empirical_spoof_mass"])

    accepted = 0
    best_tv = {}
    dual_tv = 0
    for pair_name, pair_result in result["pairs"].items():
        pair = tuple(pair_name.split(" vs "))
        empirical_sign = int(pair_result["empirical_sign"])
        for objective_name, objective in pair_result["objectives"].items():
            directions = objective["sobol"]["directions"]
            if len(directions) != objective["sobol"]["n_retained"]:
                raise AssertionError("retained Sobol count mismatch")
            accepted_directions = [item for item in directions if item["consensus"].get("accepted")]
            if len(accepted_directions) != objective["sobol"]["n_consensus_accepted"]:
                raise AssertionError("accepted Sobol count mismatch")
            for direction in accepted_directions:
                verify_consensus(
                    direction["consensus"],
                    pair,
                    empirical_sign,
                    np.asarray(direction["endpoint_q_bona"]),
                    np.asarray(direction["endpoint_q_spoof"]),
                    pb,
                    ps,
                    backends,
                )
                accepted += 1
            differential = objective["differential"]
            differential_accepted = differential.get("consensus", {}).get("accepted", False)
            if differential_accepted:
                verify_consensus(
                    differential["consensus"],
                    pair,
                    empirical_sign,
                    np.asarray(differential["endpoint_q_bona"]),
                    np.asarray(differential["endpoint_q_spoof"]),
                    pb,
                    ps,
                    backends,
                )
                accepted += 1
            if bool(objective["dual_search"]) != bool(accepted_directions and differential_accepted):
                raise AssertionError("dual-search summary mismatch")

            field = objective_name
            candidates = []
            for direction in accepted_directions:
                candidates.append(("sobol", direction["consensus"]))
            if differential_accepted:
                candidates.append(("differential", differential["consensus"]))
            expected_best = min(candidates, key=lambda item: item[1][field]) if candidates else None
            saved_best = objective["best_overall"]
            if expected_best is None:
                if saved_best is not None:
                    raise AssertionError("unexpected saved best")
            else:
                if saved_best["algorithm"] != expected_best[0]:
                    raise AssertionError("best algorithm mismatch")
                close(saved_best["witness"][field], expected_best[1][field], 1e-12)
        tv_best = pair_result["objectives"]["r_TV"]["best_overall"]
        best_tv[pair_name] = tv_best["witness"]["r_TV"] if tv_best else None
        if pair_result["objectives"]["r_TV"]["dual_search"]:
            dual_tv += 1

    return {
        "experiment": "EXP-108-secondary-v2-verification",
        "passed": True,
        "independent_three_backend_reconstruction": True,
        "results_sha256": sha(result_path),
        "n_accepted_witness_directions_verified": accepted,
        "n_pairs_with_verified_r_TV_upper_bound": sum(value is not None for value in best_tv.values()),
        "n_pairs_with_verified_r_TV_le_0.10": sum(
            value is not None and value <= 0.10 for value in best_tv.values()
        ),
        "n_pairs_with_dual_search_r_TV": dual_tv,
        "best_verified_r_TV_by_pair": best_tv,
    }


def main():
    try:
        output = verify()
    except Exception as error:
        output = {"passed": False, "error_type": type(error).__name__, "error": str(error)}
        (HERE / "secondary_v2_verification.json").write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n"
        )
        raise
    (HERE / "secondary_v2_verification.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    print(
        f"verified {output['n_accepted_witness_directions_verified']} accepted directions; "
        f"{output['n_pairs_with_verified_r_TV_upper_bound']} pairs have constructive bounds"
    )


if __name__ == "__main__":
    main()
