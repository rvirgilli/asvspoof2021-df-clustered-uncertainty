# EXP-104 — M1 provenance-stratified Speech DF Arena replication

Frozen 2026-08-16 before any pairwise bootstrap, clustered interval, rank
interval or verdict was computed on the Arena files.

- **Line/idea:** M1 · **Priority:** supporting, high-value replication
- **Hypothesis:** the collapse from trial-i.i.d. to speaker×attack inference is
  visible within the independently re-scored Speech DF Arena layer: at least one
  adjacent Arena edge is resolved by trial-i.i.d. inference but unresolved by
  the all-pair clustered simultaneous band, and the median clustered/i.i.d.
  pointwise width ratio across all 55 pairs is at least 3.
- **Why now:** an adversarial audit established that the original eight-system
  pool is not the universe of public scores. The Arena archive contributes eight
  additional system names and fills the performance gap between the modern and
  organizer blocks, but its files are re-scores and cannot be silently mixed
  with author/organizer releases.

## What was already seen before this freeze

The 2026-08-16 adversarial audit inspected the archive member names, row counts
and individual pooled EERs. It also found that Arena RawNet2 is about 40.67% EER
while the organizer release is about 22.38%. Therefore this is not a blind
pre-registration of pooled performance. **No Arena pairwise clustered
bootstrap, pairwise uncertainty result, all-pair band, rank interval, width
ratio or resolved/unresolved verdict had been computed.** Those are the frozen
outcomes below.

## Fixed provenance policy

1. The existing eight author/organizer releases remain the primary
   high-provenance layer and are not replaced.
2. All eleven complete `asvspoof_2021_df.txt` files in the public Arena archive
   form a separate `arena-rescored` layer.
3. Every comparison used for the replication is within that layer. No score
   from an author/organizer release is pooled with an Arena score.
4. Same-named systems across layers are implementation/provenance sensitivity
   checks, not duplicate measurements of one detector. Their EER difference and
   score correlation are reported separately and never enter a rank family.
5. Within the Arena layer, exact duplicate score vectors (if any) are collapsed
   by SHA-256 before inference; aliases and the retained name are reported.
6. A file enters only if its trial IDs map one-to-one onto all 533,928 eval
   trials and its labels agree with the organizer key. There is no
   system-dependent intersection.

## Fixed analysis

- Parse the utterance basename from the first field and the score from the
  second; score orientation is the upstream higher-is-bona-fide contract. No
  orientation is chosen from pairwise outcomes.
- Reproduce pooled non-interpolated EER using the same deterministic tie rule as
  EXP-101.
- Compute every one of the 55 pairwise ΔEERs among the eleven Arena systems.
- Use `B=5000`, seed `20260823`, with one shared set of bootstrap weights per
  replicate across all systems and pairs.
- Baseline A: paired trial-i.i.d. bootstrap.
- Primary estimator: product-weight speaker×attack bootstrap; speaker weights
  apply to every trial, attack weights to spoof trials, and bona fide trials
  receive speaker weights only.
- Secondary estimator: the corrected multiway/influence estimator frozen in
  EXP-105. EXP-104 is not interpreted until EXP-105's correctness checks pass.
- Construct pointwise 95% intervals and a single 95% sup-t band over all 55
  pairs for each estimator. Use the all-pair band to derive rank intervals.
- Define the ten adjacent edges only after sorting the eleven pooled EER point
  estimates. Because selection is score-dependent, all claims about those edges
  use the 55-pair simultaneous band, not a ten-edge family.
- Report all systems, all pairs and both estimators. No result-dependent system
  exclusion or regrouping is allowed.

## Reading rule

- **Confirmed:** both clauses of the hypothesis hold.
- **Partially confirmed:** exactly one clause holds.
- **Refuted:** neither clause holds.

The existing primary result is not killed by a failed Arena replication; a
failure limits its generality and must be reported in the paper.

## Detectability and dependence unit

The evidence units are 93 speakers and 110 spoof attacks, not 533,928 trials and
not 55 pairs. The first clause is itself an interval-level detectability claim:
for every pair the artifact reports the pointwise and simultaneous MDE implied
by its estimated clustered SE. The operationally meaningful minimum is one
adjacent leaderboard edge changing verdict. No analytic iid-n bar is substituted
for the crossed design; coverage and estimator agreement are governed by
EXP-105.

## Budget

CPU only. Runtime is not a decision criterion; all 55 pairs and `B=5000` run.

