# EXP-116 — Report

- **Status:** confirmed (384/384 cross-cohort indicators equal to 1, the registered reading
  "all cross-cohort pairs separated under all rules and laws").
- **Evidential status:** post-result verification of a manuscript sentence, disclosed in
  the PREREG. Not prospective confirmation.
- **Budget:** estimated 10 min wall / 106 core-min; actual 39.1 min wall (2,347.6 s) /
  about 470 core-min, 12 processes. Per-cell wall 1,130–1,183 s at B=5000. The
  single-process micro-benchmark (0.053 s per PW replicate) under-predicted by about 4×
  with 12 concurrent processes on a machine at load 17; the workers were CPU-bound with no
  swap or I/O wait, consistent with memory-bandwidth contention on 533,928-element fancy
  indexing. Calibration anchor: **0.23 s per 8-system PW replicate per process at 12-way
  concurrency**, versus 0.053 s alone.
- **What ran:** `uv run python run_policy_bands.py` with `EXP116_PROCS=12`, 2026-09-09
  00:19–00:58 -03, on repository head `23b49e0` with an unclean working tree (the EXP-116
  directory itself and unrelated untracked files; recorded in `RESULTS.json`
  `working_tree_dirty_paths`). Environment: Python 3.11.15, numpy 2.4.6, scipy 1.17.1
  (`pyproject.toml`; scipy added before the first successful run because EXP-108's
  `analyze.py` imports it; the first launch failed at import and produced no output).
  Hashes of PREREG, script and pyproject in `FREEZE.sha256`; result SHA-256
  `d0bbafbc3a505dcf99a9d0ff683d6651279fba098df58a3549b9b3ec0ba18cdd`.

## Gates passed before resampling

- Policy contract: all 12 rebuilt weight vectors match `contract.json` `sha256_float64_le`.
- Estimator: full-data ΔEER for 12 rules × 28 pairs reproduces EXP-108
  `delta_eer_pct_points` with maximum deviation 0.000e+00 points.
- Empirical-weight cell (`B0xS0`) reproduces the manuscript's counts: trial 26/28
  (16 cross + 5 within-SSL + 5 within-baseline), PW 18/28 (16 + 2 + 0).

## Results

Primary statistic: cross-cohort separation indicators, 16 pairs × 12 rules × 2 laws.

| | separated | total |
|---|---:|---:|
| cross-cohort indicators | **384** | 384 |

Every one of the 16 SSL-versus-organizer-baseline pairs has a 95% simultaneous max-t band
excluding zero under every registered weighting rule and under both perturbation laws.
`q_.95` ranges 2.904–3.005 across the 24 cells. The cross-cohort band endpoint closest to
zero over all 384 is −12.79 points (SSL-AASIST vs RawNet2, rule B0xS1, PW law), so no
indicator is within Monte Carlo reach of flipping.

Descriptive within-cohort counts (no registered reading; reported for completeness):

| rule | trial within-SSL | trial within-baseline | PW within-SSL | PW within-baseline |
|---|---:|---:|---:|---:|
| B0xS0 | 5/6 | 5/6 | 2/6 | 0/6 |
| B0xS1 | 6/6 | 5/6 | 2/6 | 0/6 |
| B0xS2 | 5/6 | 5/6 | 2/6 | 0/6 |
| B0xS3 | 5/6 | 3/6 | 2/6 | 0/6 |
| B1xS0 | 5/6 | 3/6 | 2/6 | 0/6 |
| B1xS1 | 6/6 | 3/6 | 2/6 | 0/6 |
| B1xS2 | 6/6 | 3/6 | 2/6 | 0/6 |
| B1xS3 | 5/6 | 6/6 | 2/6 | 0/6 |
| B2xS0 | 5/6 | 3/6 | 2/6 | 0/6 |
| B2xS1 | 6/6 | 3/6 | 2/6 | 0/6 |
| B2xS2 | 5/6 | 3/6 | 2/6 | 0/6 |
| B2xS3 | 5/6 | 6/6 | 2/6 | 0/6 |

Under PW resampling the within-cohort pattern is identical for all 12 rules (2/6 and 0/6).
Under trial resampling the within-baseline count moves between 3/6 and 6/6 with the rule,
which is the same message as the manuscript's: within-cohort structure is conditional on
the weighting.

## Verdict rationale

The registered reading required all 384 cross-cohort indicators to equal 1. All do. The
manuscript may state that the 16 cross-cohort separations survive both bootstraps under
every one of the 12 weighting rules. This is a fixed-score sensitivity statement under the
declared laws; it carries no population coverage.

## Deviations

- scipy added to the environment pins before the first successful run (import failure,
  no output produced); `FREEZE.sha256` was rewritten to cover the corrected
  `pyproject.toml`. PREREG and script hashes unchanged.
- None in method, seeds, B or reading.

## Artifacts

All inside the repository: `RESULTS.json` (bands, indicators, q, seeds, input hashes,
producer head), `run.log`, `FREEZE.sha256`. Inputs are the official DF key metadata and
the eight score files already recorded by EXP-108.

## Consequence

Manuscript edits E1 and E12 (abstract and conclusion) use the strong form; §4
"Alternative weights" gains one sentence reporting this result with its post-result
status. The supplement gains the 24-cell table.
