# Post-audit matched-i.i.d. diagnostic

Frozen before executing this diagnostic on 2026-08-16.  This is not described
as a preregistration: the 21DF scores and earlier i.i.d./clustered summaries
were already known.  It was added in response to an independent review that
identified threshold treatment as a possible confound in the paper's
procedure-sensitivity comparison.

## Question

Does the organizer-baseline 5/6 versus 0/6 contrast remain when the trial-i.i.d.
and speaker-by-attack perturbations use exactly the same EER functional,
evaluation-set threshold re-estimation, 28-pair family, bootstrap size and
simultaneous-band construction?

## Frozen method

- Input: the same eight released 21DF score vectors and exact 533,928-trial
  intersection used by EXP-101.
- Statistic in every observed and perturbed dataset: the repository's
  non-interpolated position-wise `weighted_eer`; its threshold is recomputed
  from the perturbed weights.  The separate tie-boundary audit remains the
  evidence that this implementation choice changes reported pair deltas by
  less than 0.001 EER point on the released files.
- Trial-i.i.d. perturbation: multinomial resampling within bona-fide and spoof
  classes, retaining the observed class sample sizes.
- Clustered perturbation: independent multinomial resampling of the 93
  speakers and 110 observed spoof attacks, with product weights on spoof trials
  and speaker weights on bona-fide trials, exactly as in `exp101_selection.py`.
- `B=5000`; master seed `2026081604`, with child RNG streams created by
  `SeedSequence.spawn` for the two procedures.
- Family: all 28 system pairs.  For each procedure, use the 95th percentile of
  the replicate maximum absolute centered studentized deviation as its own
  sup-t critical value, then apply `hat_delta +/- q * sd` to all pairs.
- Primary reading: number of zero-excluding simultaneous outputs among the six
  organizer-baseline pairs for trial-i.i.d. versus clustered perturbation.
- Secondary readings: all-28 resolved count, pointwise percentiles, simultaneous
  intervals, width ratios and agreement with the previously saved clustered
  result.

## Interpretation guard

This diagnostic can isolate the computational effect of the perturbation unit;
it cannot identify a population sampling law.  All outputs remain sensitivity
measurements on a fixed released score/incidence set.  Any qualitative result,
including an unchanged 5/6 versus 0/6 contrast, must be labeled post-audit and
must not be presented as prospective confirmation.
