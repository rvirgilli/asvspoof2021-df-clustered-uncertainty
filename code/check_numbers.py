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
import math
import os
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DERIVED = ROOT / "derived"
PLANS = ROOT / "plans"
PAPER = ROOT / "paper"
AUDIT_DIR = ROOT / "audit"
EXP115 = ROOT / "exp115"
EXP116 = ROOT / "exp116"
EXP118 = ROOT / "exp118"
TEX_PATH = Path(os.environ.get("M1_TEX_PATH", PAPER / "main.tex"))
SUPPLEMENT_PATH = Path(os.environ.get(
    "M1_SUPPLEMENT_PATH", PAPER / "SUPPLEMENT.md"))
TEX_RAW = TEX_PATH.read_text()
TEX = re.sub(r"(?m)^%.*$", "", TEX_RAW).replace("$", "").replace("{,}", ",")
SUPPLEMENT_RAW = SUPPLEMENT_PATH.read_text()
REPORT_RAW = TEX_RAW + "\n" + SUPPLEMENT_RAW
REPORT = TEX + "\n" + SUPPLEMENT_RAW.replace("`", "")
FAILURES: list[str] = []


def load(path: Path) -> object:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scientific_view(value: object) -> object:
    """Remove path-layout provenance while preserving scientific payload values."""
    if isinstance(value, dict):
        return {
            key: scientific_view(item) for key, item in value.items()
            if key not in {"path", "input_provenance", "provenance"}
            and not key.endswith("sha256")
        }
    if isinstance(value, list):
        return [scientific_view(item) for item in value]
    return value


def fail(message: str) -> None:
    FAILURES.append(message)


def check_generated_figures() -> None:
    """Reject stale figures and a retired reader-facing label."""
    import shutil
    import subprocess
    generator = PAPER / "figures_m1.py"
    source = generator.read_text()
    if "results_matched_iid.json" not in source or "1.96 * se" in source:
        fail("FIGURE forest source does not use the matched simultaneous trial-i.i.d. artifact")
    figures = sorted((PAPER / "figs").glob("*.pdf"))
    if not figures:
        fail("FIGURE no generated figures found")
        return
    for figure in figures:
        if figure.stat().st_mtime < generator.stat().st_mtime:
            fail(f"FIGURE {figure.name} is older than figures_m1.py")
    if shutil.which("pdftotext"):
        for figure in figures:
            rendered = subprocess.run(
                ["pdftotext", str(figure), "-"], capture_output=True, text=True
            ).stdout
            for phrase in ("published i.i.d. interval", "trial-i.i.d. (reconstructed)",
                           "clustered (this work)"):
                if phrase in rendered:
                    fail(f"FIGURE {figure.name} still renders retired label {phrase!r}")
            if figure.name == "forest.pdf" and not all(phrase in rendered for phrase in (
                    "trial-i.i.d. simultaneous", "speaker-attack simultaneous")):
                fail("FIGURE forest.pdf does not identify both matched simultaneous arms")


def require(text: str, why: str) -> None:
    if text not in REPORT and text not in REPORT_RAW:
        fail(f"PRESENT missing {text!r} — {why}")


def require_re(pattern: str, why: str) -> None:
    if not re.search(pattern, REPORT, re.S | re.I):
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
    if not re.search(r"(?<![\d.])" + re.escape(literal) + r"(?![\d])", REPORT):
        fail(f"VALUE {label}: {literal} absent from paper or supplement")


obligation_doc = load(PAPER / "semantic_obligations.json")
if obligation_doc.get("schema") != "m1-semantic-obligations-v1":
    fail("OBLIGATION manifest schema is missing or unsupported")
obligation_ids: set[str] = set()
for obligation in obligation_doc.get("obligations", []):
    obligation_id = obligation["id"]
    if obligation_id in obligation_ids:
        fail(f"OBLIGATION duplicate id {obligation_id}")
    obligation_ids.add(obligation_id)
    count = TEX_RAW.count(obligation["match"])
    if count != 1:
        fail(f"OBLIGATION {obligation_id} expected exactly one occurrence, found {count}")


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
packaging = load(AUDIT_DIR / "PUBLIC-PACKAGING.json")
audit_exp111 = audit["composition_fixed_sampling_control"]
exp111 = audit_exp111["result"]
exp111_receipt = audit_exp111["run_receipt"]
exp111_closure = audit_exp111["archival_closure"]
exp111_verification = audit_exp111["portable_verification"]
exp111_independent = audit_exp111["independent_reproduction"]
audit_exp112 = audit["coverage_witnessed_replacement"]
exp112 = audit_exp112["result"]
exp112_receipt = audit_exp112["run_receipt"]
exp112_closure = audit_exp112["closure"]
exp112_addendum = audit_exp112["provenance_addendum"]
exp112_verification = audit_exp112["independent_verification"]
audit_exp114 = audit["spoofceleb_sampling_unit_confirmation"]
exp114 = audit_exp114["provenance_rerun_result"]
exp114_comparison = audit_exp114["provenance_rerun_comparison"]
exp114_receipt = audit_exp114["provenance_rerun_receipt"]
exp114_mamba = audit_exp114["mamba_score_comparison"]
exp114_independent = audit_exp114["independent_reproduction"]
exp115 = load(EXP115 / "RESULTS.json")
exp115_receipt = load(EXP115 / "RUN-RECEIPT.json")
exp115_independent = load(EXP115 / "independent/RESULT.json")

if packaging.get("schema") != "m1-public-audit-packaging-v1":
    fail("AUDIT public packaging receipt schema is missing")
if packaging.get("public") != {
        "bytes": (AUDIT_DIR / "audit.json").stat().st_size,
        "sha256": sha256(AUDIT_DIR / "audit.json"),
}:
    fail("AUDIT public packaging receipt does not bind audit.json")
if packaging.get("implementation", {}).get("sha256") != sha256(
        HERE / "make_public_audit.py"):
    fail("AUDIT public packaging receipt does not bind sanitizer implementation")


# Reader-facing audit package must be the same scientific state checked below.
for key in ("matched_perturbation", "coherent_marginal_sum", "coverage_closure",
            "composition_sensitivity", "composition_fixed_sampling_control",
            "coverage_witnessed_replacement",
            "spoofceleb_sampling_unit_confirmation", "spoofceleb_factor_decomposition",
            "asv5_descriptive_replication"):
    if key not in audit:
        fail(f"AUDIT package missing current key {key}")
if audit["matched_perturbation"]["artifact_sha256"] != sha256(
        DERIVED / "results_matched_iid.json"):
    fail("AUDIT matched-perturbation hash is stale")
if audit["matched_perturbation"]["result"] != matched:
    fail("AUDIT matched-perturbation payload differs from live artifact")
if scientific_view(audit["coherent_marginal_sum"]["result"]) != scientific_view(coherent):
    fail("AUDIT coherent-marginal-sum payload differs from live artifact")
if (audit["coverage_closure"]["status_under_preregistered_reading_rule"]
        != coverage_verified["status_under_preregistered_reading_rule"]
        or audit["coverage_closure"]["confirmed_estimators"]
        != coverage_verified["confirmed_estimators"]):
    fail("AUDIT coverage closure differs from independently verified reading")
audit_comp = audit["composition_sensitivity"]
if (scientific_view(audit_comp["pair_multiverse"])
        != scientific_view(composition["pair_multiverse"])
        or scientific_view(audit_comp["primary_verification"])
        != scientific_view(composition_verified)
        or scientific_view(audit_comp["constructive_v2"]["verification"])
        != scientific_view(composition_v2_verified)):
    fail("AUDIT composition payload differs from live verified artifacts")
if len(audit_comp["policy_order"]) != 12:
    fail("AUDIT composition policy contract is incomplete")

if audit_exp114["licensed_inputs_redistributed"]:
    fail("AUDIT EXP-114 must not redistribute licensed inputs")

audit_exp115 = audit["spoofceleb_factor_decomposition"]
if (audit_exp115["result"] != exp115
        or audit_exp115["run_receipt"] != exp115_receipt
        or audit_exp115["standalone_recomputation"] != exp115_independent):
    fail("AUDIT EXP-115 payload differs from released artifacts")
if audit_exp115["licensed_inputs_redistributed"]:
    fail("AUDIT EXP-115 must not redistribute licensed inputs")
for name, digest in audit_exp115["artifact_sha256"].items():
    if sha256(EXP115 / name) != digest:
        fail(f"AUDIT EXP-115 packaged hash is stale: {name}")

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
for literal in ("680,774",):
    require(literal, "ASV5 roster structure must remain visible")

asv5_pair = asv5["arms"]
iid_band = asv5_pair["trial_iid"]["pairs"]["SSL-AASIST vs XLS-R+SLS"][
    "simultaneous_numeric_band"]
sa_band = asv5_pair["speaker_attack"]["pairs"]["SSL-AASIST vs XLS-R+SLS"][
    "simultaneous_numeric_band"]
ratios = list(asv5_cmp["primary_over_iid_simultaneous_width_ratio"].values())
require_number("27.27", asv5_cmp["median_primary_over_iid_width_ratio"], 2,
               "ASV5 median width ratio")
focal_ratio = asv5_cmp["primary_over_iid_simultaneous_width_ratio"][
    "SSL-AASIST vs XLS-R+SLS"]
require("ASVspoof 5 check", "external result scope")
require("not a system-performance replication", "ASV5 external-check scope")
require("ASVspoof~5 SSL-AASIST and AASIST score files lack their originating run logs",
        "legacy score provenance limit")
require("not a system-performance replication or population claim",
        "ASV5 boundary must be explicit")
forbid(r"two-generation replication|two-generation procedure|replicate across benchmark",
       "ASV5 supports only a family-level external sensitivity check")


# 1. Matched perturbation-unit diagnostic.
if matched["status"] != "post-audit descriptive diagnostic; not population inference":
    fail("STATUS matched diagnostic lost its descriptive/non-population guard")
if (matched["B"], matched["seed"]) != (5000, 2026081604):
    fail("CONTRACT matched diagnostic B/seed changed")
require(f"5,000 replicates and seed {matched['seed']}", "printed seed must be the matched-run seed, not the campaign seed")
forbid(r"seed 20260817", "the campaign selection seed is not the seed of the printed bands")
saved_clustered = selection["21df"]["pairs"]
for pair, row in matched["speaker_attack"]["pairs"].items():
    if row["resolved_simultaneous"] != saved_clustered[pair]["resolved_simultaneous"]:
        fail(f"GATE matched diagnostic differs from saved clustered label for {pair}")
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
require("matched all-28-pair bootstrap refits the same weighted EER in every replicate",
        "matched threshold refit closes the reviewer confound")
require("neither threshold handling nor movement of these eight class-specific masses is necessary",
        "composition-control attribution is bounded")

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


# 1b. EXP-111 post-failure composition-fixed control, carried in the
# path-sanitized composite package and bound to its original artifact hashes.
if exp111["schema"] != "exp111-post-failure-composition-fixed-v2":
    fail("STATUS EXP-111 result is not the amended v2 schema")
if exp111["status"] != "post-failure robustness control; outcome known before Amendment 1":
    fail("STATUS EXP-111 lost its outcome-known/post-failure disclosure")
if (exp111["B"], exp111["seed"], exp111["family"]) != (
        1000, 20260824, "all 28 pairs, one 95% max-t critical value per arm"):
    fail("CONTRACT EXP-111 B/seed/family changed")
exp111_hashes = audit_exp111["artifact_sha256"]
if (exp111_receipt["result"]["sha256"] != exp111_hashes["results_v2.json"]
        or exp111_closure["archival_result"]["sha256"] != exp111_hashes["results_v2.json"]):
    fail("HASH EXP-111 receipt/closure does not bind the packaged result")
if exp111_closure["archival_run_receipt"]["sha256"] != exp111_hashes["RUN-RECEIPT-v2.json"]:
    fail("HASH EXP-111 closure does not bind the packaged receipt")
if exp111_closure["producer_commit"] != exp111_receipt["producer_git_head"]:
    fail("PROVENANCE EXP-111 closure and receipt name different producer commits")
if not (exp111_receipt["assertions_passed"] and exp111["assertions"]["passed"]
        and exp111_closure["producer_tree_clean_at_start"]
        and exp111_verification["checks"]["passed"]
        and exp111_verification["checks"]["receipt_input_hashes_match_canonical_files"]
        and exp111_closure["independent_closure"]["exact_reproduction"]
        and exp111_independent["comparison_to_author"]["exact_reproduction"]):
    fail("GATE EXP-111 archival/independent verification did not pass")
if exp111_closure["portable_verification"]["output_sha256"] != exp111_hashes[
        "independent/archival-verification.json"]:
    fail("HASH EXP-111 closure does not bind portable verification")
if exp111_closure["independent_closure"]["output_sha256"] != exp111_hashes[
        "independent/results-v2-clean-producer.json"]:
    fail("HASH EXP-111 closure does not bind independent result")

exp111_expected = {
    "A_trial_iid": (5, 26), "B_global_product": (0, 18),
    "C_conditioned_class_stratum_fixed": (0, 18),
    "CONTROL_total_only_normalisation": (0, 16),
}
for arm_name, expected in exp111_expected.items():
    arm = exp111["arms"][arm_name]
    pair_rows = arm["pairs"]
    organizer_rows = {
        pair: row for pair, row in pair_rows.items()
        if all(model in {"RawNet2", "LFCC-LCNN", "LFCC-GMM", "CQCC-GMM"}
               for model in pair.split(" vs "))
    }
    recomputed = (
        sum(row["simultaneous_excludes_zero"] for row in organizer_rows.values()),
        sum(row["simultaneous_excludes_zero"] for row in pair_rows.values()),
    )
    stored = (arm["excluding_zero_simultaneous_organizer_6"],
              arm["excluding_zero_simultaneous_all"])
    if len(pair_rows) != 28 or arm["n_all_pairs"] != 28 or recomputed != stored or stored != expected:
        fail(f"VALUE EXP-111 {arm_name}: recomputed={recomputed}, stored={stored}")
exp111_c = exp111["arms"]["C_conditioned_class_stratum_fixed"]
if exp111_c["tv"]["max_class"]["maximum"] > 1e-10:
    fail("CONTROL EXP-111 composition-fixed arm exceeds class-TV tolerance")
if exp111["arms"]["CONTROL_total_only_normalisation"]["tv"]["bona"]["median"] <= 0.02:
    fail("CONTROL EXP-111 negative control no longer detects composition movement")
vcc2018 = exp111_c["conditioned_draw_diagnostics"]["vcc2018"]
if (vcc2018["attempts"], vcc2018["rejected_attempts"],
        vcc2018["zero_support_reasons"]) != (1007, 7, {"spoof": 7}):
    fail("VALUE EXP-111 conditioning diagnostics changed")
require("designed after the main result and is a robustness check",
        "EXP-111 chronology and role must be visible")
require("(1,000 draws, seed 20260824)", "EXP-111 draw count and seed differ from the primary arms and must be stated")
require("redraws a replicate only when a class loses all support in a stratum (7 of 1,007 attempts, all VCC2018 spoof), and then rescales each source and stratum mass to its observed value",
        "EXP-111 composition control must state its zero-support rule and rejection count")
require("a robustness check, not prospective evidence",
        "EXP-111 cannot be relabelled as prospective or causal")


# 1c. EXP-114 prospectively frozen single-source confirmation and the later
# scorer-provenance reproduction.
if exp114["evidence_status"] != (
        "prospective confirmation attempt frozen before SpoofCeleb access, scoring, "
        "and detector outcomes"):
    fail("STATUS EXP-114 lost its pre-access prospective chronology")
if (exp114["n_trials"], exp114["n_speakers"], exp114["n_spoof_attacks"],
        exp114["B"], exp114["seed"]) != (91130, 40, 9, 5000, 20260829):
    fail("CONTRACT EXP-114 trial/cluster/B/seed structure changed")
exp114_counts = tuple(exp114[name]["simultaneous_excluding_zero"] for name in (
    "arm_a_trial_iid", "arm_b_global_product",
    "arm_c_single_source_composition_preserving"))
if exp114_counts != (6, 3, 3):
    fail(f"VALUE EXP-114 simultaneous counts {exp114_counts} != (6, 3, 3)")
for system, literal in (("aasist", "57.93"), ("sls", "24.51"),
                        ("ssl_aasist", "26.72"), ("xlsr_mamba", "27.58")):
    require_number(literal, exp114["point_eer_percent"][system], 2,
                   f"EXP-114 {system} point EER")
if not (exp114["guards"]["complete_crossed_grid"]
        and exp114["guards"]["b_c_bootstrap_arrays_identical"]
        and exp114["guards"]["b_c_summaries_identical"]
        and exp114["guards"]["b_c_max_abs_eer_difference"] == 0.0
        and exp114["guards"]["single_official_source"] == "TITW-VoxCeleb1"):
    fail("CONTROL EXP-114 single-source arm does not reproduce global arm")
if exp114["guards"]["source_tv"] != {
        "value": 0.0, "status": "zero_by_single-source_design",
        "scientific_evidence": False}:
    fail("CONTROL EXP-114 source-TV zero lost its by-construction boundary")
if exp114["registered_reading"]["n_sampling_unit_sensitive_pairs"] != 3:
    fail("BRANCH EXP-114 registered reading changed")
exp114_hashes = audit_exp114["artifact_sha256"]
if exp114_receipt["rerun_result"]["sha256"] != exp114_hashes[
        "PROVENANCE-RERUN-RESULTS.json"]:
    fail("HASH EXP-114 receipt does not bind rerun result")
if exp114_receipt["result_comparison"]["artifact"]["sha256"] != exp114_hashes[
        "PROVENANCE-RERUN-COMPARISON.json"]:
    fail("HASH EXP-114 receipt does not bind result comparison")
if exp114_receipt["xlsr_mamba_comparison"]["artifact"]["sha256"] != exp114_hashes[
        "independent/MAMBA-SCORE-COMPARISON.json"]:
    fail("HASH EXP-114 receipt does not bind Mamba comparison")
if exp114_receipt["independent_result"]["sha256"] != exp114_hashes[
        "independent/PROVENANCE-RERUN-RESULTS.json"]:
    fail("HASH EXP-114 receipt does not bind independent result")
if sorted(exp114_receipt["exact_score_reproductions"]) != ["aasist", "sls", "ssl_aasist"]:
    fail("VALUE EXP-114 exact score-reproduction set changed")
if not (exp114_receipt["scientific_payload_reproduced_with_difference"]
        and not exp114_receipt["scientific_payload_exactly_identical"]
        and exp114_comparison["registered_endpoint_identical"]
        and exp114_comparison["all_discrete_outputs_identical"]
        and exp114_independent["comparison_to_author"]["exact_endpoint_reproduction"]
        and exp114_receipt["independent_endpoint_reproduction_exact"]):
    fail("GATE EXP-114 endpoint/result reproduction did not pass")
if (exp114_mamba["classification"] != "reproduced-with-difference"
        or exp114_mamba["rows"] != 91130
        or exp114_mamba["delta"]["max_abs"] != 1.430511474609375e-06
        or exp114_mamba["eer"]["absolute_difference_points"] != 0.0):
    fail("VALUE EXP-114 Mamba numerical-difference summary changed")
require("91,130 evaluation trials", "EXP-114 complete evaluation size must remain visible")
require("single-source SpoofCeleb", "EXP-114 source/composition control must remain visible")
require("while official access was pending and released with its hash in the repository of Sec.~\\ref{sec:disc}, fixed",
        "EXP-114 prospective chronology must remain visible in field-facing language")
require("6/6", "EXP-114 trial-i.i.d. endpoint must remain visible")
require("3/6", "EXP-114 product/source endpoint must remain visible")
require("one source label, so between-source mass cannot move",
        "EXP-114 fixes source composition, not all factor multiplicities")
require("speaker and spoof-attack multiplicities",
        "EXP-114 must not overstate its composition control")
require("off-domain sensitivity check, not a comparison of competitive SpoofCeleb systems",
        "EXP-114 external-validity boundary must remain visible")
require("archived plan did not bind the scoring code",
        "EXP-114 original provenance gap must remain disclosed in field-facing language")
require("re-scoring from freshly cloned, commit-pinned detector repositories is reproducibility evidence only",
        "EXP-114 rerun chronology must remain visible")
require("three score files were byte-identical", "EXP-114 exact score reproduction count")
mamba_ceiling = math.ceil(exp114_mamba["delta"]["max_abs"] * 1e8) / 1e8
if mamba_ceiling != 1.44e-6:
    fail(f"VALUE EXP-114 Mamba conservative ceiling changed: {mamba_ceiling}")
require("1.44\\times10^{-6}", "EXP-114 Mamba maximum score delta ceiling")
require("every EER and separation indicator was unchanged",
        "EXP-114 post-result rerun did not change the scientific result")


# 1d. EXP-115 is a disclosed post-result decomposition of the known EXP-114
# endpoint, not a second prospective confirmation.
if (exp115["evidence_status"], exp115["B"], exp115["seed"], exp115["n_trials"],
        exp115["n_speakers"], exp115["n_spoof_attacks"]) != (
        "post-result mechanism diagnostic", 5000, 20260830, 91130, 40, 9):
    fail("CONTRACT EXP-115 status/B/seed/census changed")
if (exp115["arm_speaker_only"]["simultaneous_excluding_zero"],
        exp115["arm_attack_only"]["simultaneous_excluding_zero"]) != (5, 3):
    fail("VALUE EXP-115 factor-only endpoints changed")
exp115_attack_vector = {
    pair: row["simultaneous_excludes_zero"]
    for pair, row in exp115["arm_attack_only"]["pairs"].items()
}
exp114_joint_vector = {
    pair: row["simultaneous_excludes_zero"]
    for pair, row in exp114["arm_b_global_product"]["pairs"].items()
}
if exp115_attack_vector != exp114_joint_vector:
    fail("CONTROL EXP-115 attack-only verdict vector no longer reproduces joint product")
expected_decomposition = {
    "sls vs xlsr_mamba": {
        "attack_only_includes_zero": True,
        "classification": "attack_only_includes_zero",
        "speaker_only_includes_zero": False,
    },
    "ssl_aasist vs sls": {
        "attack_only_includes_zero": True,
        "classification": "attack_only_includes_zero",
        "speaker_only_includes_zero": False,
    },
    "ssl_aasist vs xlsr_mamba": {
        "attack_only_includes_zero": True,
        "classification": "both_one_factor_arms_include_zero",
        "speaker_only_includes_zero": True,
    },
}
if exp115["known_joint_sensitive_pair_decomposition"] != expected_decomposition:
    fail("BRANCH EXP-115 factor decomposition changed")
if not (exp115["guards"]["speaker_only_attack_multiplicity_fixed_at_one"]
        and exp115["guards"]["attack_only_speaker_multiplicity_fixed_at_one"]
        and exp115["guards"]["distinct_speaker_multiplicity_patterns_observed"] == 5000
        and exp115["guards"]["distinct_attack_multiplicity_patterns_observed"] == 3924):
    fail("GUARD EXP-115 factor-only construction changed")
for name in ("SPEAKER-ONLY-BOOTSTRAP.npy", "ATTACK-ONLY-BOOTSTRAP.npy"):
    if exp115_receipt["bindings"][name] != sha256(EXP115 / name):
        fail(f"HASH EXP-115 receipt does not bind {name}")
if exp115_receipt["bindings"]["RESULTS.json"] != sha256(EXP115 / "RESULTS.json"):
    fail("HASH EXP-115 receipt does not bind result")
if not (exp115_independent["speaker_array_exact"]
        and exp115_independent["attack_array_exact"]
        and exp115_independent["speaker_only_excluding_zero"] == 5
        and exp115_independent["attack_only_excluding_zero"] == 3):
    fail("REPRODUCTION EXP-115 standalone result changed")
require("After observing this result", "EXP-115 chronology must remain visible")
require("speaker-only and attack-only bootstraps separated 5/6 and 3/6",
        "EXP-115 factor-only endpoints must remain visible")
require("attack-only matched the PW indicator vector",
        "EXP-115 mechanism localization must remain visible")


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
require("draws 200,000 vectors", "one PSD covariance must supply SEs and max-t")
require("deliberately variance-inflating sensitivity analysis",
        "marginal-sum overlap must be disclosed in field-facing language")
require("not an exact multiway estimator or a coverage guarantee", "coherent diagnostic scope")


# 3. Historical reconstruction and primary product output.
org_wide = organizer["pairs"]["B04 vs B01"]
require_number("3.180", abs(org_wide["delta_eer_pts"]), 3, "widest organizer gap")
matched_wide = matched["speaker_attack"]["pairs"]["RawNet2 vs CQCC-GMM"]["simultaneous"]
require_number("-9.284", matched_wide[0], 3, "PW widest lower")
require_number("2.925", matched_wide[1], 3, "PW widest upper")
check_generated_figures()
require("reconstructions of its adaptation to EER rather than exact finite-sample tests",
        "finite-sample limitation of the reconstruction")
require("Both reconstructions of Fig.~4(c)",
        "five positive labels are explicitly tied to the published figure")
require("no cell-level agreement", "published matrix cells are not claimed")
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
    rendered = f"{cell26['coverage'][method]['coverage']:.3f}".removeprefix("0")
    if rendered != literal:
        fail(f"VALUE low-EER cell26 {method}: {rendered} != {literal}")
all_below = sum(
    all(row["coverage"][method]["coverage"] < 0.90
        for method in ("raw", "floor", "product"))
    for row in low_rows
)
if all_below != 11:
    fail(f"VALUE low-EER all-below count {all_below} != 11")
require("11/24", "joint low-EER failure count")
oracle_min = coverage_diag["low_eer_minimum_coverage"]["oracle_sd_normal"]
if f"{oracle_min:.3f}" != "0.944":
    fail(f"VALUE oracle-SD minimum changed: {oracle_min}")
require("all three are below .90 in the same 11/24 cells",
        "adverse coverage result must remain explicit")
require("does not establish that either model describes 21DF",
        "coverage cannot validate acquisition")


# 4b. EXP-112 witnessed replacement: authenticated simulation conditional on
# its fitted organizer-like Gaussian DGP, not an adequacy claim for 21DF.
if (exp112["schema"], exp112["status"]) != (
        "exp112-coverage-reseal-v2", "witnessed_new_run_not_historical_authentication"):
    fail("STATUS EXP-112 is not the witnessed replacement")
if (exp112["R"], exp112["B"], exp112["seed"], exp112["target_delta_points"]) != (
        200, 300, 20260829, 0.5):
    fail("CONTRACT EXP-112 R/B/seed/target changed")
exp112_expected = {
    "iid": (0.185, 37), "twoway": (0.98, 196),
    "jackknife": (0.975, 195), "wild": (0.975, 195),
}
for arm, expected in exp112_expected.items():
    got = (exp112["arms"][arm]["coverage"], exp112["arms"][arm]["covered"])
    if got != expected:
        fail(f"VALUE EXP-112 {arm}: {got} != {expected}")
exp112_hashes = audit_exp112["artifact_sha256"]
if exp112_receipt["result"]["sha256"] != exp112_hashes["results-v2.json"]:
    fail("HASH EXP-112 receipt does not bind result")
if (exp112_receipt["trace"]["sha256"] != exp112_hashes["trace-v2.jsonl"]
        or exp112_receipt["trace"]["rows"] != 200):
    fail("HASH EXP-112 receipt does not bind complete trace")
if (exp112_closure["result"]["sha256"] != exp112_hashes["results-v2.json"]
        or exp112_closure["receipt"]["sha256"] != exp112_hashes["RUN-RECEIPT-v2.json"]
        or exp112_closure["trace"]["sha256"] != exp112_hashes["trace-v2.jsonl"]):
    fail("HASH EXP-112 closure differs from packaged artifacts")
if exp112_addendum["original_receipt"]["sha256"] != exp112_hashes["RUN-RECEIPT-v2.json"]:
    fail("HASH EXP-112 addendum does not bind receipt")
if not (exp112_addendum["historical_unwitnessed_aggregate"][
            "producer_commit_blob_matches"]
        and exp112_addendum["correction"]["future_producer_binds_input"]
        and exp112_verification["checks"]["passed"]
        and not exp112_verification["hardcoded_receipt_flag_used_as_evidence"]):
    fail("GATE EXP-112 provenance repair/verification did not pass")
if exp112_verification["aggregate_maximum_absolute_difference"] > 1e-12:
    fail("VALUE EXP-112 trace aggregates exceed independent tolerance")
require_number("18.5", 100 * exp112["arms"]["iid"]["coverage"], 1,
               "EXP-112 trial-i.i.d. coverage")
require_number("13.73", 100 * exp112["arms"]["iid"]["wilson95"][0], 2,
               "EXP-112 trial-i.i.d. Wilson lower")
require_number("24.46", 100 * exp112["arms"]["iid"]["wilson95"][1], 2,
               "EXP-112 trial-i.i.d. Wilson upper")
clustered = [exp112["arms"][arm] for arm in ("twoway", "jackknife", "wild")]
require_number("97.5", 100 * min(row["coverage"] for row in clustered), 1,
               "EXP-112 clustered coverage minimum")
require_number("98.0", 100 * max(row["coverage"] for row in clustered), 1,
               "EXP-112 clustered coverage maximum")
require_number("94.28", 100 * min(row["wilson95"][0] for row in clustered), 2,
               "EXP-112 clustered Wilson lower")
require_number("99.22", 100 * max(row["wilson95"][1] for row in clustered), 2,
               "EXP-112 clustered Wilson upper")
require("additional trace-retaining", "EXP-112 run must be identified separately")
require("organizer-regime run", "EXP-112 result must remain conditional on its imposed DGP")
require("The fitted DGP has not been shown", "EXP-112 DGP-adequacy boundary")


# 5. Incidence and provenance composition.
global_inc = incidence["global"]
if (global_inc["n_observed_within_stratum_cells"],
    global_inc["n_within_stratum_cartesian_cells"]) != (1062, 1068):
    fail("VALUE stratified occupancy changed")
shares = global_inc["spoof_stratum_trial_mass_shares"]
vcc_share = 1.0 - shares["asvspoof"]
if f"{100 * vcc_share:.2f}" != "85.77":
    fail(f"VALUE VCC spoof-trial share changed: {100 * vcc_share}")
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
    fail("VALUE a between-cohort label now flips under source deletion")
require("separate three within-baseline pairs in at least one deletion",
        "all three gained baseline pairs must remain counted")
require_re(r"all 16 cross-cohort", "stable cross-cohort block must be bounded")
require("some within-cohort separation decisions change with them",
        "source dependence belongs with the headline")
# The source-deletion analysis is a third construction; the paper must declare it and its
# full-data reference, and both are bound here to the artifacts that produced them.
if any(row["q_draws"] != 200000 for row in loco["by_corpus"].values()):
    fail("CONTRACT LOCO Gaussian max-t draw count changed")
require("200,000 draws", "LOCO critical-value draw count must be printed")
require("Source deletion uses a third construction", "LOCO construction must be declared in the paper")
_modern = {"XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"}
def _block(name):
    a, b = name.split(" vs ")
    return "cross" if (a in _modern) != (b in _modern) else ("ssl" if a in _modern else "base")
_full = {"cross": 0, "ssl": 0, "base": 0}
for name, row in multiway["pairs"].items():
    if row["explicit_cell_jackknife"]["resolved_simultaneous_own_q"]:
        _full[_block(name)] += 1
if _full != {"cross": 16, "ssl": 2, "base": 0}:
    fail(f"VALUE full-data exact-cell jackknife block counts changed: {_full}")
require("separates 18/28 pairs (16 cross-cohort, 2 within-SSL, 0 within-baseline)",
        "LOCO full-data reference counts must be printed")
for corpus, expected in (("asvspoof", (16, 2, 1)), ("vcc2018", (16, 1, 3)), ("vcc2020", (16, 1, 0))):
    _c = {"cross": 0, "ssl": 0, "base": 0}
    for name, row in loco["by_corpus"][corpus]["pairs"].items():
        if row["resolved"]:
            _c[_block(name)] += 1
    if (_c["cross"], _c["ssl"], _c["base"]) != expected:
        fail(f"VALUE LOCO block counts changed for {corpus}: {_c}")


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
for literal in ("Six of the twelve comparisons within either detector group, four self-supervised (SSL) detectors and four organizer baselines, reverse EER ordering",
                "six of the 12 within-cohort pairs reverse their point ordering (five within-baseline; the SSL one is XLSR-Mamba versus XLS-R+SLS, gap 0.032 points) and none of the 16 cross-cohort pairs does"):
    require(literal, "registered composition-policy asymmetry must be visible with its pair denominator")

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
require("all 729 accepted direction endpoints", "accepted constructive directions must be reported")
require("five at distance at most 0.10", "small-shift constructive witness count must be reported")
best_tv = composition_v2_verified["best_verified_r_TV_by_pair"][
    "XLSR-Mamba vs XLS-R+SLS"
]
require_number(".010218", best_tv, 6, "smallest verified constructive rTV bound")
require("explicitly post-result", "secondary search chronology must be disclosed")
require("not a minimum", "constructive upper bounds cannot become safety radii")
require("not an absence result", "absence of cross-cohort witness is scoped")


# 7. Arena and measured width layer.
for literal, value, nd, label in (
    ("52", arena["schemes"]["iid"]["n_resolved_simultaneous"], None, "Arena iid count"),
    ("38", arena["schemes"]["clustered"]["n_resolved_simultaneous"], None,
     "Arena clustered count"),
    ("8.45", arena["median_width_ratio"], 2, "Arena median width ratio"),
):
    require_number(literal, value, nd, label)
cross_layer = arena["cross_layer_sensitivity"]["RawNet2-Arena vs RawNet2"]
if (f"{cross_layer['arena_eer']:.2f}", f"{cross_layer['primary_eer']:.2f}",
        f"{cross_layer['score_pearson']:.2f}") != ("40.67", "22.38", "0.36"):
    fail("VALUE Arena cross-layer provenance diagnostic changed")
require("not population confidence intervals", "Arena outputs remain descriptive")

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


# 8. Field-standard main EER table and complete supplementary 28-pair table.
order = list(selection["21df"]["rank_sets"])
eer = {name: f"{selection['21df']['rank_sets'][name]['pooled_eer']:.3f}" for name in order}
expected_eer_rows = [[order[i], eer[order[i]], order[i + 4], eer[order[i + 4]]] for i in range(4)]
_modern = {"XLSR-Mamba", "XLS-R+SLS", "XLSR-Conformer", "SSL-AASIST"}
def _blk(pair):
    a, b = pair.split(" vs ")
    return "cross" if (a in _modern) != (b in _modern) else ("ssl" if a in _modern else "base")
def _count(rows, key):
    out = {"ssl": 0, "base": 0, "cross": 0}
    for pair, row in rows.items():
        out[_blk(pair)] += int(row[key])
    return out
_t = _count(matched["iid"]["pairs"], "resolved_simultaneous")
_p = _count(matched["speaker_attack"]["pairs"], "resolved_simultaneous")
_r = _count({p: {"x": v["registered_policy_sign_change"]} for p, v in composition["pair_multiverse"].items()}, "x")
expected_group_rows = [
    ["Pair group", "Trial", "PW", "Reversed"],
    ["Within SSL", f"{_t['ssl']}/6", f"{_p['ssl']}/6", f"{_r['ssl']}/6"],
    ["Within baselines", f"{_t['base']}/6", f"{_p['base']}/6", f"{_r['base']}/6"],
    ["SSL vs.\\ baselines", f"{_t['cross']}/16", f"{_p['cross']}/16", f"{_r['cross']}/16"],
]
body = TEX_RAW[TEX_RAW.index("\\label{tab:eers}"):TEX_RAW.index("\\end{tabular}")]
printed = [line for line in body.splitlines() if "&" in line and "\\\\" in line]
printed_rows = [[cell.strip() for cell in line.replace("\\\\", "").split("&")]
                for line in printed]
if printed_rows != expected_eer_rows + expected_group_rows:
    fail(f"TABLE main table rows differ from artifacts: {printed_rows} != {expected_eer_rows + expected_group_rows}")
if _r != {"ssl": 1, "base": 5, "cross": 0}:
    fail(f"VALUE weighting-rule reversal split changed: {_r}")
_ar = arena["schemes"]
_k = "HuBERT-ECAPA-Arena vs WavLM-ECAPA-Arena"
require_number("-2.153", _ar["iid"]["pairs"][_k]["delta_eer_pts"], 3, "Arena example gap")
for _v, _lit in ((_ar["iid"]["pairs"][_k]["ci95_simultaneous"][0], "-2.761"), (_ar["iid"]["pairs"][_k]["ci95_simultaneous"][1], "-1.544"),
                 (_ar["clustered"]["pairs"][_k]["ci95_simultaneous"][0], "-5.241"), (_ar["clustered"]["pairs"][_k]["ci95_simultaneous"][1], "0.936")):
    require_number(_lit, _v, 3, "Arena example band endpoint")
require("For HuBERT-ECAPA versus WavLM-ECAPA", "Arena example pair must be printed")

for pair, iid_row in matched["iid"]["pairs"].items():
    a, b = pair.split(" vs ")
    pw_row = matched["speaker_attack"]["pairs"][pair]
    expected = (
        f"| {a} | {b} | {iid_row['delta_eer_pts']:.6f} | "
        f"[{iid_row['simultaneous'][0]:.6f}, {iid_row['simultaneous'][1]:.6f}] | "
        f"{'yes' if iid_row['resolved_simultaneous'] else 'no'} | "
        f"[{pw_row['simultaneous'][0]:.6f}, {pw_row['simultaneous'][1]:.6f}] | "
        f"{'yes' if pw_row['resolved_simultaneous'] else 'no'} |"
    )
    if SUPPLEMENT_RAW.count(expected) != 1:
        fail(f"TABLE supplement row missing or duplicated for {pair}: {expected}")
if "MDE" in body:
    fail("RETIRED main table still contains MDE")


# 6b. EXP-116 policy-band verification (post-result), witness masses, ASV5 counts,
#     Arena ratio definition, release locator.
exp116 = load(EXP116 / "RESULTS.json")
if exp116["registered_reading"] != "all_cross_cohort_pairs_separated_under_all_rules_and_laws":
    fail("STATUS EXP-116 registered reading is not the all-separated branch")
if exp116["cross_cohort_indicators"] != {"separated": 384, "total": 384}:
    fail(f"VALUE EXP-116 cross-cohort indicators changed: {exp116['cross_cohort_indicators']}")
if len(exp116["cells"]) != 24 or exp116["B"] != 5000:
    fail("CONTRACT EXP-116 cell count or draw count changed")
if exp116["estimator_gate_max_abs_deviation_points"] > 1e-9:
    fail("GATE EXP-116 estimator did not reproduce EXP-108 contrasts")
closest = max(p["band"][1] for c in exp116["cells"] for p in c["pairs"].values()
              if p["block"] == "cross")
require_number("-12.79", closest, 2, "EXP-116 closest cross-cohort band endpoint")
b0s0 = {c["law"]: c["counts"] for c in exp116["cells"] if c["rule"] == "B0xS0"}
if (b0s0["trial"]["cross"]["separated"] + b0s0["trial"]["within_ssl"]["separated"]
        + b0s0["trial"]["within_baseline"]["separated"]) != 26 or (
        b0s0["pw"]["cross"]["separated"] + b0s0["pw"]["within_ssl"]["separated"]
        + b0s0["pw"]["within_baseline"]["separated"]) != 18:
    fail("VALUE EXP-116 empirical-weight cell does not reproduce 26/28 and 18/28")
require("separates all 16 cross-cohort pairs in all 24 rule",
        "EXP-116 result must be reported with its full cell denominator")
require("computed after the primary results, 5,000 draws per rule and bootstrap", "EXP-116 post-result status must be disclosed")

witness = composition_v2["pairs"]["XLSR-Mamba vs XLS-R+SLS"]["objectives"]["r_TV"]["best_overall"]["witness"]
q_bona = ",".join(f"{v:.3f}".lstrip("0") for v in witness["q_bona"])
q_spoof = ",".join(f"{v:.3f}".lstrip("0") for v in witness["q_spoof"])
require(f"bona-fide masses ({q_bona})", "witness bona-fide masses must match the verified artifact")
require(f"spoof-stratum masses ({q_spoof})", "witness spoof masses must match the verified artifact")
require("in the order above and rounded", "witness masses are rounded and ordered as the strata list")

asv5_trial_sep = sum(v["numeric_band_excludes_zero"] for v in asv5_pair["trial_iid"]["pairs"].values())
asv5_sa_sep = sum(v["numeric_band_excludes_zero"] for v in asv5_pair["speaker_attack"]["pairs"].values())
if (asv5_trial_sep, asv5_sa_sep) != (6, 5):
    fail(f"VALUE ASV5 separated counts changed: trial {asv5_trial_sep}, speaker-attack {asv5_sa_sep}")
require("from 6/6 under trial resampling to 5/6", "ASV5 before/after separated counts must be visible")
require("the 367 target speakers, the 370 bona-fide-only speakers and the 16 attacks as three independent multinomial draws",
        "ASV5 resampling law must be stated, not labelled")

require("median ratio of PW to trial bootstrap standard deviations over the 55 pairs",
        "Arena ratio is a bootstrap-SD ratio, not a band-width ratio")

# Release locator: the sentence naming SUPPLEMENT.md must carry a repository URL and a tag
# in the manuscript itself (never satisfied by the supplement). Mutation-tested through
# the release_locator obligation.
_rel = TEX.find("SUPPLEMENT.md")
if _rel < 0 or "github.com/rvirgilli/" not in TEX[_rel:_rel + 400] or ", tag " not in TEX[_rel:_rel + 400]:
    fail("PRESENT the supplement sentence does not carry a repository URL and tag within 400 chars; "
         "a promise of an artifact is not an artifact")

exp118 = load(EXP118 / "RESULTS.json")
if exp118["registered_reading"] != "exception_declared_and_numerically_immaterial" or exp118["stratified"]["separated"] != 6:
    fail("VALUE EXP-118 class-stratified SpoofCeleb count is not 6/6")
require("(a class-stratified recomputation also separates 6/6)", "SpoofCeleb class-stratified count must be printed next to the pooled one")

# 9. Scientific scope obligations and retired formulations.
for text, why in (
    ("fixed-score sensitivity bands", "identified scientific object"),
    ("not population confidence intervals", "abstract scope"),
    ("not an exact multiway estimator or a coverage guarantee", "Gaussian scope"),
    ("while official access was pending", "timing claim is anchored to access state"),
    ("it does not establish equality", "non-significance scope"),
    ("a defensible acquisition model and an inferential procedure valid under its dependence structure",
     "only full repair for population inference"),
    ("trial-to-speaker/attack membership", "report units rather than trial count"),
    ("remain separated under both bootstraps, each leave-one-source-out refit of the declared jackknife construction and all 12 fixed weighting rules",
     "conclusion must remain bounded to tested robustness checks"),
    ("remain separated under both resampling methods with all twelve weighting rules, and under separate leave-one-source-out jackknife refits",
     "abstract must remain bounded to tested robustness checks"),
    ("distinct from the nested-observation designs studied in", "crossed versus nested design must be stated in field terms"),
    ("Neither the primary-score analysis nor the Arena-score analysis supplies population confidence intervals or confidence sets for ranks", "no population or rank-confidence claim"),
    ("using unstratified trial resampling on a different four-detector roster", "SpoofCeleb trial law and roster must be visible in the abstract"),
    ("for SpoofCeleb only, the archived plan samples the 91,130 trial indices from the pooled list with replacement",
     "the SpoofCeleb trial-law exception must be declared in the method section"),
    ("The ASVspoof~5 SSL-AASIST and AASIST score files lack their originating run logs", "provenance limitation must name its dataset"),
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
    (r"within-generation|cross-generation|coarse generation separation",
     "detector cohorts must not be confused with spoof generators"),
    (r"universal calibration|calibrates procedures",
     "coverage evaluation must not be confused with score calibration"),
    (r"Gate~?2|original seal|scorer entrypoint|registered endpoint",
     "internal workflow vocabulary must not carry a scientific claim"),
    (r"paired-decision|Local composition fragility|coherent marginal-sum sensitivity covariance",
     "private procedure labels must not be presented as field terminology"),
    (r"pointwise percentile half-width",
     "Table 1 must report the simultaneous quantity used for decisions"),
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
print("OK — scientific contract passes: matched trial/PW results, complete system and "
      "pair tables, coverage boundaries, source weighting, SpoofCeleb/ASV5 checks, "
      "and all caveats are artifact-bound.")
