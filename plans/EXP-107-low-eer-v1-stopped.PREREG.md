# EXP-107 — Low-EER crossed-cluster inference repair (design v1, stopped)

Frozen 2026-08-16 after EXP-105 grid 26 refuted the original all-regime
coverage claim, but before implementing or evaluating any candidate repair.
The completed and still-running EXP-105 cells are a development set; none may
be used as confirmation evidence.

**Execution status: STOPPED before implementation.**  The adversarial design
audit at the end of this record found that v1 does not yet justify inference
for its declared estimand and cannot literally reuse the saved EXP-105 state.
No development or confirmation result may be generated under this contract.

- **Line/idea:** M1 · **Priority:** critical method repair
- **Primary hypothesis:** a smoothed-EER, asymmetric crossed-bootstrap-t
  interval attains nominal pointwise coverage in both organizer-like and
  low-EER regimes, including the EXP-105 failure configuration.
- **Familywise hypothesis:** the same frozen method, with asymmetric max-t
  calibration shared across all detector pairs, attains nominal simultaneous
  coverage for a multi-system leaderboard.
- **Why now:** EXP-105 showed that the hard-threshold exact-cell normal and
  product-percentile intervals have a strongly asymmetric, non-pivotal lower
  tail at low EER.  Mean estimated variance is approximately correct, but the
  estimated standard error becomes smallest in the most extreme outer
  replicates.  Symmetric variance inflation and basic-bootstrap transforms do
  not repair that mechanism.

## Evidence already seen

The following is known before this freeze and cannot count as confirmation:

- EXP-105 grid 26, low-EER/Gaussian/zero-interaction/Delta=2 points, covered
  `.879/.880/.883` for raw, marginal-adjusted and product-percentile intervals;
- grids 24--26 had raw-studentized 2.5% quantiles about `-2.88`, `-2.95` and
  `-3.38`, versus upper 97.5% quantiles about `1.68`, `1.51` and `1.57`;
- the paper's pre-existing `q=2.981` gives encouraging coverage when applied
  diagnostically, but it is not a pointwise critical value from this DGP and
  will not be used to tune or certify the new method;
- organizer-like EXP-105 cells seen so far are nominal.  All 48 EXP-105 cells,
  including cells that finish after this freeze, belong to development.

## Target estimand

The scientific target remains the population difference in ordinary
non-interpolated EER.  Smoothing is an estimation device, not a change of the
reported estimand.  Every simulation interval is assessed against the known
ordinary-EER population truth.  On real data, ordinary and smoothed point
estimates are both reported and their difference may not be hidden.

Scores are oriented higher-is-bona-fide.  For threshold `t`, define smoothed
false-reject and false-accept functions from Gaussian-kernel CDFs within the
bona-fide and spoof score distributions.  The smoothed EER is their unique
crossing; root bracketing and numerical tolerance are fixed in code before the
development run.

## Frozen candidate class and bandwidth selection

For each system and class, the reference bandwidth is

`0.9 * min(sd, IQR/1.349) * G^(-1/5)`,

where `G` is the number of observed speakers for bona fide and the harmonic
mean of observed speaker and attack counts for spoof.  Zero robust scale falls
back to standard deviation and then to the smallest positive score spacing.
The only candidate multipliers are `{1/16, 1/8, 1/4, 1/2}`.  A common
multiplier is used for all systems, classes, grid cells and real datasets.

The existing 48-cell EXP-105 grid is used once to select the multiplier by this
lexicographic rule:

1. reject a candidate if any smooth root fails or its analytic influence
   approximation has delete-one correlation below `.99` or slope outside
   `[.95,1.05]` on any load-bearing development cell;
2. reject a candidate if the 99th percentile absolute difference between
   smooth and ordinary Delta-EER exceeds `0.10` point in either regime;
3. among survivors, minimize the maximum absolute deviation of pointwise
   coverage from `.95` over the 48 development cells;
4. ties within `.002` maximum deviation choose the smaller multiplier.

If no multiplier survives, the primary method is declared non-viable without
relaxing a gate.  This development selection is reported in full, including
all rejected candidates.  The chosen multiplier is hashed into the
confirmation contract before confirmation seeds are run.

## Primary interval

For each outer dataset:

1. compute the smoothed Delta-EER and its smooth influence values;
2. compute the speaker + attack - observed-cell multiway variance from those
   influence values;
3. draw `B=999` shared speaker × attack product-bootstrap weights in
   development and `B=1999` in confirmation;
4. within every draw, recompute smoothed Delta-EER and its analytic multiway
   standard error; no inner bootstrap is substituted;
5. form `T*=(Delta* - Delta_hat)/SE*` and use its separate lower and upper
   quantiles to construct an asymmetric 95% bootstrap-t interval.

Draws with a nonpositive or nonfinite standard error are counted, reported and
make that outer replicate an interval failure.  No pair-specific fallback or
critical-value clipping is allowed.

The old hard-EER normal, product-percentile, product-basic, symmetric-widest-
tail and `q=2.981` intervals are controls/diagnostics only.  They cannot become
the primary method through favorable development coverage.

## Development campaign

- Reuse all 48 stored EXP-105 outer datasets; do not regenerate them.
- Use the corrected high-precision population truth for Student-t(5) cells.
- Base bootstrap seed `20260901`, derived by cell, replicate, multiplier and
  draw so candidates use aligned random numbers.
- Report coverage, Wilson interval, both miss directions, width, smooth-hard
  discrepancy, studentized quantiles, failed roots/SEs and runtime for every
  multiplier and cell.

Development chooses and freezes one multiplier.  Passing development is not a
scientific result and does not restore any paper claim.

## Independent pairwise confirmation

Regenerate the same fully crossed 48 DGP conditions on the real 21DF incidence
with new outer seed `20260907`, `R=2000` per cell and the frozen method only.
No candidate comparison is computed on these datasets.  Analysis code writes
intervals before aggregate coverage is revealed; shard contracts include all
code and parameter hashes.

Pointwise confirmation requires all of the following:

- every cell's coverage lies in `[.92,.98]`;
- no cell's Wilson lower bound is below `.90`;
- root/SE failure rate is below `.005` in every cell;
- the 99th percentile smooth-hard Delta discrepancy is at most `.10` point in
  both regimes;
- the exact former failure condition (low-EER, Gaussian, zero interaction,
  Delta=2) passes the same rules without special treatment.

## Independent leaderboard-family confirmation

A separate eight-system DGP uses the real 21DF incidence and frozen marginal
scales/correlations from the eight high-provenance score releases.  It includes
organizer-like and low-EER locations, Gaussian and Student-t(5) effects,
interaction shares `{0,.5}` and two truth geometries: all tied, and ordered gaps
`{0,.25,.5,1,2,4,8}` points.  Seed `20260908`, `R=1000` per condition and
`B=1999` shared draws are fixed.

Within each bootstrap draw, calculate all 28 studentized pair statistics.  Use
the empirical 2.5% quantile of the minimum and 97.5% quantile of the maximum
across pairs for one asymmetric 95% max-t band.  Rank intervals are derived
only from that band.

Familywise confirmation requires simultaneous coverage in `[.92,.98]` for
every condition, Wilson lower bound at least `.90`, and false resolution rate
at most `.05` in every tied block.  Pointwise success without familywise
success does not authorize leaderboard or rank claims.

## Interaction-correlation sensitivity

The EXP-105 interaction correlation was fixed.  After primary confirmation,
repeat the low-EER confirmation cells with nonzero interaction at correlations
`{-0.5, 0, 0.5, 0.9}` using seed `20260909`, `R=1000`, without refitting any
method or bandwidth.  Failure narrows the validated correlation scope; it may
not be averaged away.

## Fallback candidate

Crossed m-out-of-n resampling is a separately named fallback, not a silent
repair.  It is attempted only if the smooth bootstrap-t method is non-viable or
fails confirmation, and requires a new preregistration that fixes speaker and
attack subsample rates, scaling and an independent confirmation seed.  No
m-out-of-n result enters this experiment's reading rule.

## Reading rule

- **Confirmed:** both pairwise and leaderboard-family confirmation gates pass.
- **Partially confirmed:** pairwise passes and familywise fails; the method may
  support pre-specified individual contrasts but no leaderboard/rank claim.
- **Refuted:** pairwise confirmation fails, or implementation gates fail.

Until Confirmed, the M1 paper retains formal inference only for the validated
organizer-like baseline reversal; modern low-EER and Arena comparisons remain
descriptive.  A failed repair is reported and never replaced by the best-looking
candidate from confirmation.

## Budget and execution

CPU campaign, checkpointed per outer replicate and resumable.  Runtime and
storage do not truncate the grid.  The campaign does not retrain or rescore any
detector.  GPU work remains governed by the shared queue and is unrelated to
this method-validation experiment.

## Pre-execution adversarial design audit — 2026-08-16

This audit occurred before any EXP-107 code or result.  It freezes why design
v1 was stopped rather than silently rewriting the preregistration after seeing
development coverage.

1. **Estimand mismatch.**  A bootstrap-t distribution for kernel-smoothed EER
   is not automatically an interval for population ordinary EER.  The proposed
   sample smooth--hard discrepancy is not a bound on population smoothing bias.
   Moreover, the `G^{-1/5}` density bandwidth gives an order-`h^2` bias that can
   dominate an order-`G^{-1/2}` standard error.  A successor must either name
   smoothed EER as its estimand or derive an undersmoothed/bias-corrected
   estimator and gate its population bias relative to its SE.
2. **Unavailable development objects.**  EXP-105 checkpointed per-replicate
   estimates, variances and interval endpoints, not full score vectors.  A new
   estimator cannot be computed from those summaries.  A successor must
   regenerate each dataset deterministically from frozen seeds and first prove
   that its ordinary-EER summaries reproduce the saved JSONL records before
   exposing any candidate-method outcome.
3. **Unfrozen smoothing details.**  The exact transformation of scores,
   bandwidth behavior inside weighted draws, scale degeneracy, root bracket,
   tolerance, quantile convention, ties and the influence of an estimated
   bandwidth were not fully defined.  Gaussian smoothing on raw score scale is
   not invariant to monotone score transformations whereas ordinary EER is.
4. **Unspecified weighted studentization.**  A successor must give the full
   weighted empirical distributions, speaker/attack/cell sandwich equations,
   finite-cluster corrections, handling of absent/duplicated clusters and the
   interval formula
   `[Delta_hat - q_.975 SE_hat, Delta_hat - q_.025 SE_hat]`.  It must validate
   weighted analytic SEs against exact recomputation at indices chosen before
   coverage is revealed.
5. **Development overfit.**  Selecting the smallest worst-cell coverage error
   across 48 cells optimizes Monte Carlo noise; the `.002` tie tolerance is
   below the uncertainty from `R=1000`.  A successor should select by theoretical
   and stability gates alone, or use a predeclared one-standard-error rule.
6. **Family DGP ambiguity.**  A successor must freeze explicit valid vectors of
   eight population EERs, PSD cross-system correlation construction, exact
   28-pair truths and pair orientation.  The false-resolution gate is
   `P(any false resolution in a truly tied block) <= .05`, not a mean pairwise
   false-resolution rate.

The successor contract must close items 1--4 before any compute.  It receives a
new version hash and confirmation seeds; this stopped v1 remains immutable as
the design-audit trail.
