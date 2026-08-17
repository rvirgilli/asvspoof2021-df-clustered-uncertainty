# Committed derived inputs

This directory contains the machine-readable outputs consumed by
`code/make_audit_package.py` and `code/check_numbers.py`. They are committed so
the paper-to-result checker runs in a clean clone without downloading the
third-party score files.

The generating-script map is explicit below. Regenerating the full campaign
requires the score files listed in `data/README.md`; regenerating only
`audit/audit.json` requires those score files plus these committed derived
outputs. The two operations are intentionally distinct in the top-level README.

| Derived artifact | Generating script |
|---|---|
| `results_pairs.json` | `code/m1_campaign.py` |
| `results_selection.json` | `code/exp101_selection.py` |
| `results_matched_iid.json` | `code/exp101_matched_iid.py` |
| `results_matched_iid.provenance.json` | historical/released byte-identity ledger for the matched diagnostic |
| `results_organizer_test.json` | `code/exp101_organizer_test.py` |
| `results_scaling.json` | `code/exp101_scaling.py` |
| `results_widths.json` | `code/exp101_widths.py` |
| `results_floor.json` | `code/exp101_floor.py` |
| `results_floor_ci.json` | `code/exp101_floor_ci.py` |
| `results_icc.json` | `code/exp101_icc.py` |
| `results_source.json` | `code/exp101_source.py` |
| `results_verdict_ci.json` | `code/exp101_verdict_ci.py` |
| `results_coverage_real.json` | `code/exp101_coverage_real.py` |
| `results_contingency.json` | `code/m1_contingency.py` |
| `results_dgp_fit.json` | `code/exp101_dgp_fit.py` |
| `results_multiway_real.json` | `code/analyze_multiway.py` |
| `results_coherent_jackknife.json` | `code/coherent_jackknife.py` |
| `provenance_coherent_jackknife.json` | historical/released byte-identity ledger for the coherent diagnostic |
| `results_arena.json` | `code/analyze_arena.py` |
| `results_coverage_interaction.json` | `code/coverage_interaction.py` |
| `results_coverage_interaction_recalibrated.json` | `code/recalibrate_truth.py` |
| `results_crosspath_gate.json` | `code/verify_crosspath_gate.py` |
| `results_coverage_diagnostics.json` | `code/diagnose_low_eer.py` |
| `results_exp105_verified.json` | `code/aggregate_verified.py` |
| `provenance_exp105.json` | byte-identity ledger checked by `code/check_numbers.py` |
| `incidence_strata.json` | frozen source/task incidence audit consumed by the scientific checker |
| `results_composition.json` | frozen 12-policy composition multiverse |
| `verification_composition.json` | independent reconstruction record for the composition multiverse |
| `secondary_v2_results.json` | post-failure constructive witness search |
| `secondary_v2_verification.json` | three-backend reconstruction of constructive witnesses |

Every released script reads and writes derived results under `derived/`; the
clean-clone checker rejects the former internal-tree convention of placing JSON
beside source files under `code/`. Long bootstrap campaigns checkpoint only in
the documented external run roots.

The committed Arena B=5000 JSON records both the original internal-layout
generation-script hash and the released path-adapted analyzer hash. The numeric
implementation is the same, but that distinction is preserved rather than
retroactively claiming that the released bytes emitted the historical file.

The five EXP-105 result files follow the same rule. Canonical JSONs preserve
the internal campaign hashes, while `provenance_exp105.json` records and the
checker verifies both the historical bytes and the released path-adapted source.
The 48,000 checkpoint rows are too large and granular for this repository;
`results_exp105_verified.json` records the SHA-256 and row count of each external
contract, JSONL shard and cell result. The full campaign is therefore content-
addressed without pretending that the clean-clone checker recomputes it.

The matched and coherent post-audit diagnostics also preserve two identities. Their
canonical JSONs retain hashes of the exact internal campaign bytes, while their provenance
sidecars seal the released path-adapted scripts separately. The checker refuses to conflate
those identities. Both diagnostics are descriptive fixed-data sensitivity outputs.

EXP-105's authoritative status is `refuted`: no estimator covers inside
`[.92,.98]` across the whole grid. This refutes low-EER generalization. Every
organiser-like simulated cell is inside the frozen coverage band and all three
then-candidate variants preserve the full-pool 0/6 numerical output, but neither
fact validates population inference for the real organiser block.

`results_multiway_real.json` contains the exact observed-cell correctness audit.
`results_pairs.json` is retained only because the Bengio reconstruction checks its
paired-permutation diagnostic; fields marked superseded there are not paper inputs.

The ASVspoof 5 fixed-family result is packaged separately under `audit/asv5/`.
Its standard-library verifier rehashes the 698-record input manifest and binds
the portable run contract and result to `audit/audit.json`.
