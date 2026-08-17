"""Bind the current M1 manuscript to its scientific artifacts.

The checker follows the paper's post-audit object: fixed-data procedure
sensitivity.  It intentionally does not require retired MDE, finite-A,
population-confidence or pairwise-floored exact-cell claims.

Run from the repository root:

    uv run --frozen python code/check_numbers.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DERIVED = ROOT / "derived"
PLANS = ROOT / "plans"
PAPER = ROOT / "paper"
AUDIT_DIR = ROOT / "audit"
TEX_RAW = (PAPER / "main.tex").read_text()
TEX = re.sub(r"(?m)^%.*$", "", TEX_RAW).replace("$", "").replace("{,}", ",")
FAILURES: list[str] = []


def load(path: Path) -> object:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    FAILURES.append(message)


def require(text: str, why: str) -> None:
    if text not in TEX and text not in TEX_RAW:
        fail(f"PRESENT missing {text!r} — {why}")


def require_re(pattern: str, why: str) -> None:
    if not re.search(pattern, TEX, re.S | re.I):
        fail(f"PRESENT no match for {pattern!r} — {why}")


def forbid(pattern: str, why: str) -> None:
    if re.search(pattern, TEX, re.S | re.I):
        fail(f"RETIRED {pattern!r} reappeared — {why}")


def require_number(literal: str, actual: float | int, nd: int | None, label: str) -> None:
    rendered = str(actual) if nd is None else f"{float(actual):.{nd}f}"
    if literal.startswith(".") and rendered.startswith("0."):
        rendered = rendered[1:]
    if rendered != literal:
        fail(f"VALUE {label}: expected paper literal {literal}, artifact renders {rendered}")
    if not re.search(r"(?<![\d.])" + re.escape(literal) + r"(?![\d])", TEX):
        fail(f"VALUE {label}: {literal} absent from main.tex")


matched = load(DERIVED / "results_matched_iid.json")
matched_prov = load(DERIVED / "results_matched_iid.provenance.json")
selection = load(DERIVED / "results_selection.json")
organizer = load(DERIVED / "results_organizer_test.json")
source = load(DERIVED / "results_source.json")
arena = load(DERIVED / "results_arena.json")
multiway = load(DERIVED / "results_multiway_real.json")
coherent = load(DERIVED / "results_coherent_jackknife.json")
coherent_prov = load(DERIVED / "provenance_coherent_jackknife.json")
coverage = load(DERIVED / "results_coverage_interaction_recalibrated.json")
coverage_original = load(DERIVED / "results_coverage_interaction.json")
coverage_diag = load(DERIVED / "results_coverage_diagnostics.json")
coverage_verified = load(DERIVED / "results_exp105_verified.json")
incidence = load(DERIVED / "incidence_strata.json")
composition = load(DERIVED / "results_composition.json")
composition_verified = load(DERIVED / "verification_composition.json")
composition_v2 = load(DERIVED / "secondary_v2_results.json")
composition_v2_verified = load(DERIVED / "secondary_v2_verification.json")
audit = load(AUDIT_DIR / "audit.json")


# Reader-facing audit package must be the same scientific state checked below.
for key in ("matched_perturbation", "coherent_marginal_sum", "coverage_closure",
            "composition_sensitivity", "asv5_descriptive_replication"):
    if key not in audit:
        fail(f"AUDIT package missing current key {key}")
if audit["matched_perturbation"]["artifact_sha256"] != sha256(
        DERIVED / "results_matched_iid.json"):
    fail("AUDIT matched-perturbation hash is stale")
if audit["matched_perturbation"]["result"] != matched:
    fail("AUDIT matched-perturbation payload differs from live artifact")
if audit["coherent_marginal_sum"]["artifact_sha256"] != sha256(
        DERIVED / "results_coherent_jackknife.json"):
    fail("AUDIT coherent-marginal-sum hash is stale")
if audit["coherent_marginal_sum"]["result"] != coherent:
    fail("AUDIT coherent-marginal-sum payload differs from live artifact")
if (audit["coverage_closure"]["status_under_preregistered_reading_rule"]
        != coverage_verified["status_under_preregistered_reading_rule"]
        or audit["coverage_closure"]["confirmed_estimators"]
        != coverage_verified["confirmed_estimators"]):
    fail("AUDIT coverage closure differs from independently verified reading")
audit_comp = audit["composition_sensitivity"]
if (audit_comp["pair_multiverse"] != composition["pair_multiverse"]
        or audit_comp["primary_verification"] != composition_verified
        or audit_comp["constructive_v2"]["verification"] != composition_v2_verified):
    fail("AUDIT composition payload differs from live verified artifacts")
if len(audit_comp["policy_order"]) != 12:
    fail("AUDIT composition policy contract is incomplete")

audit_asv5 = audit["asv5_descriptive_replication"]
asv5 = audit_asv5["result"]
if audit_asv5["independent_execution_audit"] != {
        "verdict": "PASS",
        "report_sha256": sha256(AUDIT_DIR / "asv5/EXECUTION-AUDIT.md"),
        "inputs_rehashed": 698,
        "input_divergences": 0,
        "independent_recomputation": True,
}:
    fail("AUDIT ASV5 independent execution-audit record is stale")
if asv5["scientific_role"] != (
        "fixed-roster descriptive perturbation sensitivity; not population inference"):
    fail("STATUS ASV5 result lost its descriptive/non-population guard")
if any(asv5["interpretation_boundary"].values()):
    fail("STATUS ASV5 result unexpectedly authorizes a population interpretation")
if asv5["run_contract"]["sha256"] != audit_asv5["run_contract_sha256"]:
    fail("HASH ASV5 result and packaged run contract differ")

asv5_cmp = asv5["comparison"]
if asv5_cmp["registered_descriptive_summaries"] != {
        "A_iid_exclusion_absent_under_speaker_attack": True,
        "B_median_width_ratio_at_least_2": True,
        "n_true": 2,
}:
    fail("BRANCH ASV5 A=1/B=1 no longer holds")
if asv5_cmp["iid_zero_exclusions_absent_under_primary"] != [
        "SSL-AASIST vs XLS-R+SLS"]:
    fail("VALUE ASV5 changed zero-exclusion pair changed")

asv5_structure = {
    "n_trials": 680774,
    "n_target": 367,
    "n_non_target": 370,
    "n_attacks": 16,
}
if any(audit_asv5["run_contract_structure"][key] != value
       for key, value in asv5_structure.items()):
    fail("VALUE ASV5 run-contract structure changed")
for literal in ("680,774", "367", "370", "16"):
    require(literal, "ASV5 roster structure must remain visible")

asv5_pair = asv5["arms"]
iid_band = asv5_pair["trial_iid"]["pairs"]["SSL-AASIST vs XLS-R+SLS"][
    "simultaneous_numeric_band"]
sa_band = asv5_pair["speaker_attack"]["pairs"]["SSL-AASIST vs XLS-R+SLS"][
    "simultaneous_numeric_band"]
for literal, value in (("-2.657", iid_band[0]), ("-2.378", iid_band[1]),
                       ("-6.274", sa_band[0]), ("1.238", sa_band[1])):
    require_number(literal, value, 3, f"ASV5 band endpoint {literal}")
ratios = list(asv5_cmp["primary_over_iid_simultaneous_width_ratio"].values())
for literal, value in (("11.23", min(ratios)), ("35.90", max(ratios)),
                       ("27.27", asv5_cmp["median_primary_over_iid_width_ratio"])):
    require_number(literal, value, 2, f"ASV5 width ratio {literal}")
focal_ratio = asv5_cmp["primary_over_iid_simultaneous_width_ratio"][
    "SSL-AASIST vs XLS-R+SLS"]
require_number("26.92", focal_ratio, 2, "ASV5 focal-pair width ratio")
for system, literal in (("SSL-AASIST", "16.25"), ("AASIST", "35.53"),
                        ("XLS-R+SLS", "18.76"), ("XLSR-Mamba", "14.40")):
    require_number(literal, asv5["pooled_fixed_roster_eer_percent"][system], 2,
                   f"ASV5 {system} EER")
require("External family-level check", "external result scope")
require("not pair-level replication", "ASV5 cross-generation scope")
require("acquisition-law gate is NO-GO", "ASV5 acquisition boundary")
require("legacy SSL-AASIST/AASIST NPZ snapshots", "legacy score provenance limit")
require("not population confidence or significance", "ASV5 boundary must be explicit")
forbid(r"two-generation replication|two-generation procedure|replicate across benchmark",
       "ASV5 supports only a family-level external sensitivity check")


# 1. Matched perturbation-unit diagnostic.
if matched["status"] != "post-audit descriptive diagnostic; not population inference":
    fail("STATUS matched diagnostic lost its descriptive/non-population guard")
if (matched["B"], matched["seed"]) != (5000, 2026081604):
    fail("CONTRACT matched diagnostic B/seed changed")
if not matched["saved_clustered_labels_reproduced"]:
    fail("GATE matched diagnostic no longer reproduces saved clustered labels")
expected_counts = {
    "iid": (5, 26),
    "speaker_attack": (0, 18),
}
for arm, (organizer_count, all_count) in expected_counts.items():
    row = matched[arm]
    got = (row["n_resolved_organizer_6"], row["n_resolved_all_28"])
    if got != (organizer_count, all_count):
        fail(f"VALUE matched {arm} counts {got} != {(organizer_count, all_count)}")
for literal in ("5/6", "0/6", "26/28", "18/28"):
    require(literal, "matched all-pair result must be visible")
require("threshold in every replicate", "matched threshold refit closes the reviewer confound")
require("Thus threshold treatment does not explain the change", "causal attribution is bounded")

# Embedded and sidecar provenance, including imported implementations.
embedded_paths = {
    "plan": PLANS / "MATCHED-IID-DIAGNOSTIC.md",
    "results_selection": DERIVED / "results_selection.json",
}
for key, path in embedded_paths.items():
    if matched["sha256"][key] != sha256(path):
        fail(f"HASH matched embedded {key} does not match {path.name}")
if matched["sha256"]["script"] != matched_prov["sha256"]["exp101_matched_iid.py"]:
    fail("HASH matched historical script identity differs between result and sidecar")
for name, path in {
    "MATCHED-IID-DIAGNOSTIC.md": PLANS / "MATCHED-IID-DIAGNOSTIC.md",
    "results_matched_iid.json": DERIVED / "results_matched_iid.json",
}.items():
    if sha256(path) != matched_prov["sha256"][name]:
        fail(f"HASH matched canonical artifact mismatch: {name}")
for name, digest in matched_prov["released_path_adapted_sha256"].items():
    if sha256(HERE / name) != digest:
        fail(f"HASH matched released path-adapted code mismatch: {name}")


# 2. Coherent marginal-sum diagnostic.
if coherent["status"] != "post-audit descriptive diagnostic; no population or coverage claim":
    fail("STATUS coherent diagnostic lost its interpretation guard")
if coherent["organizer_baseline_resolved"] != {
    "coherent_marginal_sum": 0,
    "product_bootstrap": 0,
    "old_floored_exact_cell": 0,
}:
    fail("VALUE coherent organizer counts changed")
if coherent["all_28_resolved_coherent_marginal_sum"] != 18:
    fail("VALUE coherent all-28 count changed")
if min(coherent["minimum_eigenvalues"].values()) <= 0:
    fail("PSD coherent covariance/dominance no longer has positive minimum eigenvalues")
for key, path in {
    "plan": PLANS / "COHERENT-JACKKNIFE-DIAGNOSTIC.md",
    "results_multiway_real": DERIVED / "results_multiway_real.json",
}.items():
    if coherent["sha256"][key] != sha256(path):
        fail(f"HASH coherent {key} mismatch")
if coherent["sha256"]["script"] != coherent_prov["historical_campaign_sha256"]["coherent_jackknife.py"]:
    fail("HASH coherent historical script identity differs between result and sidecar")
for name, digest in coherent_prov["released_path_adapted_sha256"].items():
    if sha256(HERE / name) != digest:
        fail(f"HASH coherent released path-adapted code mismatch: {name}")
for name, digest in coherent_prov["canonical_artifact_sha256"].items():
    path = PLANS / name if name.endswith(".md") else DERIVED / name
    if sha256(path) != digest:
        fail(f"HASH coherent canonical artifact mismatch: {name}")
require_number("2.878", coherent["q95"], 3, "coherent q95")
wide = coherent["pairs"]["RawNet2 vs CQCC-GMM"]["simultaneous"]
require_number("-8.76", wide[0], 2, "coherent widest lower")
require_number("2.40", wide[1], 2, "coherent widest upper")
require_re(r"same .*Sigma_\+.* supplies every pair SE", "one PSD covariance must supply SEs and max-t")
require("retains the cell overlap", "marginal-sum double counting must be disclosed")
require("not an exact multiway estimator or coverage claim", "coherent diagnostic scope")


# 3. Historical reconstruction and primary product output.
org_wide = organizer["pairs"]["B04 vs B01"]
require_number("3.18", abs(org_wide["delta_eer_pts"]), 2, "widest organizer gap")
require_number("-9.27", org_wide["clustered_ci_simultaneous"][0], 2,
               "product widest lower")
require_number("2.91", org_wide["clustered_ci_simultaneous"][1], 2,
               "product widest upper")
require("reconstruct both variants", "five positive labels are reconstructions")
require("no cell-level agreement", "published greyscale cells are not claimed")
require("sixth has", "the non-zero-excluding sixth reconstruction remains explicit")


# 4. Coverage closure and its adverse reading.
if coverage_verified["status_under_preregistered_reading_rule"] != "refuted":
    fail("STATUS EXP-105 no longer Refuted under its frozen rule")
if coverage_verified["confirmed_estimators"]:
    fail("STATUS EXP-105 unexpectedly confirms an estimator")
if (coverage_original["R"], len(coverage_original["grid"]), coverage_original["seed"]) != (
    1000,
    48,
    20260824,
):
    fail("CONTRACT EXP-105 R/grid/seed changed")
if any(row["product"]["B"] != 500 for row in coverage_original["grid"]):
    fail("CONTRACT EXP-105 product B changed")
grid = coverage["grid"]
organizer_rows = [row for row in grid if row["spec"]["regime"] == "organizer"]
low_rows = [row for row in grid if row["spec"]["regime"] == "low_eer"]
checks = (
    (".928", min(row["coverage"]["raw"]["coverage"] for row in organizer_rows)),
    (".957", max(row["coverage"]["raw"]["coverage"] for row in organizer_rows)),
    (".946", min(row["coverage"]["product"]["coverage"] for row in organizer_rows)),
    (".968", max(row["coverage"]["product"]["coverage"] for row in organizer_rows)),
    (".845", min(row["coverage"]["raw"]["coverage"] for row in low_rows)),
    (".855", min(row["coverage"]["product"]["coverage"] for row in low_rows)),
)
for literal, value in checks:
    require_number(literal, value, 3, f"coverage {literal}")
cell26 = grid[26]
for method, literal in (("raw", ".879"), ("floor", ".880"), ("product", ".883")):
    require_number(literal, cell26["coverage"][method]["coverage"], 3,
                   f"low-EER cell26 {method}")
all_below = sum(
    all(row["coverage"][method]["coverage"] < 0.90
        for method in ("raw", "floor", "product"))
    for row in low_rows
)
if all_below != 11:
    fail(f"VALUE low-EER all-below count {all_below} != 11")
require("11 of 24", "joint low-EER failure count")
oracle_min = coverage_diag["low_eer_minimum_coverage"]["oracle_sd_normal"]
require_number(".944", oracle_min, 3, "oracle-SD minimum")
require("reading rule is therefore Refuted", "adverse result must remain explicit")
require("not the DGP as a model of 21DF", "coverage cannot validate acquisition")


# 5. Incidence and provenance composition.
global_inc = incidence["global"]
if (global_inc["n_observed_within_stratum_cells"],
    global_inc["n_within_stratum_cartesian_cells"]) != (1062, 1068):
    fail("VALUE stratified occupancy changed")
shares = global_inc["spoof_stratum_trial_mass_shares"]
vcc_share = 1.0 - shares["asvspoof"]
require_number("85.77", 100 * vcc_share, 2, "VCC spoof-trial share")
speaker_counts = sorted(row["n_speakers"] for row in incidence["spoof_strata"].values())
if speaker_counts != [4, 4, 4, 6, 48]:
    fail(f"VALUE source/task speaker counts changed: {speaker_counts}")
require("4/4/4/6", "dominant sparse blocks must be visible")

loco = source["leave_one_corpus_out"]
flips = loco["verdict_flips_vs_full_data"]
gained = {row["pair"] for row in flips if not row["full_data"] and row["refit"]}
lost = {row["pair"] for row in flips if row["full_data"] and not row["refit"]}
expected_gained = {
    "RawNet2 vs CQCC-GMM",
    "LFCC-LCNN vs LFCC-GMM",
    "LFCC-LCNN vs CQCC-GMM",
}
if gained != expected_gained or len(lost) != 2:
    fail(f"VALUE LOCO flips changed: gained={gained}, lost={lost}")
cross_flips = [
    row for row in flips
    if (row["pair"].split(" vs ")[0] in {"XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"})
    != (row["pair"].split(" vs ")[1] in {"XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"})
]
if cross_flips:
    fail("VALUE a cross-generation label now flips under source deletion")
for pair in expected_gained:
    require(pair.replace(" vs ", "--"), "all three gained baseline pairs must be named")
require_re(r"(?:all |[Tt]he )16 cross-generation gaps", "stable cross-generation block must be bounded")
require("not composition-robust", "0/6 provenance dependence belongs with the headline")


# 6. Composition-policy sensitivity and constructive witnesses.
if not composition_verified["passed"] or not composition_verified["independent_implementation"]:
    fail("GATE EXP-108 primary result lacks independent verification")
if composition_verified["result_sha256"] != sha256(DERIVED / "results_composition.json"):
    fail("HASH EXP-108 primary result differs from independently verified file")

blocks = composition["pair_blocks"]
multiverse = composition["pair_multiverse"]
within_pairs = [pair for pair, block in blocks.items() if block != "cross_generation"]
cross_pairs = [pair for pair, block in blocks.items() if block == "cross_generation"]
within_changes = sum(multiverse[pair]["registered_policy_sign_change"] for pair in within_pairs)
cross_changes = sum(multiverse[pair]["registered_policy_sign_change"] for pair in cross_pairs)
if (len(within_pairs), within_changes, len(cross_pairs), cross_changes) != (12, 6, 16, 0):
    fail("VALUE EXP-108 registered-policy block counts changed")
for literal in ("6/12", "0/16"):
    require(literal, "registered composition-policy asymmetry must be visible")

if composition_v2["changes_primary_classification"]:
    fail("STATUS post-failure constructive search now changes the frozen primary class")
if not (composition_v2_verified["passed"]
        and composition_v2_verified["independent_three_backend_reconstruction"]):
    fail("GATE EXP-108 secondary v2 lacks three-backend independent verification")
if composition_v2_verified["results_sha256"] != sha256(DERIVED / "secondary_v2_results.json"):
    fail("HASH EXP-108 secondary v2 result differs from independently verified file")
for key, expected in {
    "n_accepted_witness_directions_verified": 729,
    "n_pairs_with_verified_r_TV_upper_bound": 12,
    "n_pairs_with_verified_r_TV_le_0.10": 5,
}.items():
    if composition_v2_verified[key] != expected:
        fail(f"VALUE EXP-108 secondary v2 {key} changed")
require("729", "accepted constructive directions must be reported")
require("five at", "small-shift constructive witness count must be reported")
best_tv = composition_v2_verified["best_verified_r_TV_by_pair"][
    "XLSR-Mamba vs XLS-R+SLS"
]
require_number(".010218", best_tv, 6, "smallest verified constructive rTV bound")
require("post-failure", "secondary chronology must be disclosed")
require("not a global minimum", "constructive upper bounds cannot become safety radii")
require("search outcome rather than proof", "absence of cross-generation witness is scoped")


# 7. Arena and measured width layer.
for literal, value, nd, label in (
    ("52", arena["schemes"]["iid"]["n_resolved_simultaneous"], None, "Arena iid count"),
    ("38", arena["schemes"]["clustered"]["n_resolved_simultaneous"], None,
     "Arena clustered count"),
    ("8.45", arena["median_width_ratio"], 2, "Arena median width ratio"),
    ("40.67", arena["cross_layer_sensitivity"]["RawNet2-Arena vs RawNet2"]["arena_eer"],
     2, "Arena RawNet2 EER"),
    ("22.38", arena["cross_layer_sensitivity"]["RawNet2-Arena vs RawNet2"]["primary_eer"],
     2, "primary RawNet2 EER"),
    ("0.36", arena["cross_layer_sensitivity"]["RawNet2-Arena vs RawNet2"]["score_pearson"],
     2, "cross-layer correlation"),
):
    require_number(literal, value, nd, label)
require("not coverage-validated Arena confidence claims", "Arena outputs remain descriptive")

matched_width_ratios = sorted(
    (
        matched["speaker_attack"]["pairs"][pair]["simultaneous"][1]
        - matched["speaker_attack"]["pairs"][pair]["simultaneous"][0]
    )
    /
    (
        row["simultaneous"][1] - row["simultaneous"][0]
    )
    for pair, row in matched["iid"]["pairs"].items()
)
matched_width_median = (
    matched_width_ratios[len(matched_width_ratios) // 2 - 1]
    + matched_width_ratios[len(matched_width_ratios) // 2]
) / 2.0
for literal, value, label in (
    ("4.13", matched_width_ratios[0], "matched simultaneous width minimum"),
    ("11.36", matched_width_ratios[-1], "matched simultaneous width maximum"),
    ("8.14", matched_width_median, "matched simultaneous width median"),
):
    require_number(literal, value, 2, label)


# 8. Table 1: gaps, product half-widths and constructive TV bounds.
ssl = {"XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"}
short = {
    "XLSR-Mamba": "XLSR-Mamba",
    "XLS-R+SLS": "XLS-R+SLS",
    "XLSR-Conformer": "XLSR-Conf",
    "SSL-AASIST": "SSL-AAS",
    "RawNet2": "RawNet2",
    "LFCC-LCNN": "LFCC-LCNN",
    "LFCC-GMM": "LFCC-GMM",
    "CQCC-GMM": "CQCC-GMM",
}
order = list(short)
pairs = selection["21df"]["pairs"]
expected_rows: list[list[str]] = []
for index, a in enumerate(order):
    for b in order[index + 1:]:
        if (a in ssl) != (b in ssl):
            continue
        row = pairs.get(f"{a} vs {b}") or pairs[f"{b} vs {a}"]
        half = (row["ci_pointwise"][1] - row["ci_pointwise"][0]) / 2.0
        tv = composition_v2_verified["best_verified_r_TV_by_pair"].get(f"{a} vs {b}")
        if tv is None:
            tv = composition_v2_verified["best_verified_r_TV_by_pair"].get(f"{b} vs {a}")
        if tv is None:
            fail(f"TABLE no verified constructive TV upper bound for {a} vs {b}")
            tv = float("nan")
        expected_rows.append([
            short[a], short[b], f"{abs(row['delta_eer_pts']):.3f}",
            f"{half:.3f}", f"{tv:.3f}"
        ])
body = TEX_RAW[TEX_RAW.index("\\label{tab:pairs}"):TEX_RAW.index("\\end{tabular}")]
printed = [line for line in body.splitlines() if "&" in line and "\\\\" in line]
printed = [line for line in printed if not line.strip().startswith("pair")]
printed_rows = [[cell.strip() for cell in line.replace("\\\\", "").split("&")] for line in printed]
if printed_rows != expected_rows:
    fail(f"TABLE printed rows differ from artifact: printed={printed_rows}, expected={expected_rows}")
if "MDE" in body:
    fail("RETIRED table still contains MDE after its inferential target was withdrawn")


# 9. Scientific scope obligations and retired formulations.
for text, why in (
    ("fixed-data procedure sensitivity", "identified scientific object"),
    ("not corrected population inference", "abstract scope"),
    ("not an exact multiway estimator or coverage claim", "coherent covariance scope"),
    ("historical freeze has no independently verifiable public timestamp", "timestamp honesty"),
    ("zero-straddling output is sensitivity, not evidence of equality", "non-significance scope"),
    ("new independently sampled units", "only full repair for population inference"),
    ("speaker and attack incidence", "report units rather than trial count"),
):
    require(text, why)
require_re(r"no.{0,20}sampling uncertainty", "deterministic fixed benchmark")

for pattern, why in (
    (r"formal inference (?:is )?restricted to the (?:four )?organi[sz]er", "incidence audit withdrew it"),
    (r"validated (?:formal )?result is the organi[sz]er", "organizer output is composition-dependent"),
    (r"numerically robust result is the organi[sz]er", "three LOCO labels change"),
    (r"pairwise marginal-component adjustment.*full-family", "incoherent floor is retired"),
    (r"positive-semidefinite floor", "a scalar pair floor is not a PSD covariance repair"),
    (r"MDE_?\{?80", "MDE target was withdrawn"),
    (r"finite-\$?A\$? speaker component", "secondary unidentified target removed from paper"),
    (r"Then the practice stopped", "historical search is bounded, not a census"),
    (r"preregistered 48-cell", "historical plan has no public timestamp"),
):
    forbid(pattern, why)


# 10. Bibliography closure.
bib = (PAPER / "refs.bib").read_text()
bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
cited = {key.strip() for match in re.findall(r"\\cite\{([^}]*)\}", TEX) for key in match.split(",")}
for key in sorted(bib_keys - cited):
    fail(f"BIB {key!r} defined but uncited")
for key in sorted(cited - bib_keys):
    fail(f"BIB {key!r} cited but undefined")


if FAILURES:
    print(f"FAIL — {len(FAILURES)} problem(s):\n")
    for failure in FAILURES:
        print("  " + failure)
    sys.exit(1)
print("OK — scientific contract passes: matched perturbation, coherent covariance, "
      "coverage refusal, provenance and composition sensitivity, authenticated ASV5 "
      "family-level check, table and scope are artifact-bound.")
