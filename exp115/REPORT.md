# EXP-115 — SpoofCeleb factor-decomposition report

## Status

Complete. This is a **post-result mechanism diagnostic**, frozen after EXP-114
was known but before either factor-only arm was computed. It is not prospective
confirmation and does not change EXP-114's evidence status.

Freeze commit: `49b9057b7edba43c3914897d31fdb7917737c379`.

## Question

EXP-114 changed the simultaneous zero-exclusion count from 6/6 under
trial-IID perturbation to 3/6 under joint speaker-by-spoof-attack product
perturbation. With source fixed by the single-source corpus, EXP-115 asks which
factor-only perturbation is sufficient to reproduce those decision changes.

The arms are deliberately not generic composition controls. Speaker-only
resampling changes base-item mass across speakers. Attack-only resampling
changes spoof-attack multiplicities. The target is a transparent decomposition
of the declared product perturbation, not a causal variance decomposition.

## Inputs and computation

- Exact EXP-114 provenance-rerun manifest and four score tables; every input
  matched its frozen SHA-256.
- 91,130 trials, 40 speakers, nine spoof attacks, 9,113 complete ten-rendition
  base products, and one official source.
- `B=5000`, seed `20260830`, two `SeedSequence` child streams, shared system
  weights, threshold refitting, and one six-pair 95% centered studentized max-t
  family per arm.
- Speaker-only critical value: `2.4970260593914175`.
- Attack-only critical value: `2.351227660389506`.

## Result

Speaker-only perturbation excludes zero for **5/6** pairs. Attack-only
perturbation excludes zero for **3/6** pairs and reproduces the complete joint
product verdict vector.

| Already-known joint-sensitive pair | Speaker-only simultaneous band | Attack-only simultaneous band | Factor-only reading |
|---|---:|---:|---|
| SLS -- XLSR-Mamba | [-4.5929, -1.5327] | [-15.6524, 9.5269] | attack-only includes zero |
| SSL-AASIST -- SLS | [0.6550, 3.7587] | [-7.0918, 11.5055] | attack-only includes zero |
| SSL-AASIST -- XLSR-Mamba | [-1.9704, 0.2586] | [-14.7304, 13.0185] | both factor-only arms include zero |

All three AASIST contrasts remain zero-excluding under both factor-only arms.
Across all six pairs, attack-only bootstrap SDs are `0.9632`--`1.0077` times
their joint-product counterparts. The maximum absolute movement between an
attack-only and joint-product simultaneous endpoint is 0.9149 EER points.
These are post-result descriptive comparisons, not registered success
thresholds.

## Interpretation

On this fixed complete SpoofCeleb roster, attack-level perturbation alone is
sufficient to reproduce all three joint-product decision changes. Speaker-level
perturbation alone is sufficient for one of them. The most precise manuscript
claim is therefore not that all composition is fixed or that a latent speaker
variance drives the result. It is that **between-source movement is absent, yet
the declared attack-level sampling unit is sufficient to change three paired
decisions**.

This sharpens rather than widens the paper's identified object. It localizes
the SpoofCeleb effect to sensitivity under the attack perturbation law while
retaining the fixed-score, non-population boundary. It does not establish that
the attack distribution is random, that its nine observed attacks represent a
population, or that the factor-only bands are confidence intervals.

## Verification

- Frozen analyzer tests: 10/10 pass.
- Post-run receipt and failure-injection tests: 4/4 pass; combined suite 14/14.
- Current receipt verifies the frozen sources, result, both raw bootstrap
  arrays, exact EXP-114 result, manifest, and all four score hashes.
- Standalone implementation under `independent/` imports no repository
  analysis code and reproduced both `5000 x 4` arrays byte-for-byte, both
  critical values, every SD, interval, decision, and the 5/6 and 3/6 endpoints.

## Durable derived artifacts

- `RESULTS.json`:
  `d85156dd70c1e312069c664987f0c4fc7eab2f279af471f6fe6eddd2a121673c`.
- `SPEAKER-ONLY-BOOTSTRAP.npy`:
  `1ef95b61935f48c2ec7b499c375979509d757231ab8d80338cec78f0d1cd9d70`.
- `ATTACK-ONLY-BOOTSTRAP.npy`:
  `8b9a28fa2d5cf50db9c6aa6a3050c3f85a7a261f30837c303f433f38058b85d7`.
- `RUN-RECEIPT.json`:
  `9b175358121b41981ac7b95365e53c6b20ca3b98d15dcbcc7d1b194fb0e3b2ed`.
