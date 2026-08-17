# EXP-105 — M1 multiway intersection and interaction correctness audit

Frozen 2026-08-16 before computing a speaker×attack-cell variance term or
running the interaction-stress simulation described below.

- **Line/idea:** M1 · **Priority:** critical correctness
- **Hypothesis:** an explicit speaker×attack intersection estimator preserves
  nominal 95% coverage under interaction stress and does not reverse the
  existing product-bootstrap conclusion that the six organizer-baseline pairs
  are unresolved.
- **Why now:** EXP-101's second estimator uses
  `V_speaker + V_attack - V_iid`. The i.i.d. term contains bona-fide variation
  that is not part of the spoof-side speaker×attack intersection, and its
  direction was asserted as conservative without proof. The finite-attack
  speaker component also contains speaker×attack interaction divided by the
  number of attacks, so it cannot be called the pure-speaker asymptote until that
  interaction is estimated or bounded.

## Estimands and dependence units

The primary estimand remains paired ΔEER over speakers and spoof attacks
exchangeable with the evaluation design. Speakers index both classes; attacks
index spoof trials only. The intersection is therefore the observed spoof-side
speaker×attack cell. Bona-fide observations receive no artificial common attack
label: their second-dimension singleton terms cancel from the multiway
inclusion--exclusion expression.

## Estimators fixed before results

For every pair, all calculations use the same non-interpolated EER rule.

1. **Product bootstrap:** existing speaker weights multiplied by attack weights
   on spoof trials, speaker weights only on bona fide trials.
2. **Current proxy, diagnostic only:**
   `V_speaker + V_attack - V_iid`, with the existing max floor. It cannot be the
   final correctness estimator regardless of outcome.
3. **Explicit-cell multiway jackknife:**
   `V_speaker + V_attack - V_speaker_attack`, where the three terms are computed
   from delete-one speaker, delete-one spoof attack and delete-one observed
   spoof speaker×attack cell refits. Both the raw inclusion--exclusion result and
   the positive-semidefinite floor `max(V_multiway, V_speaker, V_attack)` are
   reported; the floor may not be hidden.
4. **Linearized multiway CRVE:** numerical influence values for ΔEER are
   validated against finite leave-one perturbations, then aggregated by speaker,
   spoof attack and observed spoof speaker×attack cell with CGM
   inclusion--exclusion and finite-cluster corrections. This is the primary
   analytic estimator if its linearization checks pass.

The implementation must report the number and size distribution of observed
cells, every variance component, negative raw inclusion--exclusion cases, and
all 28 verdicts. No pair-specific choice among estimators is allowed.

## First-principles correctness gates

Before looking at scientific verdicts:

1. Trial influence contributions must sum to ΔEER to numerical tolerance after
   centering/scaling.
2. Linearized changes must correlate at least 0.99 with exact delete-one changes
   across all speaker and attack deletions; slope must lie in [0.95, 1.05]. This
   is evaluated per pair, and failures are printed rather than averaged away.
3. On an additive Gaussian design with zero interaction, the explicit-cell
   multiway variance must match the direct Monte Carlo variance within 10% at
   `R=2000`. The cell term is reported separately as the
   inclusion--exclusion correction; it is not itself a total-variance
   estimator and is therefore not compared to the total Monte Carlo variance.
4. On the exact 21DF incidence, independently implemented product-bootstrap and
   analytic code paths must agree on score orientation, point ΔEER and cluster
   counts exactly.

If gate 1 or 2 fails for any load-bearing pair, the linearized estimator is not
used for claims. If gate 3 fails, the explicit-cell method is not called
validated and only product-bootstrap results survive.

## Interaction-stress coverage grid

Scores are generated on the real 21DF trial incidence for two correlated
systems. The grid is fully crossed:

- EER regime: organizer-like and low-EER;
- speaker×attack interaction share of spoof random-effect variance:
  `{0, 0.25, 0.50, 0.75}`;
- random-effect tails: Gaussian and standardized Student-t(5);
- true ΔEER: `{0, 0.5, 2.0}` points.

For each of 48 cells, use `R=1000` outer replicates. Product-bootstrap intervals
use `B=500` shared draws per replicate; analytic methods use the same generated
datasets. Seeds are derived from base seed `20260824` and the fixed grid index.
Report coverage with Wilson intervals, median width and failure rate.

## Reading rule

- **Confirmed:** at least one non-proxy estimator has 95% coverage inside
  `[0.92,0.98]` in every grid cell, and that same estimator leaves all six
  organizer-baseline pairs unresolved.
- **Partially confirmed:** no estimator passes the entire grid, but product
  bootstrap never falls below 0.90 and the six-pair conclusion is invariant.
- **Refuted:** every non-proxy estimator has coverage below 0.90 in at least one
  grid cell, or a validated estimator resolves an organizer-baseline pair.

The coverage bounds are detectable at `R=1000`: at true coverage 0.95 the
Monte-Carlo standard error is 0.0069 and an approximate 95% interval is
±0.0135. The operationally meaningful failure threshold is 0.90; it is over
seven Monte-Carlo standard errors below nominal.

## Floor/interactions consequence

Only after the gates pass, decompose the finite-attack speaker term into the
pure-speaker main effect and speaker×attack interaction divided by `A`. Recompute
the asymptotic floor and its shared-speaker joint-count bootstrap from the pure
component. Until then the paper calls the existing quantity the finite-`A`
speaker component and makes no `A→∞` claim.

## Budget

CPU campaign. Runtime and storage do not determine whether the full grid runs.

## Blind clarification — 2026-08-16, before coverage outcomes

The original wording of gate 3 said both "the cell term and multiway variance"
must match one direct Monte Carlo variance. That is dimensionally wrong: the
cell term is subtracted from the two marginal cluster components and is not an
estimate of total sampling variance. The corrected gate above compares the
resulting multiway total to direct Monte Carlo and still reports the cell term.
This clarification was made after the real-data component table was computed
but before any additive-gate or interaction-grid simulation result existed. It
does not change the interaction grid, its `R`, its `B`, or the reading rule.

## Post-result adversarial audit record — 2026-08-16

This section was added after grids 24--26 had completed and therefore changes
neither the frozen hypothesis nor its reading rule.  Grid 26 (low-EER,
Gaussian, zero interaction, true delta 2.0 points) gave coverage .879 raw, .880
for the pairwise marginal-component adjustment, and .883 product.  Because all
three non-proxy estimators are below .90, the original reading rule is
**REFUTED** irrespective of the remaining cells.  The full grid continues to
map the failure; no later result can relabel the original hypothesis confirmed.

The same audit identified four closure issues that will be reported as
deviations rather than repaired silently:

1. In Student-t cells, the frozen locations came from finite Monte Carlo
   quantiles while coverage was marked against nominal rather than achieved
   population delta.  The saved JSONL rows remain valid; a separately hashed,
   high-precision population recalibration will recompute coverage without
   regenerating any dataset or interval.
2. Gate 1's wording is mathematically wrong for a centered influence function:
   its contributions sum to zero, while point estimate plus contributions
   reconstructs the statistic.  The implementation checks zero.  The
   linearized CRVE failed gate 2 independently and remains excluded.
3. Gate 4 was not executed before real-data verdicts.  A separately released
   cross-path check now compares all point EERs/deltas, incidence partitions and
   real product weights; it is an audit check, not a retroactive blind gate.
4. Interaction correlation was not a grid factor and was fixed in code to the
   average of the calibrated speaker and attack correlations.  Coverage results
   are conditional on that value, not general robustness to interaction
   correlation.

The paper fallback is frozen now: coverage-calibrated claims are restricted to
the organizer-like regime if that pre-specified subgrid remains nominal.
Low-EER modern-system and Arena intervals are descriptive, and the two
within-SSL ``resolved'' verdicts are withdrawn.  The finite-A speaker component
does not identify the missing-cell interaction distribution, so no pure-speaker
or A-to-infinity floor will be restored.

Before seeing the remaining cells, the following diagnostics were fixed for
every grid cell: lower/upper-tail miss counts, point bias, mean estimated
variance over direct Monte Carlo variance, oracle-SD coverage, studentized
quantiles, association between absolute error and estimated variance, basic
bootstrap coverage, and coverage obtained by applying the paper's pre-existing
28-pair critical value `q=2.981` to the exact-cell SE.  The last is explicitly a
post-hoc diagnostic relative to this preregistration: it came from the real-data
product covariance, the simulated grid has one contrast, and it cannot rescue
the Refuted verdict.

Any new low-EER method uses this grid only for development.  Its specification
and tuning are frozen separately and its coverage is evaluated on new seeds;
choosing a critical value or interval by whichever result passes this grid is
prohibited.
