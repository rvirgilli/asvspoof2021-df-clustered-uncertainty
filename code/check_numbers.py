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
ROOT = Path(os.environ.get("M1_RELEASE_ROOT", HERE.parent))
DERIVED = ROOT / "derived"
PLANS = ROOT / "plans"
PAPER = Path(os.environ.get("M1_PAPER_ROOT", ROOT / "paper"))
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
    document = {"main.tex": TEX_RAW, "SUPPLEMENT.md": SUPPLEMENT_RAW}[obligation.get("source", "main.tex")]
    count = document.count(obligation["match"])
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
        ROOT / "code/make_public_audit.py"):
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
require("ASVspoof 5's primary Track 1 metric is", "external result retained in supplement")
require("not a system-performance replication", "ASV5 external-check scope")
require("ASVspoof 5 SSL-AASIST and AASIST score files lack their originating run logs",
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
require("movement of these eight masses is not required for the loss of separation",
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
    if sha256(ROOT / "code" / name) != digest:
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
require("A post-result PW control",
        "EXP-111 chronology and role must be visible")
require("(1,000 draws, seed 20260824)", "EXP-111 draw count and seed differ from the primary arms and must be stated")
require("stratum (7 rejected attempts out of 1,007 for VCC2018, all for lost spoof support; no\nrejections elsewhere), and then rescales each class-specific source or stratum mass exactly\nto its observed value",
        "EXP-111 composition control must state its zero-support rule and rejection count")
require("A post-result PW control",
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
# S2: the main-text headline now identifies the surviving pairs, not just their count.
spoofceleb_survivors = {
    pair for pair, row in exp114["arm_b_global_product"]["pairs"].items()
    if row["simultaneous_excludes_zero"]
}
if spoofceleb_survivors != {"aasist vs sls", "aasist vs ssl_aasist", "aasist vs xlsr_mamba"}:
    fail("VALUE SpoofCeleb joint survivors are not exactly the three AASIST comparisons")
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
require("91,130 SpoofCeleb evaluation trials", "EXP-114 complete evaluation size must remain visible")
require("single-source SpoofCeleb", "EXP-114 source/composition control must remain visible")
require("while official repository access was pending",
        "EXP-114 prospective chronology must remain visible in field-facing language")
require("6/6", "EXP-114 trial-i.i.d. endpoint must remain visible")
require("3/6", "EXP-114 product/source endpoint must remain visible")
require("one source label, so between-source mass cannot change",
        "EXP-114 fixes source composition, not all factor multiplicities")
require("a spoof trial receives the product of its speaker and attack multiplicities",
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
require("1.44e-6", "EXP-114 Mamba maximum score delta ceiling")
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
require("speaker-only and attack-only bootstraps separated 5/6\nand 3/6",
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
    if sha256(ROOT / "code" / name) != digest:
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
require("Both reconstructions of Fig. 4(c)",
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
# S3: distinguish each method's failure total from their common intersection.
low_eer_failures = {
    method: sum(row["coverage"][method]["coverage"] < 0.90 for row in low_rows)
    for method in ("raw", "floor", "product")
}
if len(low_rows) != 24 or low_eer_failures != {"raw": 16, "floor": 16, "product": 11}:
    fail(f"VALUE low-EER individual failure counts changed: {low_eer_failures}")
require("11/24", "joint low-EER failure count")
oracle_min = coverage_diag["low_eer_minimum_coverage"]["oracle_sd_normal"]
if f"{oracle_min:.3f}" != "0.944":
    fail(f"VALUE oracle-SD minimum changed: {oracle_min}")
require("Coverage fell below .90 in 16/24 low-EER cells for each jackknife interval and 11/24 for PW percentile; all three failed in the same 11 cells",
        "individual and common adverse coverage counts must remain explicit")
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
require("4, 4, 4 and 6 speakers", "dominant sparse blocks must be visible")

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
require("separate three\nwithin-baseline pairs in at least one deletion",
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
require("separates 18/28 pairs (16 cross-cohort,\n2 within-SSL, 0 within-baseline)",
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
require("Fixed rules reverse 5/6 organizer-baseline, 1/6 within-SSL and 0/16 cross-cohort point orderings.",
        "fixed-rule reversal counts and denominators must remain visible")
require("already unseparated under trial resampling", "the reversing SSL pair is already unseparated")


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
require("not confidence about future speakers or attacks", "Arena outputs remain descriptive")

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


# 8. Primary point EERs and selected paired bands in the main table; complete S3/S4 tables.
order = list(selection["21df"]["rank_sets"])
eer = {name: f"{selection['21df']['rank_sets'][name]['pooled_eer']:.3f}" for name in order}
# Point results remain required at their existing precision in supplement S3.
for i, name in enumerate(order):
    release = "model author" if i < 4 else "ASVspoof organizer"
    row = f"| {name} | {release} | {eer[name]} | {i + 1} |"
    if SUPPLEMENT_RAW.count(row) != 1:
        fail(f"TABLE supplement point row missing or duplicated: {row}")
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
# The requested two-roster panel transposes the arms; reversals move below the table.
require("Fixed rules reverse 5/6 organizer-baseline, 1/6 within-SSL and 0/16 cross-cohort point orderings.",
        "displaced reversal inventory remains in the main results")
require("The SSL pair is Mamba--SLS (gap -0.032 points), already unseparated under trial resampling.",
        "reversal identity, signed gap and trial status remain together")
ablation = load(ROOT / "evidence/ABLATION-RESULTS.json")
if "exploratory post-hoc" not in ablation["analysis_status"]:
    fail("STATUS primary ablation must remain exploratory post-hoc")
if ablation["B_per_new_arm"] != 5000 or ablation["seed_rule"]["master_seed"] != 2026081604:
    fail("CONTRACT primary ablation draw count or campaign seed changed")
if ablation["seed_rule"]["spawn_keys"] != {
        "trial": [0], "speaker_attack": [1], "speaker_only": [2], "attack_only": [3]}:
    fail("CONTRACT primary ablation must append the two campaign seed streams")
if not ablation["inputs"]["all_inputs_match_published_hashes"] or not all(ablation["verification"].values()):
    fail("GATE primary ablation input/summary verification failed")
for key, original in (("trial", matched["iid"]), ("speaker_attack", matched["speaker_attack"])):
    if ablation["arms"][key]["summary"] != original:
        fail(f"VALUE primary ablation changed published {key} summary")
expected_group_rows = []
ablation_counts = {}
for key, label, supp_label in (
    ("trial", "Trial", "Trial"),
    ("speaker_only", "Speaker-only", "Speaker-only"),
    ("attack_only", "Attack-only", "Attack-only"),
    ("speaker_attack", r"Speaker$\times$attack", "Speaker × attack"),
):
    arm = ablation["arms"][key]
    counts = arm["counts"]
    groups = _count(arm["summary"]["pairs"], "resolved_simultaneous")
    if counts != {"all_28": sum(groups.values()), "organizer_6": groups["base"],
                  "ssl_6": groups["ssl"], "cross_cohort_16": groups["cross"]}:
        fail(f"VALUE primary ablation {key} counts disagree with pair records")
    ablation_counts[key] = (counts["all_28"], counts["organizer_6"], counts["ssl_6"])

    if counts["cross_cohort_16"] != 16:
        fail(f"VALUE primary ablation {key} lost cross-cohort separation")
    dagger = "†" if key == "attack_only" else ""
    row = f"| {supp_label} | {counts['all_28']}{dagger} | {counts['organizer_6']}{dagger} | {counts['ssl_6']} | 16 |"
    if SUPPLEMENT_RAW.count(row) != 1:
        fail(f"TABLE primary ablation supplement row missing or duplicated: {row}")
if ablation_counts != {"trial": (26, 5, 5), "speaker_only": (18, 0, 2),
                       "attack_only": (22, 3, 3), "speaker_attack": (18, 0, 2)}:
    fail("VALUE primary ablation four-arm result changed")
indicators = {k: {p: v["resolved_simultaneous"] for p, v in a["summary"]["pairs"].items()}
              for k, a in ablation["arms"].items()}
if indicators["speaker_only"] != indicators["speaker_attack"]:
    fail("VALUE speaker-only must reproduce the entire joint indicator vector")
lost = [p for p in indicators["trial"] if indicators["trial"][p] and not indicators["speaker_attack"][p]]
attack_lost = [p for p in lost if not indicators["attack_only"][p]]
if (len(lost), len(attack_lost)) != (8, 4):
    fail("VALUE primary ablation must reproduce eight speaker-only and four recorded-seed attack-only losses")
for pair in lost:
    row = f"| {pair} | yes | {'yes' if pair in attack_lost else 'no'} |"
    if SUPPLEMENT_RAW.splitlines().count(row) != 1:
        fail(f"TABLE primary ablation lost-pair row missing or duplicated: {row}")
# Common exploratory/noncausal scope is protected once in Method by the manifest.

# S4a now prints the complete four-arm evidence, not only aggregate counts.
s4a = SUPPLEMENT_RAW.split("### S4a. Primary-21DF factor ablation", 1)[-1].split("## S5.", 1)[0]
ablation_arm_order = ("trial", "speaker_only", "attack_only", "speaker_attack")
for pair, original in ablation["arms"]["trial"]["summary"]["pairs"].items():
    rows = [ablation["arms"][key]["summary"]["pairs"][pair] for key in ablation_arm_order]
    cells = ["yes" if row["resolved_simultaneous"] else "no" for row in rows]
    indicator_row = "| " + " | ".join([pair, *cells]) + " |"
    bands = [f"[{row['simultaneous'][0]:.6f}, {row['simultaneous'][1]:.6f}]" for row in rows]
    band_row = "| " + " | ".join([pair, f"{original['delta_eer_pts']:.6f}", *bands]) + " |"
    for expected in (indicator_row, band_row):
        if s4a.splitlines().count(expected) != 1:
            fail(f"TABLE S4a missing or changed artifact-bound row: {expected}")
for key, label in zip(ablation_arm_order, ("Trial", "Speaker-only", "Attack-only", "Speaker × attack")):
    expected = f"| {label} | {ablation['arms'][key]['summary']['supt_critical_value']:.6f} |"
    if s4a.splitlines().count(expected) != 1:
        fail(f"TABLE S4a missing or changed critical value: {expected}")

table_start = TEX_RAW.index(r"\label{tab:eers}")
body = TEX_RAW[table_start:TEX_RAW.index(r"\end{table}", table_start)]
# Bind every display row, including pair identity, direction and both band arms.
examples = [
    ("XLSR-Mamba $-$ XLSR-Conformer", matched["iid"]["pairs"]["XLSR-Mamba vs XLSR-Conformer"],
     matched["speaker_attack"]["pairs"]["XLSR-Mamba vs XLSR-Conformer"], "simultaneous"),
    ("Arena HuBERT-ECAPA $-$ WavLM-ECAPA", arena["schemes"]["iid"]["pairs"]["HuBERT-ECAPA-Arena vs WavLM-ECAPA-Arena"],
     arena["schemes"]["clustered"]["pairs"]["HuBERT-ECAPA-Arena vs WavLM-ECAPA-Arena"], "ci95_simultaneous"),
]
expected_band_lines = []
for label, trial, pw, band_key in examples:
    expected_band_lines.append(
        r"\multicolumn{4}{@{}l@{}}{" + label + f": ${trial['delta_eer_pts']:.3f}$" + r"} \\")
    expected_band_lines.append(
        r"\multicolumn{2}{@{}l}{Trial $[" + f"{trial[band_key][0]:.3f},{trial[band_key][1]:.3f}"
        + r"]$} & \multicolumn{2}{l@{}}{PW $[" + f"{pw[band_key][0]:.3f},{pw[band_key][1]:.3f}" + r"]$} \\")
# Finding 2 adds the primary point EERs alongside every existing paired-band row.
expected_point_rows = [["SSL detector", "EER", "Organizer baseline", "EER"]]
for ssl, baseline in zip(order[:4], order[4:]):
    expected_point_rows.append([ssl, eer[ssl], baseline, eer[baseline]])
expected_point_lines = [" & ".join(row) + r" \\" for row in expected_point_rows]
arms = ("trial", "speaker_only", "attack_only", "speaker_attack")
expected_group_rows = [["Roster / subset", "Trial", "Speaker", "Attack", "Joint"]]
for label, key, denominator in (("21DF, all", "all_28", 28), ("21DF, SSL", "ssl_6", 6),
                                 ("21DF, organizer", "organizer_6", 6)):
    values = []
    for arm in arms:
        value = f"{ablation['arms'][arm]['counts'][key]}/{denominator}"
        if arm == "attack_only" and key != "ssl_6":
            # Revised table prints original + all five fresh stream extrema.
            attack_diagnostics = load(ROOT / "evidence/diagnostics.json")
            observed = [sum(p["separated"] for p in attack_diagnostics["results"][run]["pairs"].values())
                        if key == "all_28" else _count(attack_diagnostics["results"][run]["pairs"], "separated")["base"]
                        for run in ["attack_only"] + [f"attack_repeat_{i}" for i in range(5)]]
            value = f"{min(observed)}--{max(observed)}/{denominator}"
        values.append(value)
    expected_group_rows.append([label, *values])
# The removed SpoofCeleb row is replaced by its explicit control paragraph.
require("pooled trial resampling separates 6/6 pairs and joint resampling 3/6",
        "SpoofCeleb table endpoints must survive in the control paragraph")
expected_lines = expected_point_lines + expected_band_lines + [" & ".join(row) + r" \\" for row in expected_group_rows]
printed_lines = [line.strip() for line in body.splitlines() if line.rstrip().endswith(r"\\")]
if printed_lines != expected_lines:
    fail(f"TABLE main table rows differ from artifacts: {printed_lines} != {expected_lines}")
if r"primary 21DF EER (\%), with 14,869 bona-fide and 519,059 spoof trials and weights normalized within class" not in TEX_RAW:
    fail("TABLE primary point EERs must name their units, sample size and weighting")
require("primary 21DF uses all 28 pairs, Arena all 55 pairs",
        "main paired-band display must distinguish its multiplicity families")
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

# S5 checks supplement, rather than replace, the original obligations above.
for key in ("q_bona", "q_spoof"):
    masses = ", ".join(f"{v:.10f}" for v in witness[key])
    if SUPPLEMENT_RAW.count(f"`{key}=({masses})`") != 1:
        fail(f"VALUE S5 {key} masses differ from the verified witness")
# The full witness is now in S5, as authorized by the full-audit revision.
for literal in (f"{best_tv:.6f}".lstrip("0"), f"bona-fide masses ({q_bona})",
                f"spoof-stratum masses ({q_spoof})", "in the order above and rounded",
                "bona-fide sources are ASVspoof, VCC2018, VCC2020",
                "spoof strata are ASVspoof, VCC2018 HUB, VCC2018 SPO, VCC2020 Task 1, VCC2020 Task 2",
                "The reversing sign holds under the original position sweep and at distinct-score boundaries."):
    if literal not in SUPPLEMENT_RAW:
        fail(f"PRESENT relocated S5 witness missing {literal}")

asv5_trial_sep = sum(v["numeric_band_excludes_zero"] for v in asv5_pair["trial_iid"]["pairs"].values())
asv5_sa_sep = sum(v["numeric_band_excludes_zero"] for v in asv5_pair["speaker_attack"]["pairs"].values())
if (asv5_trial_sep, asv5_sa_sep) != (6, 5):
    fail(f"VALUE ASV5 separated counts changed: trial {asv5_trial_sep}, speaker-attack {asv5_sa_sep}")
require("Trial resampling separates 6/6 pairs and the role-stratified law 5/6", "ASV5 before/after separated counts must be visible")
require("Its resampling law draws 367 target-speaker\nmultiplicities, 370 bona-fide-only speaker multiplicities and 16 attack multiplicities as three\nindependent multinomial samples",
        "ASV5 resampling law must be stated, not labelled")

require("median ratio of PW to trial bootstrap standard deviations over the 55 pairs",
        "Arena ratio is a bootstrap-SD ratio, not a band-width ratio")

# The revised release binds the evidence files; anonymous readback is checked separately.
for name in ("ABLATION-RESULTS.json", "diagnostics.json", "influence.json"):
    if f"evidence/{name}" not in SUPPLEMENT_RAW:
        fail(f"RELEASE supplement lacks evidence locator {name}")
if "### S4a. Primary-21DF factor ablation" not in SUPPLEMENT_RAW:
    fail("PRESENT supplement lacks the cited ablation section")

exp118 = load(EXP118 / "RESULTS.json")
if exp118["registered_reading"] != "exception_declared_and_numerically_immaterial" or exp118["stratified"]["separated"] != 6:
    fail("VALUE EXP-118 class-stratified SpoofCeleb count is not 6/6")
require("class-stratified trial resampling also gives 6/6", "SpoofCeleb class-stratified count must be printed next to the pooled one")


# 8b. Post-review diagnostics newly cited by the impact revision.
diag = load(ROOT / "evidence/diagnostics.json")
influence = load(ROOT / "evidence/influence.json")
for name, digest in {
    "ABLATION-RESULTS.json": "41ffd32fa5bd446e0f7777d0d6d70b93b0153779b432516783216558f58fa8a3",
    "diagnostics.json": "913b096bfe4f699743fe7b58b694c622ad9473df87cef35216880e91ef426dff",
    "influence.json": "b3508bdf13f0929e7e8c9532d65e9fedc31c3158334fdb7743a5787614592759",
}.items():
    if sha256(ROOT / "evidence" / name) != digest:
        fail(f"HASH supplied post-review evidence changed: {name}")
if (diag["inputs_sha256"] != ablation["inputs"]["sha256"]
        or influence["inputs_sha256"] != diag["inputs_sha256"]
        or diag["saved_ablation_sha256"] != ablation["replicates"]["sha256"]
        or diag["protected_files_before_and_after"]["evidence/ABLATION-RESULTS.json"] != sha256(ROOT / "evidence/ABLATION-RESULTS.json")):
    fail("HASH new diagnostics do not share primary inputs/ablation")
# Forced-by-an-edit: only portable producers ship, so both the evidence and
# executable must bind to the same portable digest; no historical alternative.
diagnostic_driver_bindings = {
    "strategy_diagnostics.py": "14c25cc62b89e2ae21acf0d9b53e05708495f3aaf746a9fb845b7a9275506b7a",
    "strategy_influence.py": "8c97a8df91782e4699effc55a8c5792095834e8cae00bb5f7dfe195e98b9a19c",
}
for file, result in (("strategy_diagnostics.py", diag), ("strategy_influence.py", influence)):
    portable_digest = diagnostic_driver_bindings[file]
    if (result["driver_sha256"] != portable_digest
            or sha256(ROOT / "code" / file) != portable_digest):
        fail(f"HASH diagnostic driver changed: {file}")
for name, digest in (("ABLATION-REPLICATES.npz", diag["saved_ablation_sha256"]),
                     ("replicates.npz", diag["replicates_sha256"])):
    if sha256(ROOT / "evidence" / name) != digest:
        fail(f"HASH diagnostic replicate archive changed: {name}")
if diag["primary_validation_max_error"] != 0:
    fail("GATE diagnostic implementation no longer reproduces campaign estimator")
for arm in ("trial", "speaker_only", "attack_only", "speaker_attack"):
    if not diag["results"][arm]["published_summary_exactly_reproduced"]:
        fail(f"GATE diagnostic original arm not reproduced: {arm}")

pair = "XLSR-Mamba vs XLSR-Conformer"
# Compact main table and complete supplement mean/sign table.
for arm, main_label, label in (("trial", "Trial", "Trial"), ("speaker_only", "Speaker", "Speaker-only"),
                               ("attack_only", "Attack", "Attack-only"), ("speaker_attack", "Joint", "Joint")):
    row = diag["results"][arm]["pairs"][pair]
    count = round(row["opposite_sign_frequency"] * diag["results"][arm]["B"])
    main_row = (f"{main_label} & ${row['mean_shift']:.6f}$ & {row['sd']:.6f} & {count} & "
                + ("Yes" if row["separated"] else "No") + r" \\")
    supplement_row = (f"| {label} | {row['mean_shift']:.6f} | {row['sd']:.6f} | {count}/5,000 | "
                      f"{100*row['opposite_sign_frequency']:.2f}% | "
                      + ("yes" if row["separated"] else "no") + " |")
    for rendered, document in ((main_row, TEX_RAW), (supplement_row, SUPPLEMENT_RAW)):
        if document.count(rendered) != 1:
            fail(f"TABLE mean/sign row missing or changed: {rendered}")
joint = diag["results"]["speaker_attack"]["pairs"][pair]
for literal, value, decimals, label in (
    ("0.777", joint["correlation"], 3, "joint paired correlation"),
    ("0.248131", joint["paired_over_unpaired_variance"], 6, "paired/marginal variance"),
    ("75.19", 100*(1-joint["paired_over_unpaired_variance"]), 2, "paired variance cancellation percent"),
    ("0.032", abs(joint["mean_shift_over_sd"]), 3, "joint displacement magnitude in SD"),
    ("0.06149", diag["results"]["trial"]["pairs"][pair]["sd"], 5, "trial paired SD"),
    ("0.31997", joint["sd"], 5, "joint paired SD"),
    ("0.41", 100*joint["sign_frequency_mcse"], 2, "joint sign-frequency MCSE points"),
):
    require_number(literal, value, decimals, label)
attack_pair = diag["results"]["attack_only"]["pairs"][pair]
for value in attack_pair["percentiles_2p5_97p5"]:
    require_number(f"{value:.6f}", value, 6, "attack-only percentile endpoint")

# Recorded count is immutable; fresh seeds quantify its simulation noise.
if diag["seed_rule"]["repeats_master"] != 2026091601 or diag["seed_rule"]["repeat_spawn_keys"] != list(range(5)):
    fail("CONTRACT fresh attack-only streams changed")
fragile = "LFCC-LCNN vs CQCC-GMM"
original = diag["results"]["attack_only"]
for key, label in ([("attack_only", "Recorded seed†")]
                   + [(f"attack_repeat_{i}", f"Fresh stream {i}") for i in range(5)]
                   + [("attack_repeats_pooled_25000", "Five fresh streams pooled")]):
    row = diag["results"][key]
    groups = _count(row["pairs"], "separated")
    expected = (f"| {label} | {row['B']:,} | {row['pairs'][fragile]['hi']:+.6f} | "
                f"{row['count']}/28 | {groups['base']}/6 |")
    if SUPPLEMENT_RAW.count(expected) != 1:
        fail(f"TABLE Monte Carlo row missing or changed: {expected}")
    changes = [p for p in row["pairs"] if row["pairs"][p]["separated"] != original["pairs"][p]["separated"]]
    if changes not in ([], [fragile]):
        fail(f"VALUE fresh-seed indicators changed beyond fragile pair: {key}")
if sum(not diag["results"][f"attack_repeat_{i}"]["pairs"][fragile]["separated"] for i in range(5)) != 4:
    fail("VALUE four-of-five attack-only MC changes no longer hold")
mc = diag["saved_attack_endpoint_mc"]
for value in (mc["upper_endpoint_quantiles_2p5_50_97p5"][0], mc["upper_endpoint_quantiles_2p5_50_97p5"][-1]):
    require_number(f"{value:.6f}", value, 6, "MC upper-endpoint percentile")
require_number("56.2", 100*mc["fraction_upper_endpoint_below_zero"], 1, "MC endpoint negative share")
forbid(r"attack-only reproduces four\.", "recorded-seed attack loss count is not Monte Carlo stable")
if "attack-only reproduces four." in SUPPLEMENT_RAW:
    fail("SCOPE supplement has unqualified fixed attack-only loss count")

# Every weighted tie-check row, and its exact scope.
runs = ["trial", "speaker_only", "attack_only", "speaker_attack"] + [f"attack_repeat_{i}" for i in range(5)]
for key in runs:
    row = diag["results"][key]; tie = row["tie_check"]
    expected = (f"| {key} | {row['B']:,} | {tie['max_replicate_eer_difference']:.6f} | "
                f"{tie['max_pair_endpoint_difference']:.6f} | {len(tie['changed_indicators'])} |")
    if SUPPLEMENT_RAW.count(expected) != 1 or tie["changed_indicators"]:
        fail(f"TABLE weighted tie result missing or changed: {key}")
if sum(diag["results"][k]["B"] for k in runs) != 45000:
    fail("CONTRACT weighted tie-check replicate census changed")
require_number("0.000233", max(diag["results"][k]["tie_check"]["max_pair_endpoint_difference"] for k in runs), 6, "maximum tie endpoint change")
require_number("0.019166", max(diag["results"][k]["tie_check"]["max_replicate_eer_difference"] for k in runs), 6, "maximum tie replicate change")

# Influence concentration: group identity, denominator, and deletion gap stay together.
for p in (pair, "XLS-R+SLS vs XLSR-Conformer", "XLSR-Conformer vs SSL-AASIST"):
    row = influence["results"]["speaker"]["pairs"][p]; group = row["top_groups"][0]
    hat = diag["results"]["trial"]["pairs"][p]["hat"]
    expected = (f"| {p} | {group['speaker_label']} | {100*row['top_one_ss_share']:.2f}% | "
                f"{100*row['top_five_ss_share']:.2f}% | {hat:.6f} | {group['deletion_gap']:.6f} |")
    if SUPPLEMENT_RAW.count(expected) != 1:
        fail(f"TABLE influence row missing or changed: {expected}")
if sum(influence["results"][g]["group_count"] for g in ("speaker", "attack")) != 203:
    fail("CONTRACT group deletion census changed")

mamba_influence = influence["results"]["speaker"]["pairs"][pair]
sls_influence = influence["results"]["speaker"]["pairs"]["XLS-R+SLS vs XLSR-Conformer"]
# Revised influence claim replaces shares with the interpretable deletion gap.
expected_influence = (
    f"Deleting {mamba_influence['top_groups'][0]['speaker_label']}, which contains 315 bona-fide VCC2018 trials and no spoof trials, "
    f"changes the Mamba--Conformer gap from ${joint['hat']:.3f}$ to "
    f"${mamba_influence['top_groups'][0]['deletion_gap']:.3f}$ percentage points.")
if TEX_RAW.count(expected_influence) != 1:
    fail("VALUE main influence statement differs from the group-deletion artifact")

# Restricted-family and shared-roster counts must not replace the primary correction.
shared = ("XLSR-Mamba vs XLS-R+SLS", "XLSR-Mamba vs SSL-AASIST", "XLS-R+SLS vs SSL-AASIST")
for arm, label in (("trial", "Trial"), ("speaker_only", "Speaker-only"),
                   ("attack_only", "Attack-only"), ("speaker_attack", "Joint")):
    row = diag["results"][arm]
    expected = f"| {label} | {row['ssl_six_family']['count']}/6 | {sum(row['pairs'][p]['separated'] for p in shared)}/3 |"
    if SUPPLEMENT_RAW.count(expected) != 1:
        fail(f"TABLE family/roster sensitivity missing: {expected}")
for p in lost:
    if _blk(p) == "ssl" and "XLSR-Conformer" not in p:
        fail("VALUE a primary within-SSL loss no longer involves Conformer")
for p, corpus, source_label in (("XLSR-Mamba vs SSL-AASIST", "vcc2018", "VCC2018"),
                                ("XLS-R+SLS vs SSL-AASIST", "vcc2020", "VCC2020")):
    deleted = source["leave_one_corpus_out"]["by_corpus"][corpus]["pairs"][p]
    full = matched["speaker_attack"]["pairs"][p]
    expected = f"| {p} | {source_label} | {full['delta_eer_pts']:.3f} | {deleted['delta_eer_pts']:.3f} | no |"
    if deleted["resolved"] or SUPPLEMENT_RAW.count(expected) != 1:
        fail(f"TABLE named source-deletion result missing or changed: {expected}")

# 8c. Forced by the reconsideration's new stability, composition and inline claims.
# Preserve historical evidence checks above; bind the newly archived checks as well.
revision_conditional = load(ROOT / "evidence/revision-conditional.json")
revision_fresh = load(ROOT / "evidence/revision-fresh.json")
revision_verified = load(ROOT / "evidence/revision-mc-verification.json")
if (revision_verified["status"] != "PASS"
        or revision_verified["conditional_resamples_checked"] != 3000
        or revision_verified["fresh_streams_checked"] != 15
        or revision_verified["conditional_max_arithmetic_difference"] > 2e-12):
    fail("GATE revision Monte Carlo independent arithmetic check failed")
for name, digest in revision_verified["bindings"].items():
    if sha256(ROOT / "evidence" / name) != digest:
        fail(f"HASH revision Monte Carlo binding changed: {name}")
if revision_verified["verifier_sha256"] != sha256(ROOT / "code/verify_revision_mc.py"):
    fail("HASH revision independent verifier changed")
if (revision_conditional["driver_sha256"] != sha256(ROOT / "code/revision_mc.py")
        or revision_fresh["contract"]["driver_sha256"] != sha256(ROOT / "code/revision_mc.py")):
    fail("HASH revision Monte Carlo producer changed")
if (revision_conditional["master_seed"], revision_conditional["resamples"], revision_conditional["B"],
        revision_conditional["arm_order"]) != (2026092001, 1000, 5000, ["trial", "speaker_attack", "speaker_only"]):
    fail("CONTRACT conditional Monte Carlo protocol changed")
if (revision_fresh["contract"]["master"], revision_fresh["contract"]["runs"],
        revision_fresh["contract"]["B"], revision_fresh["contract"]["arms"]) != (
        2026092002, 5, 5000, ["trial", "speaker_attack", "speaker_only"]):
    fail("CONTRACT fresh primary streams changed")
if (revision_fresh["contract"]["inputs_sha256"] != diag["inputs_sha256"]
        or revision_fresh["estimator_validation_max_error"] != 0):
    fail("GATE fresh streams must share the original inputs and estimator")
for arm, expected_counts in (("trial", {"all": 26, "ssl": 5, "organizer": 5, "cross": 16}),
                             ("speaker_attack", {"all": 18, "ssl": 2, "organizer": 0, "cross": 16}),
                             ("speaker_only", {"all": 18, "ssl": 2, "organizer": 0, "cross": 16})):
    cond = revision_conditional["arms"][arm]
    if cond["changed_indicators"] or cond["count_ranges"] != {k: [v, v] for k,v in expected_counts.items()}:
        fail(f"VALUE conditional stability changed: {arm}")
    if revision_verified["fresh_changed_pairs_by_stream"][arm] != [[], [], [], [], []]:
        fail(f"VALUE fresh indicator stability changed: {arm}")
    for repeat in range(5):
        row = revision_fresh["results"][f"{arm}_{repeat}"]
        if row["counts"] != expected_counts or any(
                row["pairs"][p]["separated"] != diag["results"][arm]["pairs"][p]["separated"]
                for p in diag["results"][arm]["pairs"]):
            fail(f"VALUE fresh stream changed its primary indicators: {arm}/{repeat}")
expected_composition = {"group": "VCC2SM3", "n": 315, "bona_fide": 315, "spoof": 0, "sources": ["vcc2018"]}
if (revision_fresh["composition"] != expected_composition or revision_verified["composition"] != expected_composition
        or revision_verified["protocol_sha256"] != diag["inputs_sha256"]["protocol_key"]):
    fail("VALUE influence-group class composition differs from independently parsed protocol")
require_number("5.2", joint["sd"] / diag["results"]["trial"]["pairs"][pair]["sd"], 1,
               "paired SD increase in abstract and conclusion")
for literal, endpoint in zip(("-4.252", "-0.277"), _ar["clustered"]["pairs"][_k]["ci95_pointwise"]):
    require_number(literal, endpoint, 3, "Arena pointwise qualification")
for literal, value in (("14,869", ablation["inputs"]["n_bonafide"]),
                       ("519,059", ablation["inputs"]["n_spoof"])):
    if f"{value:,}" != literal or literal not in TEX_RAW:
        fail(f"VALUE primary table class count changed: {literal}")
require_number("98.0", 100 * exp112["arms"]["twoway"]["coverage"], 1,
               "inline supportive speaker-attack percentile coverage")
for literal, arm in (("37/200", "iid"), ("196/200", "twoway")):
    if literal != f"{exp112['arms'][arm]['covered']}/{exp112['R']}" or literal not in TEX_RAW:
        fail(f"VALUE inline simulation count changed: {arm}")
if re.search(r"\bS[2-8](?:[a-e]|\b)", TEX):
    fail("SCOPE submission again depends on supplement section locators")
if (ROOT / "SUPPLEMENT.md").read_text() != (PAPER / "SUPPLEMENT.md").read_text():
    fail("RELEASE root and paper supplements differ")

# 9. Scientific scope obligations and retired formulations.
# Scientific boundaries follow their revised locations; every one is deletion-tested.
for text, why in (
    ("fixed-score sensitivity bands", "identified scientific object"),
    ("not confidence about future speakers or attacks", "Method scope"),
    ("not an exact multiway estimator or a coverage guarantee", "Gaussian scope"),
    ("while official repository access was pending", "timing anchored to access state"),
    ("A band containing zero establishes neither equality nor a deployment ranking", "zero inclusion boundary"),
    ("Publish the group memberships and weighting rules needed to reproduce the check", "report observed units"),
    ("The sixteen SSL-versus-baseline contrasts survive the tested resampling laws and fixed weighting rules", "tested scope"),
    ("distinct from the nested-observation designs studied in", "crossed versus nested design"),
    ("without population-coverage guarantees", "population/rank boundary"),
    ("A separate eleven-detector roster on the same corpus changes from 52 of 55 to 38 of 55 bands excluding zero", "abstract separate-roster result"),
    ("for SpoofCeleb only, the archived plan samples the 91,130 trial indices from the pooled list with replacement", "trial-law exception"),
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
