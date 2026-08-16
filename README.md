# Clustered uncertainty on ASVspoof 2021 DF system comparisons

Code and derived artifacts for a re-analysis of pairwise system comparisons on the
ASVspoof 2021 DeepFake (DF) evaluation set.

## What this is

The DF evaluation set contains 533,928 trials: 14,869 bona fide trials from 93 speakers
and 519,059 spoof trials spanning 110 attack conditions. The significance test published
with the challenge treats trials as independent observations.

This repository contains the estimator, the analysis scripts and a derived audit artifact
for a paired two-way bootstrap that resamples **speakers and attack conditions** rather
than trials, applied to all 28 pairwise comparisons among eight systems whose per-trial
scores are publicly released.

The accompanying paper is under submission. This repository is the artifact a reader needs
to check its numbers; it will be updated as the paper changes.

## Contents

| Path | Contents |
|---|---|
| `ANALYSIS-PLAN.md` | the analysis plan, frozen before the campaign ran |
| `audit/audit.json` | every quantity the paper reports, derived rather than transcribed |
| `audit/README.md` | what each key answers, the estimand, and the scope statements |
| `code/` | the estimator, the analysis scripts, and three checkers |
| `data/README.md` | source, sha256, byte and line counts for all nine input files |

## Reproducing

The inputs are third-party releases and are not redistributed here. Obtain them as
described in [`data/README.md`](data/README.md), set the three environment variables
listed there, then:

```
pip install -r requirements.txt
cd code
python make_audit_package.py    # regenerates audit.json from the score files and key
python check_numbers.py         # every number in the paper against a named JSON path
python check_tie_safety.py      # EER tie handling moves no reported quantity
```

Regeneration writes to `code/audit_package/`, deliberately not over `audit/audit.json`, so
the committed artifact stays available to diff against a fresh run. Regenerated from the
inputs listed in `data/README.md`, the two files are byte-identical.

`audit.json` is derived on every run. If a number in it disagrees with the paper, the
paper is wrong.

Each input file's sha256, byte count and line count is recorded under
`audit.json:provenance`, so a reader can confirm they hold the same bytes used here.

## Estimand

The target is the paired ΔEER over speakers and attack conditions exchangeable with those
the ASVspoof 2021 DF evaluation design represents — not the 93 speakers and 110 attacks
themselves, and not a probability sample from a named population. The organisers selected
those speakers and attacks, so every interval is conditional on treating them as
exchangeable draws from the design that produced them.

Under trial-level independence, which is what the published test assumes, 26 of 28 pairs
resolve. Under speaker × attack clustering, 18 do. Both answer the same question; they
differ in what is held random.

## Known limits

These are stated in full in [`audit/README.md`](audit/README.md). In summary:

- Provenance for the four self-supervised systems is by hash of the released score files.
  Those systems were not retrained or re-scored from audio here.
- Coverage is checked under a fitted bivariate-Gaussian random-effects model on the real
  trial index. It reproduces organiser-era error rates and does not reproduce the low-EER
  ones. At R = 200 replicates a coverage estimate near .95 carries roughly ±3 points, so
  the simulation is a failure check rather than a certificate.
- The corpus decomposition rests on three source corpora, i.e. two degrees of freedom. The
  permutation null and the leave-one-corpus-out refits are reported for that reason.
- The attack-budget statement is conditional on the observed effect and a fixed speaker
  pool. `audit.json:floor_scope` records exactly which pairs it covers.

## License

Code is released under the MIT License (`LICENSE`). The input score files and evaluation
key are covered by their respective original licenses and are not redistributed.
