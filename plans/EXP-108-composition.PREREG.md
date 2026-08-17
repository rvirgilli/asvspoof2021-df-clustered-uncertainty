# EXP-108 — Fixed-benchmark composition robustness of the 21DF leaderboard

Frozen **2026-08-16 15:36 BRT**, before computing any EER under a new
composition policy, any policy-specific ordering, or any composition-shift
witness.  Existing ordinary pooled EERs, clustered-diagnostic results,
leave-one-source-out results and the metadata-only incidence audit were already
known.  Those objects motivate the axes but cannot select policies, pairs or
reading rules below.

This experiment is deterministic and CPU-only.  It does not retrain or rescore
a detector, resample a population, open ASV5 outcomes or use the GPU.

## Scientific question and target

For the eight fixed score vectors on the 533,928 fixed ASVspoof 2021 DF eval
trials, how sensitive are EER orderings to prospectively declared policies for
weighting the observed bona-fide sources, spoof source/task strata, speakers,
attacks and attack families?

The target is **evaluation-design robustness of the fixed benchmark**.  Every
reported EER is a deterministic functional of the observed score vectors and a
declared probability mass over the observed trials.  A policy range or shift
radius is not a confidence interval and supports no claim about unobserved
speakers, attacks, corpora or deployments.

The primary qualitative hypothesis is asymmetric:

- within-generation orderings are sensitive to modest score-blind composition
  changes; but
- the modern-versus-organizer-baseline separation is stable over the same
  registered policies.

The analysis reports the full symmetric result if either, both or neither
clause holds.

## Evidence and structural inputs known at freeze

The metadata-only audit established, without loading scores:

- 14,869 bona-fide and 519,059 spoof eval trials;
- bona-fide source masses `asvspoof/vcc2018/vcc2020 =
  .53393/.25422/.21185`;
- spoof source/task masses `asvspoof/vcc2018-HUB/vcc2018-SPO/
  vcc2020-Task1/vcc2020-Task2 = .14229/.23425/.11716/.21500/.29130`;
- corresponding spoof-speaker counts `48/4/4/4/6`;
- 1,062 of 1,068 possible within-stratum speaker x attack cells observed; and
- a frozen attack-to-family mapping in the official metadata.

The total-variation distance from empirical mass to equal top-level mass is
`.20060` for bona-fide sources and `.14055` for spoof strata.  This is a
metadata-only calibration: the registered `TV <= .10` label below means moving
at most ten percentage points of conditional class mass and is smaller than
full top-level balancing on either class.

Frozen structural hashes:

- official trial metadata:
  `70e0e7d5964562cb0166e79143f73beaeaf77ee18e799fa4156355a57006d800`;
- metadata-only incidence JSON:
  `c790f14b5c419a6224d7b2571319be98a524215f7f75d034d6bb0f5228b4d192`;
- incidence builder:
  `d4a84acc31ac2d40a6bc4a9729bf51184b1cfc727ce4f7889a1d6df5ca05ef96`;
- historical common EER implementation snapshot:
  `66756f430c8a0e28e76b3b0c296d6f593c030b7620894f8bf57630a5d52be65a`.

## Fixed systems, orientation and pair family

The system order is fixed as:

1. XLSR-Mamba
2. XLS-R+SLS
3. XLSR-Conformer
4. SSL-AASIST
5. RawNet2
6. LFCC-LCNN
7. LFCC-GMM
8. CQCC-GMM

All `8 choose 2 = 28` pairs are reported in this order with
`Delta(A,B) = EER(A) - EER(B)`; lower EER is better.  Pairs 1--6 within the
first four systems form the modern block, pairs within the last four form the
organizer-baseline block, and the remaining 16 form the cross-generation
block.  No pair can be removed because it is stable, inconvenient or close to
zero.

`sign` is exactly `-1`, `0` or `+1`.  A move from a nonzero empirical sign to
zero counts as loss of the strict ordering and therefore as a sign change, but
is separately labelled `tie` rather than `reversal`; the report gives both
counts.  No numerical near-tie tolerance is introduced.

## Common weighted-EER functional

Scores are oriented higher-is-bona-fide.  For each system, sort score positions
ascending once with NumPy's default `argsort`, accumulate weighted bona-fide
and spoof mass, select the first position minimizing `abs(FRR-FAR)`, and report
the mean of FRR and FAR there.  There is no interpolation.  This is the same
functional as the frozen historical implementation.  Every class-conditional
policy below sums to one, but common class scaling would cancel in the EER.

Tie safety is checked by a stable utterance-ID secondary ordering and by
aggregation at unique score thresholds.  If either changes any reported EER by
more than `.001` point or any pair sign, the affected result is flagged and no
qualitative reading is emitted until the convention is resolved without
outcome selection.

## Prospectively fixed policy multiverse

Let `n(g)` denote trial count in group `g`.  All groups and attack families are
read only from official metadata.  Every observed trial receives positive
mass; there is no trimming or intersection change.

### Bona-fide policies

- **B0 empirical:** each bona-fide trial has mass `1/N_bona`.
- **B1 source-balanced:** each of three sources has mass `1/3`, uniform over
  trials within source: `1 / (3 n(source))`.
- **B2 source-speaker-balanced:** each source has mass `1/3`, each bona-fide
  speaker observed in that source has equal conditional mass, and trials are
  uniform within speaker:
  `1 / (3 n_speakers(source) n_trials(source,speaker))`.

### Spoof policies

- **S0 empirical:** each spoof trial has mass `1/N_spoof`.
- **S1 stratum-balanced:** each of the five source/task strata has mass `1/5`,
  uniform over trials within stratum.
- **S2 observed-cell-balanced:** each stratum has mass `1/5`, every observed
  speaker x attack cell within it has equal mass, and trials are uniform within
  cell:
  `1 / (5 n_cells(stratum) n_trials(stratum,speaker,attack))`.
- **S3 family-attack-cell-balanced:** each stratum has mass `1/5`; each attack
  family present in that stratum has equal mass; each attack within family has
  equal mass; each observed speaker cell for that attack has equal mass; and
  trials are uniform within cell.  Thus the mass is
  `1 / (5 n_families(stratum) n_attacks(stratum,family)
        n_speaker_cells(stratum,attack) n_trials(stratum,speaker,attack))`.

The primary multiverse is the complete Cartesian product of the three bona-fide
and four spoof policies: **12 policies**, including empirical `B0xS0`.  This
factorial is required even if one side appears to explain the entire effect.

## Primary deterministic outputs

For every one of the 12 policies, save:

- the exact per-trial mass vector hash and mass checks by class and hierarchy;
- eight EERs, 28 oriented deltas and the complete rank order;
- Kendall inversions relative to empirical `B0xS0`;
- the best system and every system's regret relative to that policy's best;
- the strict pairwise dominance graph.

For every pair, save:

- minimum and maximum delta over all 12 policies and the attaining policies;
- every sign observed, whether a sign changes from empirical, and the number of
  policies on each sign;
- maximum delta range caused by changing only the bona policy at fixed spoof
  policy, and by changing only the spoof policy at fixed bona policy; and
- whether one system strictly dominates the other under all 12 policies.

Also report the minimax-regret system over the finite registered 12-policy set.
This is not minimax over an unspecified deployment distribution or over the
continuous convex hull.

## Registered-policy path-grid radii

For each of the 11 non-empirical policies `Pk`, define separate class-
conditional trial masses

`P(lambda) = (1-lambda) P_empirical + lambda Pk`, `lambda in [0,1]`.

The registered path is the finite grid `lambda = 0, 1e-4, ..., 1`.  For every
pair whose sign differs on a path, report the first registered grid point with
the differing sign and its immediately preceding grid point.  This is an exact
result on the registered grid, not a claim about the continuous minimum.  The
maximum unsearched path increment is `1e-4`, so the corresponding TV
discretization is also reported for every witness.  Because the non-interpolated
empirical EER may jump when its selected threshold changes, equality at zero is
not assumed.  The left and right EERs, deltas, selected threshold positions and
full witness weight hashes are saved.

At the right witness, report:

- `TV_bona = .5 sum_i |P_bona(lambda)_i-P_bona(0)_i|`;
- `TV_spoof` analogously;
- primary `r_TV = max(TV_bona, TV_spoof)`; and
- the maximum symmetric trial-mass odds factor
  `R = max_i max(P_i(lambda)/P_i(0), P_i(0)/P_i(lambda))`, separately by class
  and jointly.

The path search evaluates all 11 paths for all 28 pairs at every registered
grid point.  A finer local grid or continuous optimizer may be reported only as
a secondary upper bound and cannot replace the registered-grid result.  Only
grid witnesses reproduced independently enter the reading rule.

## Secondary arbitrary source/task witness search

A secondary search varies only the three bona source masses and five spoof
stratum masses, retaining empirical conditional trial mass within every
top-level group.  It searches separately for a sign-flip witness minimizing
`max(TV_bona, TV_spoof)` and minimizing the joint symmetric odds factor.

Two predeclared searches are run from fixed seeds:

1. constrained differential evolution, seed `20260828`, followed by SLSQP;
2. a Sobol `2^18` simplex search, seed `20260829`, followed by deterministic
   coordinate/pairwise-mass-transfer descent.

Every candidate is independently recomputed by the slow reference EER
implementation.  Agreement within `1e-5` on the objective is recorded, but
even agreement does **not** prove global minimality.  These quantities are
labelled `witness upper bounds`; they may establish that a flip is possible
within a stated shift, never that all smaller shifts are safe.  No primary
reading depends on this secondary search.

## Frozen reading rule

`r_TV <= .10` is labelled a **small registered shift**; `.10 < r_TV <= .25`
is labelled **material but not small**.  These are operational deterministic
labels, not significance thresholds.  The result receives exactly one primary
classification, in this order:

1. **GLOBAL COMPOSITION FRAGILITY:** at least one of the 16 cross-generation
   pairs changes sign under a registered policy or verified registered path grid.
   Within-generation results are still reported, but the coarse-separation
   hypothesis is false.
2. **COARSE GAP STABLE / WITHIN RANKING FRAGILE — STRONG:** all 16 cross-
   generation pairs retain the modern-better sign under every registered
   policy and path; at least three of 12 within-generation pairs change sign;
   and at least two within-generation pairs have a verified registered-path-grid
   witness with `r_TV <= .10`.
3. **LOCAL COMPOSITION FRAGILITY:** no cross-generation pair changes sign, and
   at least one but fewer than three within-generation pairs changes sign, or
   the strong count holds without two small-shift witnesses.
4. **REGISTERED-POLICY STABILITY:** no pair changes sign under any of the 12
   policies or 11 paths.  This refutes the proposed fragility expansion over
   the registered policy family.

If no clause applies because a saved witness fails independent reproduction,
classify `UNVERIFIED` and report the implementation failure.  Counts cannot be
replaced by Arena rows, leave-source-out verdicts, or a favorable secondary
optimizer result.

## Implementation and validation gates

No policy outcome may be printed or written until a pre-output run contract
records hashes of this preregistration, metadata, all eight score files, every
executable source file and the Python/NumPy/SciPy environment.

The analysis then passes all of the following:

1. after the official `phase=eval` filter, exact trial-ID equality across
   metadata and all eight score files.  A release may contain additional rows
   only when every additional ID joins uniquely to an official non-eval
   metadata row; ignored non-eval counts and phases are recorded.  Missing eval
   IDs, duplicate IDs or extras absent from official metadata remain fatal;
2. unique IDs, finite scores, fixed orientation and 533,928 rows per system;
3. all 12 mass vectors positive, class-normalized and satisfying every declared
   hierarchical marginal to absolute error `<=1e-12`;
4. empirical `B0xS0` reproduces the existing eight pooled EERs within
   `.001` point, used only as an implementation check;
5. the fast crossing-search EER equals an independent full cumulative-array
   implementation to `1e-12` on every policy, every saved witness and 200 fixed
   synthetic/random controls;
6. identical-system and fixed-gap negative controls return no sign flip, while
   a constructed composition-dependent positive control must flip; an inert
   control aborts;
7. every path witness reproduces the saved right-hand sign and the preceding
   registered grid point preserves the preceding sign;
8. a second path-grid pass using the slow reference EER verifies the complete
   sign sequence for every pair within two grid steps of each saved first flip;
9. the verifier imports no analysis implementation and reconstructs all 12
   policy masses and every headline count from metadata, score and result
   artifacts; and
10. any optimizer exception, tie-convention failure, hash drift or verifier
    mismatch emits no qualitative classification.

All raw 12-policy outcomes, including falsifying and counter-directional
results, are retained.  Nothing may be moved to an appendix or omitted because
it weakens the preferred story.

## Planned files and execution order

1. `build_contract.py` reads metadata only and materializes/hashes the 12 policy
   masses and structural assertions.
2. `test_exp108.py` must pass before a score file is opened by the analyzer.
3. `analyze.py` writes `run_contract.json` before any aggregate and then writes
   `results.json` without a prose verdict.
4. `verify_results.py`, implemented independently, writes
   `verification.json` and only then `render_report.py` applies this frozen
   reading rule to produce `REPORT.md`.

No amendment may alter a policy, pair, distance, count threshold or reading
branch after a new weighted EER has been computed.  A necessary implementation
clarification must preserve the mathematical object, be dated and hashed, and
must be recorded before rerunning from scratch.
