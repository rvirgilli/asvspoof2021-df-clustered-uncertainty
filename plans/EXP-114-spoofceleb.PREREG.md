# EXP-114 — prospective SpoofCeleb confirmation of sampling-unit sensitivity

Frozen on **2026-08-29 while access to the official SpoofCeleb repository was
still pending and before any SpoofCeleb audio, score vector, detector metric,
or registered endpoint was available locally**.

This is a one-shot prospective confirmation attempt.  A null or adverse result
will be retained and reported.  It will not trigger replacement of the corpus,
systems, seed, resampling law, endpoint, or reading rule.

## Evidence status at freeze

The corpus was known from its paper and public dataset card.  Local searches
found only bibliographic descriptions and download planning; no SpoofCeleb
audio, manifest, score file, or detector result was present.  A dry-run using
the machine's authenticated Hugging Face identity returned `Access denied`.
The user then submitted the official access request, which remained pending at
freeze.  Dataset structure, labels, and roster counts are design information,
not detector outcomes.

If this preregistration or `analyze.py` changes after any one of the four score
files begins, the result loses prospective-confirmation status.  Mechanical
manifest parsing may be added after access only if it implements the fixed
selection rule below.  Its bytes, the official metadata, and the execution
code must be hash-bound and committed before scoring begins.

## Frozen corpus and roster

Use **every trial in the official SpoofCeleb evaluation SDD protocol**, and no
training, validation, SASV, convenience, quality, duration, or successful-
decode subset.

The public release describes:

- 91,130 evaluation trials;
- 9,113 bona-fide A00 trials and 82,017 spoof trials;
- 40 evaluation speakers, disjoint from training and validation;
- nine evaluation attacks, A15 through A23;
- 9,113 trials for each spoof attack;
- a single source domain, TITW-Easy derived from VoxCeleb1.

The manifest must contain `utt,path,base_id,label,speaker,attack,source`.  It
must establish a complete paired grid: every one of 9,113 base utterances has
exactly one A00 rendition and one rendition from every A15--A23 attack, all
with the same speaker.  `source` must have exactly one value,
`TITW-VoxCeleb1`.  Failure of any census or grid guard aborts the experiment
before scoring.  It may not be repaired by dropping rows or choosing another
subset.

The official archive bytes, official SDD protocol, extracted files, manifest,
and manifest builder will be hash-bound.  The large sequential dataset belongs
under `/media/rv/14bis/data/corpora/anti-spoofing/spoofceleb`, not under the
NVMe project tree.

## Fixed detector family

The four systems are inherited unchanged from EXP-106 and EXP-113.  No system
is trained, calibrated, selected, or removed using SpoofCeleb:

1. AASIST, checkpoint `AASIST.pth`, SHA-256
   `51d2d9cf0738172f61e2a384ec50a54a55363240f67c971ed55a92435bc1a1c0`;
2. SSL-AASIST, checkpoint `LA_model.pth`, SHA-256
   `bd6f36097259fe54e7004eb983651e5304d807be81156dbd04faccb70d91e10c`;
3. XLS-R+SLS, checkpoint `asvdf_sls_best.pth`, SHA-256
   `0d315184aa8e6f017ea72c4d2458c11bae8f07fd743fe860a3aa932e36135fa6`;
4. XLSR-Mamba-LA, checkpoint `model.safetensors`, SHA-256
   `bb8a1af0b3f9ee28dbcfc7c82d733f7cc5fdc77ff3e96b25db7b4ed72f2d1663`.

The shared XLS-R front end has SHA-256
`b08927597f2c9eb2ebd7dcc3ac78ee4b5f6021cbac4b3a6c5a9deec445d80ed9`.
AASIST, SSL-AASIST, and SLS use their canonical 64,600-sample input.  Mamba
uses its registered 66,800-sample ASVspoof input.  Scores are raw
higher-is-bona-fide outputs.  Zero decode failures and a complete common roster
are mandatory.

## Estimand and fixed computation

For each of the six unordered detector pairs, estimate the difference in
pooled EER percentage points on the complete evaluation roster.  Every draw
refits every EER threshold.  Ties use stable score ordering and the frozen
closest-crossing rule in `analyze.py`.

Use `B=5000`, NumPy generator seed `20260829`, shared resampling weights across
all four systems within a draw, `ddof=1`, NumPy's default linear quantile, and
one six-pair 95% centered studentized max-t band per arm.  Preserve unrounded
values in the result artifact.

## Frozen resampling arms

- **A — paired trial-i.i.d.**: sample 91,130 trial indices with replacement.
- **B — global speaker x attack product**: independently resample the 40
  speaker IDs and nine spoof-attack IDs with replacement.  Bona-fide weights
  use speaker multiplicity; spoof weights use speaker times attack
  multiplicity.
- **C — single-source composition-preserving product**: use B's exact draws
  through the independently implemented normalized class/cell-mass pathway.
  Because the official evaluation roster contains one source, C must be
  bit-identical to B.  This equality is an implementation invariant, not
  empirical evidence.

There is deliberately no multi-source arm or TV negative control.  Source
composition cannot drift because the frozen corpus has one source.  Claiming a
scientific composition result from a zero TV value would be invalid; the
scientific evidence is instead the A-versus-C contrast on a corpus whose
design removes the between-source composition degree of freedom.

## Primary hypothesis and reading rule

A detector pair is sampling-unit-sensitive when its arm-A simultaneous
interval excludes zero and its arm-C simultaneous interval includes zero.

- **Prospectively confirmed on SpoofCeleb:** at least one of six pairs meets
  that rule.
- **Not prospectively confirmed on SpoofCeleb:** no pair meets that rule.

Counts and identities for all pairs and arms are reported.  No width ratio,
pointwise interval, EER quality threshold, agreement with EXP-111/113, or
post-hoc detector subset enters the primary reading.

## Guards that can fail

1. The official archive/protocol, extraction, manifest, checkpoints, scoring
   code, dependency locks, analysis code, run contracts, and outputs must be
   hash-bound.  The pre-execution seal must be committed before scoring.  It
   must contain the named bindings enforced by `analyze.py`, the four fixed
   upstream revisions, and clean upstream source worktrees; an arbitrary or
   incomplete list of hashes is not a passing seal.
2. The exact 91,130-row, 40-speaker, A00/A15--A23 complete crossed roster must
   pass.  Duplicate IDs, duplicate paths, missing renditions, extra attacks,
   source multiplicity, or unequal speakers within a base item abort.
3. All four score files must contain the same unique roster, finite nonconstant
   scores, correct orientation contracts, and zero decode failures.
4. Reversed perfect scores must give EER 1 while correctly oriented perfect
   scores give 0.  One-class support and constant score vectors must fail.
5. B and C normalized masses must be array-identical on every draw; every
   per-system replicate EER and every summarized endpoint must consequently be
   identical.  This guards the implementation only.
6. Synthetic fixtures must reach the registered confirmatory and null branches
   and must reject an incomplete crossed grid and a second source.

## Resolution and claim boundary

Nine attack clusters limit generator-side resolution.  Report empirical
bootstrap support and unique endpoint counts; do not print a zero-event
severity as an exact point probability.  Inclusion of zero is not evidence of
equality.

This experiment tests sampling-unit sensitivity for a fixed detector family on
one new, in-the-wild, single-source corpus.  It does not validate the fitted
Gaussian DGP used in the paper's 21DF simulations, identify a population
acquisition law, or establish universality across corpora.  A positive result
strengthens the empirical answer to the composition-confounding objection
without changing M1's scope.
