# EXP-106 amendment 5 — fixed-roster descriptive replication

Frozen **2026-08-16 15:10 BRT**, after the acquisition-law NO-GO and while
post-reboot XLS-R+SLS scoring was incomplete.  At freeze time XLSR-Mamba full
scoring had not begun.  No new-detector EER, four-system delta, procedure band,
width ratio, zero-exclusion count or four-system reading had been computed or
viewed.  Raw SLS values previously viewed without labels remain only the
documented liveness check.

This amendment does not revive the original population hypotheses or the v2
speaker-conditional confidence analysis.  It freezes a deterministic reporting
contract for the fixed ASVspoof 5 roster so that completed scoring can provide
external descriptive evidence without being represented as inference.

Historical inputs and their hashes at this freeze are:

- `PREREG.md`: `c4a6057f191e3b85be8fa34708ec08fea377725655ed06165b98a4e2ad2f5eaa`;
- `AMENDMENT-1-incidence.md`: `db4264254be7cac6047aec0961a3b103d1285160bd8a2b44526e1c98d0cd4991`;
- `AMENDMENT-3-acquisition-no-go.md`: `788c9379904a32f7192b9f93ecb260be721eeb58991624e6d17900b086e099d2`;
- `incidence_asv5.json`: `e5afcffa8f69e0ff5fe78fe34341174383cff2c169f55b558f3344b30d2fc771`;
- 21DF matched implementation snapshot: `exp101_matched_iid.py`
  `7745e9c498e9e5b3c995b233ab026379245815d6657a3fa30fcfe9e46d6b96d3`.

## Scientific object

The object is the change in outputs of two fully specified perturbation
algorithms applied to the same four fixed score vectors and protocol.  It is
not uncertainty over a named speaker, attack, acquisition or deployment
population.  Procedure bands must not be called confidence intervals, and a
zero-exclusion must not be called significance, resolution or evidence of a
population difference.

The detector family remains frozen as SSL-AASIST, AASIST, XLS-R+SLS and
XLSR-Mamba.  AASIST cannot be excluded on performance grounds.  The analysis
uses all 680,774 protocol utterances once and only once in every system.

## Pre-outcome gates

The descriptive analyzer must stop before pooled EER if any gate fails:

1. protocol, manifest and incidence hashes equal the frozen values;
2. every system has exactly the same 680,774 unique utterance IDs;
3. labels, speaker role, speaker ID, attack and codec join identically to the
   protocol; there are 138,688 bona-fide and 542,086 spoof trials, 367 target
   speakers, 370 bona-only non-target speakers, 16 attacks, 12 codecs and the
   complete 5,872-cell target-speaker×attack incidence;
4. every score is finite and all score and available sidecar hashes are recorded
   in a pre-outcome run contract.  The legacy SSL-AASIST/AASIST NPZ chunks have
   no original run sidecars; this absence is recorded, and the analyzer writes
   a pre-outcome ledger of every chunk name, size and hash.  That ledger proves
   input identity but must not be represented as historical run provenance;
5. median bona-fide score exceeds median spoof score for all four systems;
6. the analyzer, this amendment and every imported implementation dependency
   are hashed in that contract before any aggregate is printed or written;
7. no historical `analyze_asv5.py` result or v2 confidence driver is used.

## Common EER and family construction

Use `B=5000`, base seed `20260826`, the same non-interpolated `weighted_eer`
functional as the sealed 21DF matched diagnostic, weights shared across all
four systems, and an EER-threshold refit in every replicate.  Both arms use the
same six pairs and centered all-pair max-t construction.  Each arm receives its
own critical value because changing the joint perturbation covariance is the
object of the comparison.  For pair `p`, report
`hat_delta_p +/- q_arm * sd_arm,p` and label only whether that numeric band
excludes zero.

The point statistic is the ordinary pooled fixed-roster EER.  The perturbation
arms are:

1. **class-stratified trial-iid:** independently draw a multinomial sample of
   size 138,688 over bona-fide trials and size 542,086 over spoof trials;
2. **role-stratified speaker×attack:** draw 367 multinomial target-speaker
   counts, 370 multinomial non-target-speaker counts and 16 multinomial attack
   counts.  A target count is shared across that target speaker's bona-fide and
   spoof rows and across systems; a non-target count applies only to its
   bona-fide rows; spoof weights multiply target-speaker and attack counts.

The role-stratified law fixes the observed 367/370 participation counts.  It is
a declared perturbation, not a claim that those two samples are independent or
randomly acquired.  The public acquisition audit specifically withholds that
claim.

A named secondary sensitivity removes attack weights from arm 2 while retaining
the two speaker-role draws.  It reports the same outputs but cannot replace the
primary arm.  Codec/source-recording perturbations are excluded from this
amendment because the missing acquisition linkage prevents a clean third unit.

## Frozen descriptive outputs

The result JSON must contain:

- all input, plan, code and sidecar hashes;
- pooled EER and orientation diagnostics for every system;
- all six fixed-roster deltas;
- for each arm: seed namespace, `B`, critical value, pair SDs, pointwise
  percentiles, simultaneous procedure bands and all six zero-exclusion flags;
- the set of trial-iid zero-exclusions absent under role-stratified
  speaker×attack perturbation, and the reverse set;
- all six simultaneous-band width ratios and their median;
- the speaker-only secondary sensitivity with identical fields;
- exact reproduction of the common point statistics across arms.

Two original numeric thresholds are retained only as predeclared descriptive
summaries:

- `A`: at least one trial-iid zero-exclusion is absent under the primary
  speaker×attack perturbation;
- `B`: the median primary/trial-iid simultaneous-band width ratio is at least 2.

The output reports `A`, `B` and how many of the two are true.  It must not emit
Confirmed/Partially-confirmed/Refuted because the acquisition gate blocks an
inferential reading.  Failure of either threshold is reported symmetrically and
cannot be hidden by a sensitivity variant.

## Paper integration rule

After code and artifact review, the M1 paper may call this a fixed-roster ASV5
external replication of **procedure sensitivity**.  It must state the four
detectors, 680,774 fixed trials, 367/370 role structure, 16 observed attacks,
both numeric criteria and the acquisition-law NO-GO.  It may compare the
direction and magnitude with 21DF, but cannot say the 21DF population result
generalizes, that the ASV5 bands have coverage, or that any ASV5 pair is
statistically resolved.

No real score aggregate is authorized until the two new TSVs are complete and
the separate descriptive analyzer plus tests pass a static audit against this
amendment.
