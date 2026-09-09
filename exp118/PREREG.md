# EXP-118 — SpoofCeleb under the class-stratified trial law

- **Line/idea:** M1 · **Priority:** supporting (manuscript specification check)
- **Pre-registered:** 2026-09-09, before any class-stratified trial bootstrap on SpoofCeleb
  was computed. CPU only. No GPU. Post-result: the pooled-law result (EXP-114, 6/6) is known.
- **Why now:** the 2026-09-09 exact-PDF audit (round 3, finding 1) noted that the manuscript's
  method section defines the trial bootstrap as class-stratified while EXP-114's archived
  plan draws the 91,130 SpoofCeleb trial indices from the pooled list. The manuscript now
  declares the exception. This experiment measures whether the declared law and the
  class-stratified law give the same separation vector on SpoofCeleb, so the reader knows
  whether the exception matters numerically.

## Hypothesis

On the 91,130-trial SpoofCeleb evaluation grid with the four EXP-114 detectors, the
class-stratified trial bootstrap (9,113 bona-fide and 82,017 spoof indices drawn with
replacement within class) separates the same six pairs as the pooled trial bootstrap of
record (6/6).

## Method

Inputs: the EXP-114 manifest of record (SHA-256
`008371adaeb300401357a58035d3c4ac9e1c440abe804ceab8ccd1bdc84b2544`) and the four original
EXP-114 score tables from the run archive (`EXP-114-run-artifacts.tar`). Estimator: the
sealed EXP-101 weighted EER (class-normalized cumulative masses, first minimum of |FRR−FAR|,
mean of the two rates, mergesort orders), all six pairwise contrasts, one 95% max-t
critical value per arm, B=5000. Two arms in one process: (A) pooled trial law as in EXP-114
(seed 20260829, identical RNG use: `rng.integers(0, n, size=n)`), which must reproduce
EXP-114's arm-A bands to 1e-9 points before the new arm is emitted; (A') class-stratified
trial law, seed 20260909.

## Registered reading, fixed before computation

| A' result | Reading |
|---|---|
| 6/6 separated, same vector as A | the trial-law exception is declared and numerically immaterial on SpoofCeleb; the supplement reports both counts |
| any other vector | the exception is material; the manuscript reports the class-stratified count alongside the pooled one and says which pairs differ |

## Budget

91,130 trials × 4 systems: about 0.005 s per replicate; two arms × 5,000 replicates ≈ 1 min.

## Amendment 1 (2026-09-09, before the stratified arm ran)

The estimator gate required the pooled arm to reproduce EXP-114's arm-A bands to 1e-9
points. It reproduced them to 2.39e-6 points: EXP-114 normalizes class masses before the
cumulative sums (`normalized_class_mass` then `eer_from_class_mass`) while this script uses
the sealed EXP-101 `weighted_eer` on raw counts, so the two functionals differ by float
rounding order, not by definition. No stratified replicate had been computed when this was
found. The gate is amended to 1e-5 points plus exact equality of the six separation
indicators; the original tolerance is left visible above.
