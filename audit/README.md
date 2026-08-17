# Audit package — all 28 comparisons

## Reproducing this

Run these commands from the repository root. The first needs no third-party data;
the latter two need the inputs below:

```
uv run python code/check_numbers.py
uv run python code/make_audit_package.py
diff -u audit/audit.json audit-regenerated/audit.json
uv run python code/check_tie_safety.py
```

**Inputs are not redistributed here** — they are the official ASVspoof 2021 DF key package and
four author-released score files, all publicly downloadable; `audit.json:provenance` gives the
sha256 of each so you can confirm you have the same bytes we did. Point the code at your copies:

| Variable | Default | Holds |
|---|---|---|
| `M1_DATA_ROOT` | `inputs/anti-spoofing` | the DF key package and the official baseline scores |
| `M1_SSL_AASIST_SCORES` | `inputs/anti-spoofing/author-scores/ssl-aasist/Scores_DF.txt` | the SSL-AASIST score file |
| `M1_EXP001_SCORES` | `inputs/exp001-scores` | not needed for anything in this package |

With those set, `make_audit_package.py` regenerates `audit.json` byte-identically under
`audit-regenerated/`; that diff is the input-level check. `check_numbers.py` independently
binds the versioned paper source to the committed derived JSON files in a clean clone.

`audit.json` is derived, never transcribed. If a number here disagrees with the paper, the
paper is wrong.

## The scientific target, stated plainly

The benchmark does not identify paired **ΔEER over new speakers and new attacks**. The 93
speakers and 110 attacks are not a probability sample from a named population, and the later
source/task audit finds that 85.77% of spoof trials lie in four blocks with only 4/4/4/6
speakers. A global exchangeability law is therefore rejected rather than assumed.

The package identifies a fixed-data procedure-sensitivity result. A matched diagnostic uses
the same EER implementation, threshold refit and all-pair max-$t$ rule in both arms: trial-i.i.d.
weights output five of six organiser zero-exclusions while speaker×attack product weights
output zero. A single PSD marginal-sum covariance separately outputs zero of six; it is a
coherent sensitivity construction rather than an exact multiway estimator or coverage claim.
The latter outputs are conditional on provenance
composition—three organiser pairs resolve in at least one leave-one-corpus-out refit—and is
not corrected population inference. EXP-105 additionally refutes low-EER coverage for the
current interval family. The passing organiser-like simulation cells check the implementation
under that imposed DGP; they do not establish the DGP as a model of 21DF.

## What is in the package

| Key | Answers |
|---|---|
| `provenance` | sha256, byte and line counts for all eight score files and the eval key |
| `intersection` | the exact trial-ID rule, and that **all eight systems are scored on the identical set** |
| `eer_rule` | tie/interpolation handling, demonstrated on the observed statistic *and* a bootstrap replicate |
| `cluster_size` | why n₀ = 159.15 rather than 14,869/93 = 159.88 |
| `seeds` | every seed and replicate count in the campaign |
| `incidence` | speaker × attack occupancy, and the bona-fide/spoof speaker asymmetry |
| `contrasts` | all 28 pairs: Δ, product-bootstrap interval, exact-cell simultaneous jackknife interval, verdict |
| `multiway_intersection` | exact speaker, attack and observed-cell variance components; failed CRVE gate |
| `floor_scope` | the withdrawn attack-budget extrapolation and the finite-$A$ component it was based on |
| `finite_A_component_count` | shared-speaker uncertainty for the number of gaps below half that measured component |
| `coverage_mc` | the superseded R=200 pilot, retained as labelled audit history |
| `coverage_validation` | the 48-cell EXP-105 contract, Refuted reading rule, regime-specific coverage and correctness gates |
| `variant_by_pair` | product-bootstrap and exact-cell simultaneous verdicts for every pair |

The post-audit matched and coherent results live under `derived/` rather than the historical
`audit.json` schema. `code/check_numbers.py` binds both to the paper and verifies their plans,
canonical result hashes, historical emitter identities and released path-adapted code hashes.

## Three scope statements the paper depends on

**The attack-budget extrapolation is withdrawn.** Deleting a speaker across the observed
attacks carries both the pure speaker main effect and speaker×attack interaction divided by
the observed attack count. `floor_scope` records the finite-$A$ component and the pairs below
it, but it is not an $A\to\infty$ floor and supports no claim that adding attacks cannot close
a gap.

**EXP-105 refutes the universal coverage claim.** The historical R=200 pilot remains under
`coverage_mc`, explicitly marked superseded. EXP-105 instead runs 1,000 outer replicates and
a 500-draw product bootstrap in each of 48 crossed cells. All 24 organiser cells lie inside
`[.92,.98]`; low-EER coverage falls to `.845/.845/.855`, with all estimators below `.90` in
11 of 24 cells. The clean Gaussian, zero-interaction, two-point-gap cell covers only
`.879/.880/.883`. Modern and Arena intervals are therefore descriptive pending a separately
validated low-EER method.

**The incidence audit refutes global source-blind exchangeability.** Near-complete pooled
speaker×attack occupancy hides four dominant source/task blocks with only 4/4/4/6 spoof
speakers. All full-21DF bands are therefore descriptive outputs, including the organiser
block; another bootstrap on the same rows cannot supply the missing independent units.

**n₀ is the unbalanced effective cluster size, not the mean.** Speakers contribute between 8
and 355 bona-fide trials, so the one-way random-effects n₀ (159.15) is below N/k (159.88).
The design-effect figure uses n₀ — and the same inequality is why that figure is a
back-of-the-envelope approximation rather than an identity: the exact expression assumes
equal-size exchangeable clusters and a linear statistic, where the EER is a thresholded
functional over two crossed factors.

## Known limits

Provenance for the four modern score files is by hash of the released files, not by
re-derivation from audio — we did not retrain or re-score those systems. EXP-105 covers
Gaussian and Student-t(5) effects, but interaction correlation remains fixed at the frozen
calibrated value and absent speaker×attack cells remain unidentified. The corpus
decomposition rests on three source corpora, i.e. two degrees of freedom; the permutation
null (with finite-sample +1 p-values) and leave-one-corpus-out refits, each with its own
28-pair max-t band, are reported for exactly that reason.
