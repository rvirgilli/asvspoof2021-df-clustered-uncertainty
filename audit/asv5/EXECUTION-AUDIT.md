# Independent execution-artifact audit — fixed-roster ASVspoof 5 result

Date: 2026-08-17  
Gate: execution artifact, after scoring and before manuscript integration  
Verdict: **PASS**

The auditor worked independently from the implementation and recomputed the
complete descriptive result without importing the analyzer or its core.  The
audit opened no sealed stdout and made no changes to the execution artifacts.

## Authenticated chain

- Result:
  `6667c473df095c39784c2395b6062bbbc06586642d32f03fd43d5633dc657124`
- Run contract:
  `27efe0aceee94e29275130ff1cc39f5518c8fce5771de2b782b033f6e4d348d6`
- Fixed roster: 680,774 trials; 138,688 bona-fide and 542,086 spoof;
  367 target speakers, 370 bona-fide-only non-target speakers, 16 attacks and
  5,872 observed speaker-by-attack cells.
- Input records rehashed: 698; divergences: 0.
- Checkpoint payloads: three complete `(5000, 4)` float64 arrays, all finite,
  each linked to the run contract, analyzer, core, seed and namespace.

Checkpoint data hashes recorded by the independent recomputation:

- trial-i.i.d.: `0fdf3428…`
- role-stratified speaker-by-attack: `a2adf79a…`
- speaker-only: `53e2347a…`

## Independently reproduced result

Fixed-roster pooled EERs:

| Detector | EER (%) |
|---|---:|
| SSL-AASIST | 16.2458 |
| AASIST | 35.5273 |
| XLS-R+SLS | 18.7637 |
| XLSR-Mamba | 14.4014 |

All EERs, six pairwise deltas, bootstrap SDs, percentiles, simultaneous
max-t bands, zero-exclusion flags, band-width ratios and registered A/B
criteria were recomputed and matched the sealed result numerically.

The registered branch is `A=1, B=1`:

- `A=1`: the SSL-AASIST minus XLS-R+SLS trial-i.i.d. band
  `[-2.657, -2.378]` excludes zero, whereas the role-stratified
  speaker-by-attack band `[-6.274, 1.238]` does not;
- `B=1`: the median simultaneous-band width ratio is 27.2676; all six ratios
  lie between 11.23 and 35.90.

## Scientific boundary

This PASS authenticates a fixed-roster external descriptive replication of
sampling-unit sensitivity.  It does **not** authorize population coverage,
significance, generalization to unseen systems/speakers/attacks, or a claim
that zero exclusion is a population verdict.  The acquisition gate remains
NO-GO, so every paper statement must call the bands outputs of the two declared
perturbation procedures on this released roster.
