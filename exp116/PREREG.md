# EXP-116 — do the 16 cross-cohort separations survive every fixed weighting rule?

- **Line/idea:** M1 · **Priority:** supporting (manuscript claim verification)
- **Pre-registered:** 2026-09-09, before any band under a nonempirical weighting rule was
  computed. CPU only, on score files already on disk. No GPU.
- **Status disclosed up front:** this is a **post-result** verification, not prospective
  confirmation. The 12 weighting rules, their point-ordering outcomes (EXP-108) and the
  bootstrap bands under empirical weights (EXP-101/EXP-111) were all known when this plan
  was written. What was never computed, and what the current manuscript nonetheless asserts
  in its abstract and conclusion, is whether the *separation event* (simultaneous band
  excluding zero) holds for the cross-cohort pairs under each weighting rule. The 2026-09-08
  exact-PDF audit (finding S2) identified that gap. This experiment measures it instead of
  narrowing the sentence.

## Hypothesis

Under each of the 12 registered score-blind weighting rules of EXP-108, and under both
declared perturbation laws (class-stratified trial resampling; speaker×attack product
weights), every one of the 16 SSL-versus-organizer-baseline pairs has a 95% simultaneous
max-t band that excludes zero.

## Method

Identical to the manuscript's procedure bands, with the weighting rule supplying the base
weight of every trial.

1. **Trials and rules.** The 533,928 eval trials and the 12 weight vectors are rebuilt
   score-blind by `build_policy_weights` (EXP-108 `build_contract.py`) and validated against
   the frozen `contract.json` hashes (`sha256_float64_le`). Any drift aborts the run.
2. **Scores.** Loaded by EXP-108 `load_scores` under its eval identity gate.
3. **Estimator gate before any resampling.** For every rule, the full-data
   $\Delta\mathrm{EER}$ of all 28 pairs, computed with this script's sorted-order weighted
   EER, must reproduce EXP-108 `policies[*].delta_eer_pct_points` to 1e-9 points. The run
   aborts otherwise. This binds the new implementation to a known quantity before it emits
   any new one.
4. **Perturbation laws**, per rule $w^0$ (class-normalized, positive):
   - *trial*: within each class, draw multinomial counts $c_i$ over its trials
     (n draws with replacement); replicate weight $w_i = w^0_i c_i$.
   - *PW*: draw 93 speaker multiplicities $c_s$ and 110 spoof-attack multiplicities $c_a$
     with replacement; $w_i = w^0_i c_{s(i)}$ for bona fide and $w_i = w^0_i c_{s(i)} c_{a(i)}$
     for spoof.
5. **Bands.** $B=5000$ per (rule, law); seed $20260909 + 100\,k + \ell$ for rule index $k$
   and law index $\ell$. Each replicate refits every system's non-interpolated EER threshold.
   $s_p=\operatorname{sd}_b(\Delta^{(b)}_p)$, $q_{.95}$ = empirical 95th percentile of
   $\max_p|\Delta^{(b)}_p-\bar\Delta_p|/s_p$ over the 28 pairs, band
   $\hat\Delta_p\pm q_{.95}s_p$ with $\hat\Delta_p$ the full-data contrast under $w^0$.
   Separation indicator $I_p=1$ iff the band excludes zero.
6. **Output.** `RESULTS.json`: per (rule, law) the 28 bands, indicators, $q_{.95}$, counts
   by block (16 cross, 6 within-SSL, 6 within-baseline); the 384 cross-cohort indicators;
   input hashes (metadata, eight score files, `contract.json`, EXP-108 `results.json`),
   script hash, producer git head, seeds, wall time.

## Registered reading, fixed before computation

| Cross-cohort indicators equal to 1 | Reading |
|---|---|
| 384 / 384 | The manuscript may state that all 16 cross-cohort pairs remain separated under both bootstraps and all 12 weighting rules. |
| any fewer | The manuscript states point-order stability only (the narrowed wording already drafted), and names every (pair, rule, law) that fails. |

No intermediate reading. Within-cohort results are reported descriptively and change no
sentence.

## Kill criterion and detectability

The bar is a deterministic property of a declared procedure (an indicator vector), not a
significance test, so `bar_check.py` does not apply. The stochastic component is Monte
Carlo: at $B=5000$ the standard error of a 95th-percentile critical value is about 1% of
its value, and cross-cohort point gaps (19.5–23.7 points) exceed the empirical-weight PW
half-widths (about 6 points) by more than a factor of three, so a flip caused by Monte
Carlo noise alone would require a band endpoint within roughly 0.1 point of zero. If any
cross-cohort indicator is 0, the cell is rerun once with seed offset $+1000$ **for
reporting only**; the registered reading uses the first seed.

## Budget

Micro-benchmark 2026-09-08 on the real data: 0.053 s per PW replicate over eight systems
(argsort precomputed). 24 cells × 5000 replicates ≈ 106 core-minutes; 12 parallel
processes ≈ 10 min wall. Memory per process < 200 MB.

## What this does not establish

Nothing about population coverage or about weighting rules outside the registered 12. A
384/384 result is a fixed-score sensitivity statement under the declared laws, exactly as
the rest of the manuscript.
