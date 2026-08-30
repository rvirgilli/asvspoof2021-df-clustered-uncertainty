# Scientific claim and stopping contract

This document fixes the scientific identity of the accompanying paper. It
separates the result supported by the released score files from population
claims that the benchmark cannot identify. Expanding the target requires a
separate prospective analysis plan; it is not a condition for reproducing or
accepting the present result.

## Central claim

On the fixed ASVspoof 2021 DF score set, pairwise EER conclusions are sensitive
to two declared evaluation-design choices: the unit used to perturb the scores
and the source/task composition used to weight them. With threshold refitting
and all-pair multiplicity held fixed, trial-i.i.d. and speaker-by-attack
perturbations produce materially different zero-exclusion outputs.

This is an identified fixed-data procedure-sensitivity result. It is not an
estimate of which method would cover a named population of future speakers,
attacks or systems.

## Findings supported by the release

- The two Bengio--Mariethoz reconstructions separate five of the six organizer
  baseline pairs shared with the released system pool.
- A matched diagnostic gives 5/6 organizer zero-exclusions under trial-i.i.d.
  perturbation and 0/6 under speaker-by-attack product perturbation. Both arms
  refit the same EER rule and use the same all-28-pair multiplicity procedure.
- A disclosed post-failure EXP-111 arm fixes class-by-source/task composition
  and retains 0/6 organizer and 18/28 overall product-perturbation endpoints.
  It answers that confound but is not prospective confirmation.
- A pre-access frozen, single-source SpoofCeleb experiment gives 6/6
  trial-i.i.d. versus 3/6 product/source exclusions. A disclosed post-result
  scorer-provenance rerun leaves every EER, decision and endpoint unchanged.
- A disclosed post-result SpoofCeleb factor decomposition gives 5/6 speaker-only
  and 3/6 attack-only exclusions. Attack-only reproduces the joint-product verdict
  vector, so attack-level perturbation alone is sufficient for all three changed
  decisions under the declared procedure; speaker-only is sufficient for one.
- A single coherent marginal-sum covariance also gives 0/6 for the organizer
  family. It is a sensitivity construction, not a proved variance estimator.
- Twelve internally frozen score-blind composition policies reverse 6/12
  within-block orderings and none of the 16 contrasts between the four selected
  modern systems and four selected baselines.
- Constructive post-failure searches provide verified upper bounds on the
  composition change sufficient to cross each within-block sign boundary.
  Those bounds are existence results, not minima or evidence that every
  witness is practically plausible.
- The low-EER stress grid refutes universal calibration of the candidate
  intervals. The adverse result limits rather than validates population use.
- A witnessed EXP-112 trace gives 18.5% trial-i.i.d. and 97.5--98.0%
  clustered-candidate coverage under its fitted organizer-like Gaussian DGP.
  This authenticates the simulation, not the DGP's adequacy for 21DF.
- A fixed four-system ASVspoof 5 check reproduces the registered family-level
  direction and magnitude criteria. It is not a pair-level or independently
  sampled replication.

## Claims expressly excluded

The paper and artifact do not claim that:

- speaker-by-attack resampling is the correct population inference for 21DF;
- the 5/6 trial-i.i.d. outputs are five proven false positives;
- zero-straddling establishes equality between systems;
- the selected modern and baseline blocks identify a general property of model
  generations;
- every constructive composition witness is operationally plausible;
- corpus-associated influence values refute every possible exchangeability
  law;
- the internal analysis freezes have an independently verifiable public
  timestamp;
- the ASVspoof 5 check is an independent-team replication; or
- the EXP-111 post-failure arm is a preregistered confirmation;
- the EXP-114 provenance rerun is a second prospective trial;
- the EXP-115 factor decomposition is prospective confirmation, a causal variance
  decomposition, or a population law;
- the fitted Gaussian DGP has been validated as a population model of 21DF; or
- released score files regenerate detector inference or training from audio.

## Completion gates for this release

The base paper is complete when all of the following hold:

1. The exact PDF contains at most four pages of technical content and uses any
   fifth page only for permitted back matter.
2. Every reported number is bound to a named machine-readable artifact and the
   clean-clone checker passes.
3. Every documented regeneration command either runs in the public layout or
   is explicitly labelled as artifact authentication rather than regeneration.
4. No paper or README sentence exceeds the central claim or contradicts the
   exclusions above.
5. A closure review finds no reproducible fatal error and no major error that
   contradicts the central claim.

Once these gates pass, requests for a new corpus, a named population sampling
frame, additional systems or an independent sample are prospective extensions,
not blockers for this release.
