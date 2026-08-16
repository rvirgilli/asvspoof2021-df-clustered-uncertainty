# Audit package — all 28 comparisons

## Reproducing this

Three commands, given the inputs below:

```
python make_audit_package.py     # regenerates audit.json from the score files and the key
python check_numbers.py          # every number in the paper against a named JSON path
python check_tie_safety.py       # EER tie handling does not move any reported quantity
```

**Inputs are not redistributed here** — they are the official ASVspoof 2021 DF key package and
four author-released score files, all publicly downloadable; `audit.json:provenance` gives the
sha256 of each so you can confirm you have the same bytes we did. Point the code at your copies:

| Variable | Default | Holds |
|---|---|---|
| `M1_DATA_ROOT` | `~/data/corpora/anti-spoofing` | the DF key package and the official baseline scores |
| `M1_SSL_AASIST_SCORES` | `~/projects/academic/SSL_Anti-spoofing/Scores/DF/Scores_DF.txt` | the SSL-AASIST score file |
| `M1_EXP001_SCORES` | an internal scoring-campaign path | not needed for anything in this package |

With those set, `make_audit_package.py` regenerates `audit.json` byte-identically to the
committed copy; that is the check to run first, because a path change should never move a
number.

`audit.json` is derived, never transcribed. If a number here disagrees with the paper, the
paper is wrong.

## The estimand, stated plainly

The target is the paired **ΔEER over speakers and attacks exchangeable with those the
ASVspoof 2021 DF evaluation design represents** — not the 93 speakers and 110 attacks
themselves, and not a probability sample from a named population. Those 93 and 110 were
chosen by the organizers, so **every interval here is conditional on treating them as
exchangeable draws from the design that produced them.** Under trial-level independence,
which is what the organizers' test assumes, 26 of 28 pairs resolve; under speaker×attack
clustering, 18 do. Both answer the same question; they differ in what is held random.

## What is in the package

| Key | Answers |
|---|---|
| `provenance` | sha256, byte and line counts for all eight score files and the eval key |
| `intersection` | the exact trial-ID rule, and that **all eight systems are scored on the identical set** |
| `eer_rule` | tie/interpolation handling, demonstrated on the observed statistic *and* a bootstrap replicate |
| `cluster_size` | why n₀ = 159.15 rather than 14,869/93 = 159.88 |
| `seeds` | every seed and replicate count in the campaign |
| `incidence` | speaker × attack occupancy, and the bona-fide/spoof speaker asymmetry |
| `contrasts` | all 28 pairs: Δ, both certified intervals, the jackknife interval, the verdict |
| `floor_scope` | exactly which pairs the attack-budget statement covers |
| `coverage_mc` | binomial Monte Carlo intervals on every coverage figure |

## Three scope statements the paper depends on

**The attack-budget floor is conditional.** "Adding attacks cannot close the gap" holds *for
the pairs named in `floor_scope`, at the observed effect, with this speaker pool fixed*. A
genuinely new attack family changes the effect itself; nothing here bounds that.

**The simulation checks, it does not certify.** At R = 200 a coverage estimate near .95
carries roughly ±3 points (intervals in `coverage_mc`). The organizer-era and low-EER figures
are all consistent with nominal — the simulation is a failure check, not a certificate, and
one fitted Gaussian family cannot certify coverage under arbitrary dependence.

**n₀ is the unbalanced effective cluster size, not the mean.** Speakers contribute between 8
and 355 bona-fide trials, so the one-way random-effects n₀ (159.15) is below N/k (159.88).
The design-effect figure uses n₀ — and the same inequality is why that figure is a
back-of-the-envelope approximation rather than an identity: the exact expression assumes
equal-size exchangeable clusters and a linear statistic, where the EER is a thresholded
functional over two crossed factors.

## Known limits

Provenance for the four modern score files is by hash of the released files, not by
re-derivation from audio — we did not retrain or re-score those systems. Coverage is checked
under a fitted bivariate-Gaussian random-effects model on the real trial index, which
reproduces organizer-era error rates and does not reproduce the low-EER ones. The corpus
decomposition rests on three source corpora, i.e. two degrees of freedom; the permutation
null and the leave-one-corpus-out refits are reported for exactly that reason.
