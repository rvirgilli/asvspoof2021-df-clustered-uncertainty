# EXP-105 — M1 multiway intersection and interaction correctness audit

## Decision

**Refuted under the preregistered reading rule.**  No non-proxy estimator has
coverage in `[.92,.98]` throughout the 48-cell grid, and every candidate falls
below `.90` together in 11 of the 24 low-EER cells.  The minimum corrected
coverage is `.845` raw exact-cell, `.845` after the pairwise marginal-component
adjustment and `.855` product-percentile.  Truth-calibration sensitivity lowers
those minima by at most `.001`.

The six-pair organizer-baseline conclusion is invariant: product, raw
exact-cell and marginal-adjusted exact-cell inference each resolve zero of six
pairs.  All three methods cover inside `[.92,.98]` in every one of the 24
organizer-like stress cells.  The experiment therefore narrows the supported
scope; it does not reverse the paper's central organizer result.

## Frozen design and execution

- Real ASVspoof 2021 DF incidence: 533,928 trials, 93 speakers, 110 spoof
  attacks and 1,062 occupied spoof speaker × attack cells.
- Fully crossed grid: organizer-like/low-EER × interaction share
  `{0,.25,.50,.75}` × Gaussian/Student-t(5) effects × true delta
  `{0,.5,2}` points.
- `R=1000` outer replicates in each of 48 cells; `B=500` product-bootstrap
  draws per replicate; seed `20260824`.
- Additive gate: `R=2000` and exact-cell mean variance / direct Monte Carlo
  variance `1.0255898569570525`, inside the frozen `[.90,1.10]` gate.
- Coverage code SHA-256:
  `570727728b78300d30371a4c0e163f7d4d72028ccc006cc02c85a6a6c53b40ef`.
- All 48 contracts carry that hash; the strict closure verifies each contract,
  1,000-row JSONL shard, result file and regenerated aggregate.

No detector was retrained or rescored.  This is a CPU simulation and audit on
the frozen real trial incidence.

## Corrected coverage results

High-precision population truth uses eight independent Student-t(5)
calibrations, each with 10 million antithetic samples.  Gaussian truths remain
analytic.  The organizer ranges are unchanged under every truth-calibration
repeat.

| regime | estimator | minimum | maximum | cells in `[.92,.98]` |
|---|---|---:|---:|---:|
| organizer | raw exact-cell | .928 | .957 | 24/24 |
| organizer | marginal-adjusted | .928 | .957 | 24/24 |
| organizer | product-percentile | .946 | .968 | 24/24 |
| low-EER | raw exact-cell | .845 | .923 | 1/24 |
| low-EER | marginal-adjusted | .845 | .923 | 1/24 |
| low-EER | product-percentile | .855 | .925 | 3/24 |

Sixteen of 24 low-EER cells have at least one candidate below `.90`; eleven
have all three below `.90`.  The worst cell is low-EER, interaction share `.5`,
Student-t(5), delta 2 points: `.845/.845/.855`.  Crucially, failure does not
require tails or interaction.  At low-EER, Gaussian, zero interaction and delta
2, coverage is `.879/.880/.883`, which alone satisfies the frozen Refuted rule.

## Failure mechanism

The average variance scale is not the main defect.  In the first three exact
Gaussian low-EER cells, mean raw variance / direct Monte Carlo variance is
approximately `1.065/1.075/.945`; an oracle constant-SD interval covers
`.944/.954/.953`.  Replicate-specific SE instead collapses in extreme samples.
For grids 24--26 the raw-studentized 2.5%, median and 97.5% quantiles are:

- `[-2.879, -.111, 1.682]`;
- `[-2.954, -.079, 1.512]`;
- `[-3.384, -.182, 1.572]`.

In grid 24, median raw variance is `.084` among failures against `.187` among
covered replicates.  Product-percentile intervals have the same directional
miss.  This is asymmetric non-pivotality, not a simple global underestimate of
variance.

## Post-result diagnostics, not alternative reading rules

Across all low-EER cells, minimum coverage is:

| diagnostic interval | minimum |
|---|---:|
| oracle constant-SD normal | .944 |
| product basic | .821 |
| product symmetric widest-tail | .866 |
| pre-existing `q=2.981` × raw exact SE | .926 |
| pre-existing `q=2.981` × marginal-adjusted SE | .926 |

The basic and symmetric transforms fail.  `q=2.981` is encouraging but cannot
rescue EXP-105: it was estimated from the real 28-pair product covariance, while
each simulated cell has one contrast, and it was not the preregistered pointwise
critical value.  Selecting it after seeing coverage would be outcome-dependent.

## Correctness gates and deviations

1. The exact-cell additive gate passed (`1.02559`).
2. The independent real-score cross-path gate passed 256/256 weighted
   comparisons, including score orientation, incidence partitions, point EERs,
   deltas and product weights.
3. The smooth linearized CRVE failed its preregistered exact-refit correlation
   and slope gates on every pair and remains excluded.
4. The original gate-1 prose incorrectly said centered influence contributions
   sum to delta; they sum to zero, while point estimate plus contributions
   reconstructs the statistic.  The implementation used the correct identity.
5. Student-t(5) locations were frozen from finite Monte Carlo calibration but
   the original flags used nominal delta.  No dataset or interval was rerun;
   `recalibrate_truth.py` recomputed population truth and flags from saved rows.
6. The cross-path gate was completed after real-data verdicts, so it is an audit
   check rather than a retroactively blind gate.
7. Interaction correlation was fixed to the calibrated average, not crossed in
   the grid.  Results are conditional on that value.

## Consequence for M1

- Retain formal inference for the organizer-baseline reversal: reconstructed
  cited tests 5/6, clustered product and exact-cell 0/6.
- Withdraw the two within-SSL ``resolved'' labels, modern rank confidence claims
  and the formal `10 of 12` within-generation count.
- Treat the 16 large cross-generation gaps as descriptive arithmetic, not proof
  that the low-EER interval family is calibrated.
- Treat the eleven-system Arena layer as provenance and descriptive sensitivity,
  not formal confidence inference.
- Do not call the finite-`A` speaker component a pure-speaker or infinite-attack
  floor; observed-cell inclusion--exclusion does not identify absent-cell
  interactions.

## Released closure files

| file | SHA-256 |
|---|---|
| `results_coverage_interaction.json` | `ec261bee657b19551bf64d87415fa72043eddb5c17814f879041541d5f6bf751` |
| `results_coverage_interaction_recalibrated.json` | `259f382e100488b36ce2e1d672718e6cada576b49805e3e9363b840cd9495c74` |
| `results_crosspath_gate.json` | `4b82b8ef74675745813cd579b288777be22857b330a7f7924854877fbe970a60` |
| `results_coverage_diagnostics.json` | `ddf290ba12f37b646db646a9129540b65a57881121fb8b3fdd23e7405d07609c` |
| `results_exp105_verified.json` | `83653a5e2da338f3884926d6cc26f0db2711cb83d3ae0749f94ca0949f63c4a6` |

`results_exp105_verified.json` is the authoritative machine-readable closure.
It records `status_under_preregistered_reading_rule: refuted`, an empty
`confirmed_estimators` list, input hashes and hashes/counts for all 48 shards.
