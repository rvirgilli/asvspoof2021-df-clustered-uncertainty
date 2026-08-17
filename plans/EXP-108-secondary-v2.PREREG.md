# EXP-108 secondary v2 — multi-backend constructive source/task witnesses

Frozen **2026-08-16 16:15 BRT**, after the primary EXP-108 result and after two
failed secondary verifier attempts.  This is not a fresh confirmation dataset:
the scores and earlier candidate outcomes are known.  Its valid scientific
object is therefore strictly constructive:

> exhibit an explicit positive source/task mass vector that deterministically
> changes a fixed pair ordering under multiple fully specified EER evaluators.

An accepted vector proves existence within its reported distance.  Search
failure does not prove stability; the smallest found distance is an upper bound,
not a global minimum, confidence bound or preregistered primary result.  Nothing
in v2 can change the primary `LOCAL COMPOSITION FRAGILITY` classification.

## Known failure mechanism

Secondary attempt 1 contracted a fast grouped-CDF candidate to machine precision
at the sign boundary.  For CQCC-GMM, two adjacent threshold positions had gaps
approximately `-9.63265e-7` and `+9.63268e-7`.  Grouped arithmetic selected one;
direct per-trial accumulation selected the other, changing a pair delta from
`+6.816e-5` to `-2.817e-5` point.  Attempt 2 added a fixed `1e-4` path step, but
another candidate still failed direct sign verification.  Both complete output
hashes remain in the failure records; no candidate from either attempt is reused
as evidence.

The repair is not a larger tuned margin.  It changes acceptance from a fast-
backend sign to prospective **multi-backend consensus**, tests multiple complete
directions rather than one contracted boundary, and treats rejected candidates
as ordinary search output rather than as a fatal experiment-wide failure.

## Fixed composition domain

The three bona-fide groups are `asvspoof`, `vcc2018`, `vcc2020`; the five spoof
groups are `asvspoof`, `vcc2018/HUB`, `vcc2018/SPO`, `vcc2020/Task1`,
`vcc2020/Task2`.  Candidate vectors `q_b` and `q_s` lie in the interiors of their
respective simplexes.  Trials retain uniform empirical conditional mass within
their top-level group.  No row is removed.

All eight systems and 28 oriented pairs from the primary preregistration remain
mandatory.  The empirical sign is the verified primary `B0xS0` sign.

For a witness report:

- `r_TV = max(.5 ||q_b-p_b||_1, .5 ||q_s-p_s||_1)`;
- symmetric odds factor
  `R = max_i max(q_i/p_i, p_i/q_i)`; and
- the full group masses, per-trial mass hash and three pair deltas.

## Three frozen EER evaluators

All use the same default NumPy score ordering except where the tie-safe rule is
explicit.

1. **Count-canonical search evaluator.**  For every threshold, store exact
   integer cumulative counts for each of 3+5 groups.  Form class CDFs as
   `sum_g q_g count_g(t)/n_g`; choose the first position minimizing
   `abs(FRR-FAR)` and average FRR/FAR there.  Integer group counts prevent the
   repeated-`1/n_g` accumulation that caused the failed fast constraint.
2. **Direct per-trial evaluator.**  Materialize each trial's `q_g/n_g`, perform
   NumPy cumulative sums in sorted trial order, normalize by realized class
   totals and apply the historical first-argmin EER rule.
3. **Tie-safe threshold evaluator.**  Stable-sort by score from the
   utterance-ID-sorted roster, aggregate all equal-score rows before evaluating
   a threshold, and use the first threshold minimizing `abs(FRR-FAR)`.

An accepted witness must have a sign different from the empirical sign under
**all three** evaluators.  Equality under any backend is a rejection, not a
reversal.  The three numeric deltas need not agree exactly, but their signs must.

## Candidate directions

Both searches restart from their original fixed seeds; old boundary candidates
are not fed back as initial points.

### Sobol search

- scrambled Sobol dimension 8, seed `20260829`, `2^18` draws;
- transform uniforms to independent exponential coordinates and normalize the
  first 3 and last 5 coordinates to simplexes;
- evaluate every draw with the count-canonical evaluator;
- for every pair and each objective (`r_TV`, `R`), retain the **32** best endpoint
  directions whose endpoint sign differs from empirical; retain fewer if fewer
  exist; and
- do not run the prior coordinate/pairwise-transfer refinement.

### Differential search

- six free logits with the last coordinate of each simplex fixed to zero;
- constrained differential evolution, seed `20260828`, bounds `[-16,16]`,
  population multiplier 12, 240 generations, tolerance `1e-8`;
- one SLSQP polish with `maxiter=1000`, `ftol=1e-12`;
- run separately for all 28 pairs and both objectives; and
- retain the uncontracted feasible endpoint direction from each run.  An
  infeasible or same-sign endpoint is recorded as rejected.

Thus a pair/objective receives at most 32 Sobol plus one differential direction.
Every retained and rejected count is saved; the report cannot display only the
algorithm that looks best.

## Frozen consensus path rule

For each retained endpoint direction `q`, consider
`q(lambda)=(1-lambda)p + lambda q`.

1. With the count-canonical evaluator, scan `lambda=0,.01,...,1` and take the
   first observed sign-changing coarse interval.  Because the endpoint itself
   must flip, absence of a coarse flip can occur only through a non-monotone
   region narrower than `.01`; record and reject it rather than searching
   adaptively.
2. Bisect that coarse interval for 60 iterations with the canonical evaluator.
3. Round upward to the next `1e-4` grid point.
4. Evaluate the three EER backends at that point and at the next at most 100
   registered grid points (`+1e-4` each, maximum additional path length `.01`).
5. Accept the **first** grid point at which all three signs differ from
   empirical.  If none passes, reject the direction.  The number of extra grid
   steps is reported.

This bounded consensus scan is fixed before v2 output.  There is no adaptive
margin, candidate-specific tolerance or machine-epsilon nudge.

## Selection and reporting

For every pair and objective, report separately:

- best accepted Sobol witness;
- accepted differential witness, if any;
- best accepted witness across the two algorithms;
- absolute objective difference when both algorithms succeed; and
- numbers of directions retained, consensus-accepted and rejected by reason.

The only scientific language authorized is:

- **verified constructive upper bound** when at least one witness passes all
  three backends and the independent verifier;
- **dual-search upper bound** when both algorithms independently yield verified
  witnesses; or
- **not found by the registered search** otherwise.

No absence claim, optimum, safety radius or change to the primary frozen class
is permitted.

## Independent verification

`verify_secondary_v2.py` imports neither search implementation nor primary EER
code.  It reconstructs group masses and all three evaluators, verifies input and
code hashes, re-evaluates every accepted candidate, checks path-grid identity,
distances, odds factors, hashes and signs, and recomputes every report summary.

Candidate-level consensus rejection is expected and does not fail the run.
Any candidate labelled accepted that fails reconstruction, any omitted retained
count, hash drift or summary mismatch fails the entire v2 output.

Execution is CPU-only and writes its own pre-output contract before loading a
score.  It does not touch ASV5, the GPU queue, the primary result JSON or the
primary report.
