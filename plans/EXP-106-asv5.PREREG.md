# EXP-106 — M1 replication on ASVspoof 5

Frozen 2026-08-16 before XLS-R+SLS or XLSR-Mamba was scored on ASVspoof 5 and
before any four-system pairwise uncertainty analysis was computed.

- **Line/idea:** M1 · **Priority:** supporting, external validity
- **Hypothesis:** trial-i.i.d. inference overstates the resolution of at least
  one of the six four-detector edges on ASVspoof 5, and the median clustered/iid
  pointwise width ratio is at least 2.
- **Why now:** the M1 result currently rests on ASVspoof 2021 DF with 93 speakers
  and 110 spoof attacks. ASVspoof 5 changes that balance to 737 speakers and 16
  attacks and therefore tests whether the dependence result survives a major
  benchmark redesign rather than another score release on the same trial list.

## Information already seen before this freeze

EXP-103 already scored SSL-AASIST and AASIST and reported A2's threshold-transfer
analysis. Its viability gate found SSL-AASIST usable and AASIST
overlap-dominated. Those individual detector facts are known. No XLS-R+SLS or
XLSR-Mamba A5 scores exist, and no M1 ΔEER interval, width ratio, rank interval
or resolved/unresolved verdict has been computed on A5.

## Fixed detector pool and provenance

1. SSL-AASIST and AASIST: the resumable EXP-103 score dumps from the project's
   smoke-tested reference adapters.
2. XLS-R+SLS: checkpoint
   `~/data/checkpoints/deepfake-references/sls/asvdf_sls_best.pth` and the shared
   XLS-R front end.
3. XLSR-Mamba: checkpoint
   `~/data/checkpoints/deepfake-references/xlsr-mamba-la/model.safetensors` and
   the same front end, using its upstream ASVspoof length of 66,800 samples.

All four are 19LA-trained reference implementations. AASIST remains in the
complete table even if its EER is poor; no performance-dependent exclusion is
allowed. Score orientation and exact trial intersection are verified before
analysis.

## Fixed scoring and analysis

- Score all 680,774 rows of the existing ASV5 eval manifest. Scoring is
  resumable and every GPU invocation goes through `gpu-submit`.
- Primary dependence units: 737 speakers and the 16 spoof attack IDs. Codec
  conditions are reported and treated as fixed in the primary analysis because
  twelve levels do not support a stable third-axis bootstrap.
- Sensitivities: add codec as a third multiplier; repeat on the 80.5% of bona
  fide sources that occur under only one codec condition; and cluster by source
  recording in place of speaker for the 19.5% crossed subset. These are named
  sensitivity analyses, not alternative primaries.
- `B=5000`, seed `20260826`, with shared replicate weights across all four
  systems and six pairs.
- Compare paired trial-i.i.d. bootstrap, speaker×attack product bootstrap and
  the EXP-105 estimator if and only if its correctness gates pass.
- Form pointwise intervals and one sup-t band over all six pairs. Rank intervals
  derive from the six-pair band. Report all pairs and all variants.
- Report width ratios and variance components beside the 21DF results, without
  assuming that either the speaker or attack share must move monotonically.

## Reading rule

- **Confirmed:** both hypothesis clauses hold.
- **Partially confirmed:** exactly one holds.
- **Refuted:** neither holds.

Failure limits M1's external validity and is reported; it does not erase the
ASVspoof 2021 measurement.

## Detectability and dependence unit

The primary evidence units are 737 speakers and 16 spoof attacks. The six-pair
simultaneous intervals themselves determine detectable ΔEER, and each pair's
pointwise and familywise MDE is reported. The operational minimum is one pair
changing verdict; no 680,774-trial analytic bar is used as if trials were
independent.

## Budget

Two full detector scoring passes plus CPU inference. Cost does not gate the run.

