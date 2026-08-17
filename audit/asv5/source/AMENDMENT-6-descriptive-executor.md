# EXP-106 amendment 6 — descriptive executor contract

Frozen **2026-08-16 16:38 BRT**, with the resumed XLS-R+SLS scoring job at
544,624/680,774 rows and before XLSR-Mamba full scoring.  No complete new score
vector, pooled EER, pairwise delta, perturbation replicate, band, width ratio
or Amendment-5 reading had been computed or viewed.

This contract fills implementation choices left implicit by
`AMENDMENT-5-fixed-roster-descriptive.md`.  It authorizes implementation and
synthetic testing only while either new score TSV is incomplete.  It does not
revive the stopped population-inference path and it does not authorize the
historical `analyze_asv5.py` or the v2 confidence driver.

## Immutable analysis constants

- systems, in this order: `SSL-AASIST`, `AASIST`, `XLS-R+SLS`, `XLSR-Mamba`;
- pairs: the six lexicographic combinations induced by that system order;
- `B=5000`, base seed `20260826`;
- score orientation: higher means bona fide;
- EER: the sealed EXP-101 position-wise weighted functional, with NumPy's
  default quicksort ordering, the first index minimizing `abs(FRR-FAR)`, and
  `(FRR+FAR)/2` at that index;
- pair delta: `100*(EER_a-EER_b)` in percentage points;
- percentile convention: NumPy `method="linear"` for 2.5%, 95% and 97.5%;
- max-t centering: each bootstrap pair-delta column is centered at its own
  bootstrap mean, as in the sealed EXP-101 matched diagnostic;
- max-t scale: bootstrap standard deviation with `ddof=1`; a nonpositive or
  nonfinite scale is a hard failure;
- simultaneous numeric procedure band:
  `hat_delta +/- q95*sd`, where `q95` is the linear 95th percentile of the
  per-replicate maximum absolute centered studentized delta over all six pairs.

The output field for a band not containing zero is named
`numeric_band_excludes_zero`.  The executor must not emit `confidence`,
`significant`, `resolved`, `confirmed`, `refuted` or a population-coverage
claim.

## Exact perturbation arms

Each arm uses an independent namespace.  For zero-based replicate `r`, create
a new generator from

```text
SeedSequence([20260826, uint32_le(SHA256(namespace)[0:4]), r]).
```

The namespaces are:

```text
exp106-amendment5/class-stratified-trial-iid
exp106-amendment5/role-speaker-attack
exp106-amendment5/role-speaker-only
```

Draw order is fixed:

1. trial-iid: draw `n_bona` indices uniformly with replacement over bona-fide
   rows, then `n_spoof` indices over spoof rows;
2. speaker×attack: draw 367 target-speaker labels, then 370 non-target-speaker
   labels, then 16 attack labels, each uniformly with replacement from its own
   observed set;
3. speaker-only: draw the same two role-stratified speaker samples using its
   own namespace and draw no attack labels.

All systems share a perturbation draw.  The EER threshold is refit separately
for every system and replicate.  The class totals in trial-iid and the three
multinomial totals in the primary arm are asserted exactly.

## Checkpoint and resume

Each arm writes one `float64` NumPy array of shape `(5000,4)` and a sidecar
binding the run-contract hash, arm, namespace, constants, system order,
analyzer hash and algorithm-core hash.  A row is either wholly finite or
wholly `NaN`; mixed rows stop execution.  Pending rows are derived only from
that rule and use their original zero-based replicate indices, so batching,
interruption and resume cannot change RNG draws.

An existing checkpoint is reused only when its sidecar and shape match exactly.
No completed arm is recomputed or silently overwritten.  The analyzer rehashes
all inputs before every resumed outcome block and again before final output.

## Pre-outcome transaction

The executor performs two phases.

1. **Identity phase:** hash the protocol, manifest, incidence record, four
   score inputs, every legacy NPZ chunk, every available scoring sidecar, both
   amendments, analyzer, algorithm core and tests; validate row counts,
   uniqueness, exact common utterance set, protocol joins and finite scores;
   then atomically create a run contract.  Legacy chunk hashes are explicitly
   an input ledger, not historical run provenance.
2. **Outcome phase:** rehash the committed snapshot, enforce orientation, then
   and only then compute pooled EERs and perturbation replicates.  No EER or
   delta is printed or persisted before the contract exists.

The frozen protocol/manifest/incidence hashes and all count/incidence gates are
those in Amendment 5.  A pre-existing run contract must match byte-for-byte or
execution stops.  Result files are created atomically and never overwritten.

## Frozen outputs and reading

For every arm, report its namespace, `B`, max-t critical value, six bootstrap
SDs, six pointwise percentiles, six simultaneous numeric bands and six
zero-exclusion flags.  Also report all pooled EERs, six point deltas, identical
point-statistic reproduction across arms, six primary/iid simultaneous-width
ratios and their median.

The two predeclared Amendment-5 summaries remain:

- `A`: at least one trial-iid numeric zero-exclusion is absent under the
  speaker×attack arm;
- `B`: median speaker×attack/iid simultaneous-width ratio is at least 2.

Report the two booleans and their sum, without mapping them to a verdict word.
The speaker-only arm is a named sensitivity and cannot replace either primary
arm.

## Static GO required before real execution

Before either new score TSV is complete, synthetic tests must establish:

1. optimized and literal weighted EER agreement for every arm, including ties;
2. exact equality with the sealed EXP-101 EER and summary conventions;
3. shared draws across systems and exact multinomial totals;
4. batch/resume invariance and rejection of mixed checkpoint rows;
5. common-roster, duplicate, missing, nonfinite, label, role, attack, codec,
   orientation and input-mutation failures;
6. correct pair order, centering, percentiles, width ratios and `A/B` readings;
7. absence of inferential verdict vocabulary from the result schema.

Passing synthetic tests is implementation GO only.  Real execution remains
blocked until both new TSVs and their matching run contracts are complete and
the static audit of the sealed analyzer snapshot passes.

