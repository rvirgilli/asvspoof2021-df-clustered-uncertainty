# EXP-104 report — Speech DF Arena replication

## Outcome

**Confirmed.** Both frozen clauses passed on the separate eleven-system
`arena-rescored` layer.

- Two of the ten adjacent leaderboard edges were resolved by the trial-i.i.d.
  all-pair band but unresolved by the speaker×attack all-pair band:
  `HuBERT-ECAPA-Arena vs WavLM-ECAPA-Arena` and
  `AASIST-Arena vs Wav2Vec2-ECAPA-Arena`.
- The median clustered/i.i.d. pointwise-width ratio over all 55 pairs was
  **8.4485**, above the pre-registered threshold of 3.
- The number of resolved comparisons under the 55-pair simultaneous band fell
  from **52/55** under trial-i.i.d. inference to **38/55** under the
  speaker×attack product bootstrap.

This is an independent provenance-stratified replication of the inferential
mechanism. It is not an expansion of, or a replacement for, the primary eight
author/organizer releases.

## Data and inference checks

- All eleven files mapped one-to-one to the same 533,928 ASVspoof 2021 DF eval
  trials, with 93 speakers and 110 spoof attacks.
- No exact duplicate score vectors were found.
- Inference used `B=5000`, seed `20260823`, shared bootstrap weights across all
  systems and all 55 pairs, and one sup-t family over all 55 pairs.
- The trial-i.i.d. and clustered sup-t critical values were 3.157462 and
  3.061613, respectively. The loss of resolution is therefore driven by the
  dependence-aware standard errors, not by a larger multiplicity penalty.

## Provenance sensitivity

Same-named systems were kept outside the rank family, as frozen. Arena and
primary XLSR-Mamba had `r=1.0` at reported precision and equal EER; XLS-R+SLS
also had `r=1.0` at reported precision, with EER 1.9105% versus 1.9161% under
the primary file. Arena RawNet2 was materially different (`r=0.3604`, EER
40.6686% versus 22.3833%), confirming that the Arena layer cannot be silently
pooled with organizer releases.

## Pre-registration accounting

The two frozen reading-rule outcomes were computed exactly as specified. The
EXP-105 secondary analytic estimator is not reported here: its strict
linearization gate failed on real data, and the explicit-cell alternative has
not yet passed the pre-registered interaction-coverage gate. Per the frozen
rule, no unvalidated analytic interval is substituted for the product
bootstrap.

Machine-readable results and file hashes are in `results_arena.json`.
