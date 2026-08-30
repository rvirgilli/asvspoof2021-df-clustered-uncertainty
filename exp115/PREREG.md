# EXP-115 — post-result SpoofCeleb factor decomposition

Frozen on **2026-08-30 before any speaker-only or attack-only result was
computed**. This is a bounded mechanism diagnostic requested after the
prospective EXP-114 result was known. It is not a new confirmation and must
never be described as prospective evidence for the original endpoint.

## Information known at freeze

EXP-114 had already established, on the complete 91,130-trial SpoofCeleb
evaluation grid, that trial-IID max-t bands excluded zero for 6/6 detector
pairs and joint speaker-by-spoof-attack product bands excluded zero for 3/6.
The three changed pairs were known:

- `ssl_aasist vs sls`;
- `ssl_aasist vs xlsr_mamba`;
- `sls vs xlsr_mamba`.

The four score vectors, point EERs, joint-arm output, and all EXP-114 audit
results were known. No speaker-only or attack-only bootstrap result had been
computed or found locally when this diagnostic was designed.

## Fixed inputs

Use the exact provenance-rerun inputs authenticated by EXP-114:

- manifest: 91,130 unique trials, SHA-256
  `008371adaeb300401357a58035d3c4ac9e1c440abe804ceab8ccd1bdc84b2544`;
- AASIST scores:
  `6e75ff20e525713a800e47d756d289604e145f868eed174809c4983fcedac2ad`;
- SSL-AASIST scores:
  `f0237f3712c435157d2cbd5f84f403acf6bea23e2c5553210f8fe276a82743b5`;
- SLS scores:
  `4e83b949a51de18866dd2021559cfe4dcab5df6ff028080e28c7b2c82b8d28c9`;
- XLSR-Mamba scores:
  `5d4c6ca9cc4be52746f7cc1ae2b1007e5dc5e1ca01ddd1221b9560236f1ff835`;
- EXP-114 provenance-rerun result:
  `ff999f5b35ecc77c92299037a07a1700dbed1f88c5ff874a5cbfc3222a6836ae`.

The corpus must retain exactly 9,113 bona-fide trials, 82,017 spoof trials,
40 speakers, nine spoof attacks (`A15`--`A23`), one official source, and 9,113
complete base products, each with `A00` plus all nine spoof renditions.

## Fixed estimand and common inference rule

For the same four systems and all six unordered pairs, estimate the difference
in pooled EER percentage points on the fixed complete roster. Every replicate
refits the tie-aware, non-interpolated weighted-EER threshold. Shared weights
are used across systems within a draw.

Each arm uses `B=5000`, NumPy `default_rng` child streams spawned in the order
below from `SeedSequence(20260830)`, `ddof=1`, and one centered studentized
95% max-absolute-t critical value across all six pairs. NumPy's default linear
quantile is retained. Report the point estimate, bootstrap SD, pointwise
percentile interval, simultaneous interval, complete six-pair verdict vector,
and critical value for both arms.

## Frozen arms

1. **Speaker-only.** Resample the 40 speaker IDs with replacement. All trials
   receive their speaker multiplicity; every spoof-attack multiplicity is
   fixed at one.
2. **Attack-only.** Keep every speaker multiplicity fixed at one. Resample the
   nine spoof attacks with replacement; spoof trials receive their attack
   multiplicity and bona-fide trials retain unit weight.

The arms deliberately change different factors. They are not
composition-preserving: the attack-only arm changes spoof-attack mass, and the
speaker-only arm may change the distribution of base items across speakers.
The single-source design continues to prevent between-source mixture movement.

## Frozen reading

For each of the three already-known joint-sensitive pairs, record whether the
speaker-only interval includes zero and whether the attack-only interval
includes zero. Assign exactly one label:

- `both_one_factor_arms_include_zero`;
- `speaker_only_includes_zero`;
- `attack_only_includes_zero`;
- `neither_one_factor_arm_includes_zero`.

All four branches are publishable. Inclusion under one arm means that factor
alone is sufficient to make that pair unresolved under this declared
procedure; it does not identify a causal variance component. Inclusion under
neither arm means the joint result is interaction-dependent at the decision
level, not that either factor is irrelevant. Counts over all six pairs are
descriptive and cannot replace the complete verdict vectors.

## Guards that can fail

1. Every input must match the hashes above, and the EXP-114 result must contain
   exactly the known 6/6-to-3/6 endpoint and pair identities.
2. The experiment directory, preregistration, analyzer, tests, Python lock,
   and data record must match the committed freeze before analysis.
3. All score files must contain the exact manifest roster once, with finite,
   non-constant scores and the frozen higher-is-bona-fide orientation.
4. Both class masses must be positive and normalize to one in every draw.
5. The speaker-only arm must apply no attack multiplicity; the attack-only arm
   must apply no speaker multiplicity. Synthetic tests exercise both.
6. Each arm must show more than one distinct multiplicity pattern and every
   pair must have positive finite bootstrap SD and more than one distinct
   bootstrap delta.
7. Raw `5000 x 4` bootstrap EER arrays are retained as `.npy` files and
   SHA-bound by the result and run receipt. A stale or changed array must fail
   receipt verification.

If any guard fails, no scientific reading is taken. No failed arm may be
silently replaced, retuned, or rerun with a result-selected seed.

## Limits

This diagnostic decomposes a known fixed-data sensitivity result. It does not
add a corpus, validate a population acquisition law, estimate an independent
speaker or attack variance component, or change EXP-114's confirmatory status.
With only nine spoof attacks, attack-only outputs are resolution-limited by the
observed factor support and must not be generalized beyond the fixed roster.
