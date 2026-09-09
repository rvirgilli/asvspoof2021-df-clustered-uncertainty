# EXP-118 — Report

- **Status:** confirmed against the registered reading "exception declared and numerically
  immaterial": the class-stratified trial bootstrap separates 6/6 SpoofCeleb pairs, the same
  vector as the pooled law of record.
- **Budget:** estimated ~1 min; actual 31.3 s (one process), 2026-09-09 03:04 -03.
- **What ran:** `uv run python run_trial_laws.py inputs` on the EXP-114 manifest of record
  (SHA-256 `008371ad…`) and the four original EXP-114 score tables from the run archive
  (hashes in `RESULTS.json`); sealed EXP-101 weighted EER; B=5000; pooled seed 20260829,
  stratified seed 20260909. Result SHA-256
  `8e55047790c3472cbf96c3309f0d62302f3348639ebe6728f1ff2bc24e86541a`.
- **Estimator gate:** the pooled arm reproduces EXP-114 arm A to 2.39e-6 points with the
  same six indicators (Amendment 1 explains the tolerance).

## Results

| pair | pooled band (EXP-114 law) | class-stratified band | separated |
|---|---|---|---|
| aasist vs ssl_aasist | [30.449, 31.971] | [30.441, 31.979] | both |
| aasist vs sls | [32.647, 34.187] | [32.641, 34.193] | both |
| aasist vs xlsr_mamba | [29.418, 31.291] | [29.411, 31.297] | both |
| ssl_aasist vs sls | [1.592, 2.821] | [1.600, 2.814] | both |
| ssl_aasist vs xlsr_mamba | [−1.446, −0.266] | [−1.455, −0.257] | both |
| sls vs xlsr_mamba | [−3.771, −2.355] | [−3.790, −2.336] | both |

Endpoints move by at most 0.02 points; every indicator is unchanged.

## Deviations

Amendment 1 to the estimator-gate tolerance (float rounding order between two equivalent
EER functionals), made before any stratified replicate existed and left visible in the
PREREG.

## Consequence

The manuscript keeps the declared exception (§3.2) and adds that a class-stratified
recomputation separates the same 6/6; the supplement carries the table.
