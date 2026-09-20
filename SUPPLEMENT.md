# Supplementary methods and complete numerical results

Revision: September 20 concentration rewrite. The manuscript cites the immutable artifact commit; prior tags are unchanged.

This document retains the complete technical record for
*Speaker-Group Sensitivity of Paired Detector Comparisons on ASVspoof 2021 DF*.
The submission prints its primary evidence; Arena, fixed weighting and simulations remain artifact-only. All paths below
are relative to the release root unless stated otherwise. The paper's Method defines the
fixed-score scope and design chronology of the added diagnostics. Read S4a for the
four-arm comparison, S4b for Monte Carlo stability, S4c for mean/sign and pairing,
S4d for weighted ties, and S4e for delete-one-group influence.

The release ships [evidence/ABLATION-RESULTS.json](evidence/ABLATION-RESULTS.json),
[evidence/diagnostics.json](evidence/diagnostics.json) and
[evidence/influence.json](evidence/influence.json) without numerical modification.
The analysis drivers are `code/strategy_diagnostics.py` and `code/strategy_influence.py`;
input hashes, seed rules and driver hashes are recorded in the evidence files.

## S1. Data map and terminology

The 21DF analysis uses all 533,928 evaluation-phase trials shared by the eight score files:
14,869 bona-fide and 519,059 spoof trials. A **bona-fide source** is one of the three rows in
the first table. A **spoof stratum** is one of the five source/task rows in the second table.
An **observed cell** is one speaker×attack combination with at least one spoof trial.

| Bona-fide source | Trials | Speakers |
|---|---:|---:|
| ASVspoof | 7,939 | 67 |
| VCC2018 | 3,780 | 12 |
| VCC2020 | 3,150 | 14 |

| Spoof stratum | Trials | Speakers | Attacks | Observed cells |
|---|---:|---:|---:|---:|
| ASVspoof | 73,856 | 48 | 13 | 624 |
| VCC2018/HUB | 121,590 | 4 | 25 | 97 |
| VCC2018/SPO | 60,813 | 4 | 13 | 49 |
| VCC2020/Task1 | 111,600 | 4 | 31 | 124 |
| VCC2020/Task2 | 151,200 | 6 | 28 | 168 |

Thus there are 93 distinct speakers, 110 distinct spoof attacks and 1,062 observed spoof
speaker×attack cells. The **attack family** used by weighting rule S3 is the attack-type
field of the official `trial_metadata.txt` (ninth column), taken verbatim. Its values over
the 519,059 spoof eval trials are:

| Attack-type field value | Spoof trials |
|---|---:|
| traditional_vocoder | 232,594 |
| neural_vocoder_autoregressive | 136,085 |
| neural_vocoder_nonautoregressive | 115,540 |
| unknown | 29,043 |
| waveform_concatenation | 5,797 |

`unknown` is treated as a family of its own; no attack is dropped or relabelled. “Leave one source out” always means deleting ASVspoof, VCC2018 or
VCC2020 as one of these three named top-level sources; it does not mean deleting one of the
five spoof strata.

## S2. EER, contrasts, resampling and separation

Larger scores mean bona fide. The released estimator sorts trial positions by ascending
score. At each position it computes

`FRR = cumulative bona-fide mass / total bona-fide mass`

and

`FAR = 1 - cumulative spoof mass / total spoof mass`.

It selects the first position minimizing `|FRR-FAR|` and returns their mean, without
interpolation. The implementation is a position-wise sweep, not a distinct-score sweep.
An independent distinct-score-boundary recomputation changes every point EER and every
pairwise delta by less than 0.001 EER point on the released score files.

For ordered pair `(A,B)`,

`DeltaEER(A,B) = 100 * (EER(A) - EER(B))` percentage points.

A negative value favors `A`. Every resample refits both thresholds. A pair is **separated
under procedure h** exactly when its simultaneous band excludes zero; this event is
`I[p,h]=1`.

The trial bootstrap resamples trials independently within class (21DF, Arena and
ASVspoof 5). For SpoofCeleb only, the archived plan's arm A samples the 91,130 trial indices
from the pooled list with replacement, so the replicate bona-fide count varies
(Binomial(91,130, 0.1), SD 90.6) instead of staying at 9,113; see S8. The speaker×attack
product-weight bootstrap independently samples 93 speaker multiplicities and 110 attack
multiplicities. A spoof trial's weight is their product; a bona-fide trial has no attack and
receives only its speaker multiplicity. Both use `B=5000`, master seed `2026081604`, separate procedure streams, shared
weights across systems within each replicate, and all 28 contrasts. For procedure `h`, with bootstrap scale `s[p,h]`, its max-t
critical value is the empirical 0.95 quantile of

`max_p |Delta[p,h,b] - mean_b Delta[p,h,b]| / s[p,h]`.

The reported band is `Delta_hat[p] +/- q[.95,h] s[p,h]`.

**Interpretation.** The manuscript's Method states the common scope for every result:
the outputs describe fixed scores under declared laws and weights, not population confidence
or safety. The reporting decision rule is in Discussion. A finite zero count of opposite-sign
draws is not proof of a zero reversal probability. The sign-frequency and centering diagnostics
are separate quantities (S4c).

Product reweighting and its conservatism for crossed-array means are studied by Art B.
Owen and Dean Eckles, “Bootstrapping data arrays of arbitrary order,” *Annals of Applied
Statistics*, 6(3), 895–927, 2012, [doi:10.1214/12-AOAS547](https://doi.org/10.1214/12-AOAS547).
Those results do not establish coverage for these EER bands.

**Source-deletion construction.** Source deletion uses a third construction: with
delete-one speaker, attack and observed-cell jackknife variances `V_s`, `V_a` and `V_sa` of each
contrast, the interval is `Delta_hat +/- q * sqrt(max(V_s+V_a-V_sa, V_s, V_a, 0))`, where `q` is
the 0.95 quantile of the Gaussian max-t statistic over all 28 contrasts under the jackknife
system covariance, recomputed for each remaining subset from 200,000 draws (seed components
`20260822/900/k`). On the full data this construction separates 18/28 pairs (16 cross-cohort,
2 within-SSL, 0 within-baseline), the same verdicts as the PW bootstrap. Deleting ASVspoof,
VCC2018 or VCC2020 gives `q` = 2.874, 2.827 and 2.888 respectively, and the flips against the
full data are: XLSR-Mamba vs
SSL-AASIST ceases to separate without VCC2018; XLS-R+SLS vs SSL-AASIST ceases without VCC2020;
RawNet2 vs CQCC-GMM, LFCC-LCNN vs LFCC-GMM and LFCC-LCNN vs CQCC-GMM become separated in at
least one deletion. Result file: `derived/results_source.json`, key `leave_one_corpus_out`.

For Gaussian calibration, form `Sigma_raw = Sigma_s + Sigma_a - Sigma_sa` from the
delete-one system-EER covariances and obtain `Sigma_PSD` by symmetrizing and replacing
negative eigenvalues with zero. Draw `Z ~ N(0, Sigma_PSD)` and standardize each pair
contrast using its variance under `Sigma_PSD` (implemented as
`sqrt(max(contrast variance,1e-18))` for the zero-scale guard). The final interval radius
uses the separate marginal floor printed above. Implementation: `code/exp101_source.py`,
functions `jack_cov`, `nearest_psd` and the leave-one-corpus-out block in `main`.

The secondary additive marginal-jackknife Gaussian sensitivity analysis uses
`Sigma_plus = Sigma_speaker + Sigma_attack`. It projects the symmetric matrix to positive
semidefinite form by clipping negative eigenvalues at zero, draws 200,000 vectors
`Z ~ N_8(0,Sigma_plus)` with seed `20260824`, forms and standardizes all 28 contrasts, and
uses `sqrt(max(contrast variance,1e-18))` for a zero-scale guard. Its max-t critical value is
`2.878444888` (`2.878` to three decimals); it separates 18/28 pairs and 0/6
organizer-baseline pairs. For RawNet2 minus CQCC-GMM its band is `[-8.76,2.40]`. Because the cell
overlap is not subtracted, this is a deliberately variance-inflating sensitivity analysis,
not an exact multiway estimator or a coverage guarantee.

For RawNet2 minus CQCC-GMM, the point gap is **−3.180** percentage points and the matched simultaneous PW band is **[-9.284, 2.925]**. These values are rounded from `results_matched_iid.json`, `iid.pairs["RawNet2 vs CQCC-GMM"].delta_eer_pts` and `speaker_attack.pairs["RawNet2 vs CQCC-GMM"].simultaneous`; they are a fixed-score procedure-sensitivity example, not a population confidence interval.

The marginal maximum has a max-se antecedent in MacKinnon, Nielsen and Webb,
*Jackknife inference with two-way clustering*, arXiv:2406.08880v4 (2026),
https://arxiv.org/abs/2406.08880v4. Their regression results do not establish coverage
for refitted EER contrasts. The source-deletion results above are a separately specified
sensitivity construction, not another arm of the primary bootstrap.

| Joint-surviving pair | Source omitted | Full gap (points) | Omission gap (points) | Omission separates? |
|---|---|---:|---:|:---:|
| XLSR-Mamba vs SSL-AASIST | VCC2018 | -0.968 | -0.270 | no |
| XLS-R+SLS vs SSL-AASIST | VCC2020 | -0.935 | -0.760 | no |

Both retain their point-order signs. Leave-one-source-out refits preserve separation for
all 16 cross-cohort pairs, remove both separated within-SSL pairs and separate three
within-baseline pairs in at least one deletion. Thus cross-cohort separation survives these
source changes, while some within-cohort separation decisions change with them.

### S2a. Historical paired-test reconstruction

Fig. 4(c) of Yamagishi et al. (2021) does not disclose which Bengio–Mariéthoz variant
produced its matrix, so we make no cell-level attribution. Both reconstructions of Fig. 4(c)
(independent-trial and shared-trial) separate the same five of six baseline pairs; we claim
no cell-level agreement. The published 34-system matrix has 561 tests. In the independent-trial
reconstruction, the largest p among the five separated pairs, 9.7e-6, is below even its
Bonferroni threshold .05/561, approximately 8.9e-5, while the sixth has p=.217.
The cited derivation assumes thresholds fixed outside the test set, so these are
reconstructions of its adaptation to EER rather than exact finite-sample tests.
Source: `derived/results_organizer_test.json`, `pairs` (independent-trial and shared-trial
statistics); the comparison is historical context, not validation of the main bands.

## S3. Complete 21DF point results

Here `SLS` abbreviates `XLS-R+SLS`; `XLSR+SLS` is a spelling alias for the same detector name.

| System | Score-file release | EER (%) | Point rank |
|---|---|---:|---:|
| XLSR-Mamba | model author | 1.884 | 1 |
| XLS-R+SLS | model author | 1.916 | 2 |
| XLSR-Conformer | model author | 2.273 | 3 |
| SSL-AASIST | model author | 2.852 | 4 |
| RawNet2 | ASVspoof organizer | 22.383 | 5 |
| LFCC-LCNN | ASVspoof organizer | 23.477 | 6 |
| LFCC-GMM | ASVspoof organizer | 25.247 | 7 |
| CQCC-GMM | ASVspoof organizer | 25.563 | 8 |

## S4. Complete 28-pair simultaneous-band table

All values are EER percentage points. `T sep.` and `PW sep.` are the two separation
indicators. These rows are the numerical support for every `26/28`, `18/28`, `5/6` and
`0/6` statement in the paper.

| A | B | Delta(A-B) | Trial 95% simultaneous band | T sep. | PW 95% simultaneous band | PW sep. |
|---|---|---:|---:|:---:|---:|:---:|
| XLSR-Mamba | XLS-R+SLS | -0.032130 | [-0.144037, 0.079778] | no | [-0.725307, 0.661048] | no |
| XLSR-Mamba | XLSR-Conformer | -0.389234 | [-0.570024, -0.208445] | yes | [-1.348081, 0.569612] | no |
| XLSR-Mamba | SSL-AASIST | -0.967604 | [-1.174902, -0.760306] | yes | [-1.827816, -0.107392] | yes |
| XLSR-Mamba | RawNet2 | -20.499407 | [-21.070188, -19.928626] | yes | [-26.949685, -14.049129] | yes |
| XLSR-Mamba | LFCC-LCNN | -21.593130 | [-22.123222, -21.063038] | yes | [-27.444664, -15.741595] | yes |
| XLSR-Mamba | LFCC-GMM | -23.363258 | [-23.980830, -22.745685] | yes | [-29.462125, -17.264390] | yes |
| XLSR-Mamba | CQCC-GMM | -23.679283 | [-24.364178, -22.994387] | yes | [-29.246867, -18.111699] | yes |
| XLS-R+SLS | XLSR-Conformer | -0.357105 | [-0.537688, -0.176521] | yes | [-1.492950, 0.778741] | no |
| XLS-R+SLS | SSL-AASIST | -0.935474 | [-1.140571, -0.730377] | yes | [-1.783624, -0.087324] | yes |
| XLS-R+SLS | RawNet2 | -20.467277 | [-21.038884, -19.895670] | yes | [-26.958382, -13.976173] | yes |
| XLS-R+SLS | LFCC-LCNN | -21.561000 | [-22.089936, -21.032065] | yes | [-27.439585, -15.682415] | yes |
| XLS-R+SLS | LFCC-GMM | -23.331128 | [-23.947902, -22.714355] | yes | [-29.468602, -17.193654] | yes |
| XLS-R+SLS | CQCC-GMM | -23.647153 | [-24.330222, -22.964084] | yes | [-29.216117, -18.078189] | yes |
| XLSR-Conformer | SSL-AASIST | -0.578369 | [-0.834918, -0.321820] | yes | [-1.636891, 0.480152] | no |
| XLSR-Conformer | RawNet2 | -20.110173 | [-20.672859, -19.547486] | yes | [-26.306745, -13.913601] | yes |
| XLSR-Conformer | LFCC-LCNN | -21.203896 | [-21.726182, -20.681609] | yes | [-26.757261, -15.650530] | yes |
| XLSR-Conformer | LFCC-GMM | -22.974023 | [-23.587262, -22.360785] | yes | [-28.898893, -17.049154] | yes |
| XLSR-Conformer | CQCC-GMM | -23.290049 | [-23.964374, -22.615723] | yes | [-28.708961, -17.871136] | yes |
| SSL-AASIST | RawNet2 | -19.531803 | [-20.118497, -18.945109] | yes | [-25.738877, -13.324730] | yes |
| SSL-AASIST | LFCC-LCNN | -20.625526 | [-21.171401, -20.079651] | yes | [-26.214636, -15.036417] | yes |
| SSL-AASIST | LFCC-GMM | -22.395654 | [-23.028473, -21.762835] | yes | [-28.398920, -16.392388] | yes |
| SSL-AASIST | CQCC-GMM | -22.711679 | [-23.406084, -22.017274] | yes | [-28.122807, -17.300552] | yes |
| RawNet2 | LFCC-LCNN | -1.093723 | [-1.721589, -0.465857] | yes | [-5.527954, 3.340508] | no |
| RawNet2 | LFCC-GMM | -2.863851 | [-3.654035, -2.073667] | yes | [-9.948626, 4.220925] | no |
| RawNet2 | CQCC-GMM | -3.179876 | [-4.003326, -2.356426] | yes | [-9.284290, 2.924538] | no |
| LFCC-LCNN | LFCC-GMM | -1.770128 | [-2.426145, -1.114111] | yes | [-6.490406, 2.950150] | no |
| LFCC-LCNN | CQCC-GMM | -2.086153 | [-2.765372, -1.406934] | yes | [-6.173476, 2.001170] | no |
| LFCC-GMM | CQCC-GMM | -0.316025 | [-0.928617, 0.296567] | no | [-3.369889, 2.737839] | no |

The 16 cross-cohort gaps span 19.5–23.7 points. Over all primary pairs, PW simultaneous
bands are 4.13–11.36 times wider than matched trial bands (median 8.14). The two within-SSL
pairs separated by PW have gaps 0.968 and 0.935 points; each ceases to separate under one
source deletion in the separate jackknife construction of S2.

### S4a. Primary-21DF factor ablation

**Evidence.** All entries below are transcribed from
[evidence/ABLATION-RESULTS.json](evidence/ABLATION-RESULTS.json). The trial and joint
summaries are unchanged copies of the primary results. The Method states the one-factor diagnostics' design chronology and exploratory scope.

**Fixed roster and estimator.** All arms use the same 533,928 evaluation trials
(14,869 bona fide, 519,059 spoof), 93 speakers and 110 spoof attacks. The four
self-supervised (SSL) detectors are XLSR-Mamba, XLS-R+SLS, XLSR-Conformer and SSL-AASIST;
the four organizer baselines are RawNet2, LFCC-LCNN, LFCC-GMM and CQCC-GMM. All nine
score-file/protocol hashes match the primary matched comparison, as recorded in
`inputs.sha256` and `inputs.all_inputs_match_published_hashes`.

The EER estimator is unchanged in every arm. Larger scores mean bona fide. Sort trial
positions in ascending score order; at each position FRR is cumulative bona-fide weight
divided by total bona-fide weight, and FAR is one minus cumulative spoof weight divided
by total spoof weight. Select the first position minimizing `|FRR-FAR|` and take their
mean, without interpolation. This is the position-wise sweep, not a distinct-score-boundary
sweep. Each replicate refits every system's threshold using that replicate's weights.
For each ordered pair `(A,B)`, `Delta = 100 * (EER(A) - EER(B))` in percentage points;
negative favors A. Original estimates use empirical trial weights normalized within
class and are the same in all arms.

**Four resampling laws.** Each arm uses `B=5000` replicates. All eight systems share a
replicate's trial weights, preserving their pairing.

- **Trial:** independently sample trials with replacement within each class, retaining
  the original class counts; weights are the trial multiplicities.
- **Speaker-only:** draw 93 speakers with replacement uniformly from the 93 observed
  speakers. Each trial receives its speaker's multiplicity, shared across bona-fide and
  spoof trials; attack weights are fixed at one.
- **Attack-only:** draw 110 attacks with replacement uniformly from the 110 observed spoof
  attacks. Spoof trials receive their attack's multiplicity; speaker weights and all
  bona-fide trial weights stay one.
- **Speaker × attack:** independently draw the speaker and attack multiplicities just
  defined. Each spoof trial receives their product, and each bona-fide trial receives
  only its speaker's multiplicity.

Thus the speaker and attack counts are multinomial draws with equal probabilities over
their respective observed levels. The one-factor implementations use
`exp101_selection.load_21df`, `clustered_eer_replicates` and the unchanged
`m1_campaign.weighted_eer`: speaker-only sets `att_idx=None`; attack-only uses one
degenerate speaker cluster to fix speaker weights at one. These are implementation
identifiers for the estimator and laws defined above.

**Seed streams.** The complete campaign-derived rule is
`children = np.random.SeedSequence(2026081604).spawn(4)`, followed by
`np.random.default_rng(children[k])` for the arm's child. Trial retains spawn key `(0,)`,
joint speaker × attack retains `(1,)`, speaker-only appends `(2,)`, and attack-only
appends `(3,)`. Appending children leaves the original two streams unchanged. Workers
receive saved states of these sequential streams at block boundaries, with no per-worker
seeds. The recorded NumPy version is `2.4.6`. The artifact reports exact agreement across
block partitions, exact summary reconstruction from saved replicates, and agreement of
the first three replicates of each new arm with direct factor weights and the unchanged
weighted EER function. These are the existing verification records, not new runs.

**Full-family construction.** For arm `h` and pair `p`, let `Delta[p,h,b]` be the
replicate contrast, `mean_b Delta[p,h,b]` its bootstrap mean, and `s[p,h]` its sample
standard deviation across the 5000 replicates (`ddof=1`). For every replicate form

`T[h,b] = max over all 28 pairs p of |Delta[p,h,b] - mean_b Delta[p,h,b]| / s[p,h]`.

The arm's `q[.95,h]` is the empirical 95th percentile of those maxima; report
`Delta_hat[p] +/- q[.95,h] * s[p,h]`, centered on the original contrast. This is
`exp101_matched_iid.summarize` in the record. Each arm has its own standard deviations
and critical value. All 28 pairs enter every maximum, including cross-cohort pairs;
subgroup counts use these same bands without separate subgroup corrections. Separation
means the band excludes zero. These are the fixed-score sensitivity bands defined in Method.

| Arm | q.95 |
|---|---:|
| Trial | 2.940238 |
| Speaker-only | 2.890609 |
| Attack-only | 2.887804 |
| Speaker × attack | 2.996669 |

Arm names describe what is resampled. Daggered counts are the recorded-seed result; S4b quantifies their Monte Carlo sensitivity.

| Arm | All /28 | Organizer /6 | Within-SSL /6 | Cross-cohort /16 |
|---|---:|---:|---:|---:|
| Trial | 26 | 5 | 5 | 16 |
| Speaker-only | 18 | 0 | 2 | 16 |
| Attack-only | 22† | 3† | 3 | 16 |
| Speaker × attack | 18 | 0 | 2 | 16 |

**Pair identities and interpretation.** Speaker-only reproduces the joint procedure's eight
lost separations on this roster; attack-only reproduces four or five of the eight joint
losses across Monte Carlo repeats (S4b). The inventory below is the recorded-seed result.
Speaker-only and joint resampling
have the same indicator for every named pair in the complete table below; equal counts
alone would not establish that result.

Every row in the following inventory is separated by trial resampling and loses separation
under joint speaker × attack resampling. “Yes” means the one-factor arm also loses that
separation; “no” means it retains it.

| Pair | Speaker-only | Attack-only |
|---|:---:|:---:|
| XLSR-Mamba vs XLSR-Conformer | yes | yes |
| XLS-R+SLS vs XLSR-Conformer | yes | yes |
| XLSR-Conformer vs SSL-AASIST | yes | no |
| RawNet2 vs LFCC-LCNN | yes | yes |
| RawNet2 vs LFCC-GMM | yes | no |
| RawNet2 vs CQCC-GMM | yes | no |
| LFCC-LCNN vs LFCC-GMM | yes | yes |
| LFCC-LCNN vs CQCC-GMM | yes | no |

Attack-only therefore reproduces the losses of XLSR-Mamba vs XLSR-Conformer,
XLS-R+SLS vs XLSR-Conformer, RawNet2 vs LFCC-LCNN, and LFCC-LCNN vs LFCC-GMM.
The two SSL pairs separated under **both speaker-only and joint** resampling are
**XLSR-Mamba vs SSL-AASIST** and **XLS-R+SLS vs SSL-AASIST**. Both also remain separated
under trial and attack-only resampling. Attack-only additionally separates
XLSR-Conformer vs SSL-AASIST; trial additionally separates that pair, XLSR-Mamba vs
XLSR-Conformer, and XLS-R+SLS vs XLSR-Conformer. XLSR-Mamba vs XLS-R+SLS and LFCC-GMM vs
CQCC-GMM remain unseparated under every arm. All 16 named cross-cohort pairs below
remain separated under every arm.

**Complete separation indicators.** Here “yes” means separated, not loss of separation.
The order is the artifact's pair order; no pair was selected by its result.

| Pair | Trial | Speaker-only | Attack-only | Speaker × attack |
|---|:---:|:---:|:---:|:---:|
| XLSR-Mamba vs XLS-R+SLS | no | no | no | no |
| XLSR-Mamba vs XLSR-Conformer | yes | no | no | no |
| XLSR-Mamba vs SSL-AASIST | yes | yes | yes | yes |
| XLSR-Mamba vs RawNet2 | yes | yes | yes | yes |
| XLSR-Mamba vs LFCC-LCNN | yes | yes | yes | yes |
| XLSR-Mamba vs LFCC-GMM | yes | yes | yes | yes |
| XLSR-Mamba vs CQCC-GMM | yes | yes | yes | yes |
| XLS-R+SLS vs XLSR-Conformer | yes | no | no | no |
| XLS-R+SLS vs SSL-AASIST | yes | yes | yes | yes |
| XLS-R+SLS vs RawNet2 | yes | yes | yes | yes |
| XLS-R+SLS vs LFCC-LCNN | yes | yes | yes | yes |
| XLS-R+SLS vs LFCC-GMM | yes | yes | yes | yes |
| XLS-R+SLS vs CQCC-GMM | yes | yes | yes | yes |
| XLSR-Conformer vs SSL-AASIST | yes | no | yes | no |
| XLSR-Conformer vs RawNet2 | yes | yes | yes | yes |
| XLSR-Conformer vs LFCC-LCNN | yes | yes | yes | yes |
| XLSR-Conformer vs LFCC-GMM | yes | yes | yes | yes |
| XLSR-Conformer vs CQCC-GMM | yes | yes | yes | yes |
| SSL-AASIST vs RawNet2 | yes | yes | yes | yes |
| SSL-AASIST vs LFCC-LCNN | yes | yes | yes | yes |
| SSL-AASIST vs LFCC-GMM | yes | yes | yes | yes |
| SSL-AASIST vs CQCC-GMM | yes | yes | yes | yes |
| RawNet2 vs LFCC-LCNN | yes | no | no | no |
| RawNet2 vs LFCC-GMM | yes | no | yes | no |
| RawNet2 vs CQCC-GMM | yes | no | yes | no |
| LFCC-LCNN vs LFCC-GMM | yes | no | no | no |
| LFCC-LCNN vs CQCC-GMM | yes | no | yes | no |
| LFCC-GMM vs CQCC-GMM | no | no | no | no |

**Complete simultaneous bands (EER percentage points).** Pair direction is A minus B
as named by “A vs B”; each interval below is copied at the six-decimal precision stored
in `simultaneous`. The common point contrasts are copied from `delta_eer_pts`. These are
the full-family bands defined above, not the artifact's pointwise percentile intervals.

| Pair | Delta | Trial band | Speaker-only band | Attack-only band | Speaker × attack band |
|---|---:|---|---|---|---|
| XLSR-Mamba vs XLS-R+SLS | -0.032130 | [-0.144037, 0.079778] | [-0.457634, 0.393375] | [-0.536119, 0.471860] | [-0.725307, 0.661048] |
| XLSR-Mamba vs XLSR-Conformer | -0.389234 | [-0.570024, -0.208445] | [-1.172086, 0.393618] | [-0.814703, 0.036235] | [-1.348081, 0.569612] |
| XLSR-Mamba vs SSL-AASIST | -0.967604 | [-1.174902, -0.760306] | [-1.760857, -0.174350] | [-1.214382, -0.720825] | [-1.827816, -0.107392] |
| XLSR-Mamba vs RawNet2 | -20.499407 | [-21.070188, -19.928626] | [-26.386349, -14.612465] | [-22.660816, -18.337997] | [-26.949685, -14.049129] |
| XLSR-Mamba vs LFCC-LCNN | -21.593130 | [-22.123222, -21.063038] | [-26.722574, -16.463686] | [-23.871153, -19.315107] | [-27.444664, -15.741595] |
| XLSR-Mamba vs LFCC-GMM | -23.363258 | [-23.980830, -22.745685] | [-28.468195, -18.258321] | [-25.977707, -20.748808] | [-29.462125, -17.264390] |
| XLSR-Mamba vs CQCC-GMM | -23.679283 | [-24.364178, -22.994387] | [-28.395216, -18.963350] | [-26.155690, -21.202876] | [-29.246867, -18.111699] |
| XLS-R+SLS vs XLSR-Conformer | -0.357105 | [-0.537688, -0.176521] | [-1.191055, 0.476845] | [-1.000877, 0.286668] | [-1.492950, 0.778741] |
| XLS-R+SLS vs SSL-AASIST | -0.935474 | [-1.140571, -0.730377] | [-1.595547, -0.275401] | [-1.387343, -0.483605] | [-1.783624, -0.087324] |
| XLS-R+SLS vs RawNet2 | -20.467277 | [-21.038884, -19.895670] | [-26.440245, -14.494310] | [-22.534966, -18.399589] | [-26.958382, -13.976173] |
| XLS-R+SLS vs LFCC-LCNN | -21.561000 | [-22.089936, -21.032065] | [-26.777669, -16.344331] | [-23.711405, -19.410595] | [-27.439585, -15.682415] |
| XLS-R+SLS vs LFCC-GMM | -23.331128 | [-23.947902, -22.714355] | [-28.507968, -18.154288] | [-25.901004, -20.761252] | [-29.468602, -17.193654] |
| XLS-R+SLS vs CQCC-GMM | -23.647153 | [-24.330222, -22.964084] | [-28.457437, -18.836870] | [-25.966950, -21.327356] | [-29.216117, -18.078189] |
| XLSR-Conformer vs SSL-AASIST | -0.578369 | [-0.834918, -0.321820] | [-1.428012, 0.271273] | [-1.075139, -0.081600] | [-1.636891, 0.480152] |
| XLSR-Conformer vs RawNet2 | -20.110173 | [-20.672859, -19.547486] | [-25.778284, -14.442062] | [-22.165021, -18.055325] | [-26.306745, -13.913601] |
| XLSR-Conformer vs LFCC-LCNN | -21.203896 | [-21.726182, -20.681609] | [-26.064402, -16.343390] | [-23.393428, -19.014363] | [-26.757261, -15.650530] |
| XLSR-Conformer vs LFCC-GMM | -22.974023 | [-23.587262, -22.360785] | [-27.903658, -18.044389] | [-25.549988, -20.398059] | [-28.898893, -17.049154] |
| XLSR-Conformer vs CQCC-GMM | -23.290049 | [-23.964374, -22.615723] | [-27.826501, -18.753596] | [-25.759126, -20.820971] | [-28.708961, -17.871136] |
| SSL-AASIST vs RawNet2 | -19.531803 | [-20.118497, -18.945109] | [-25.133666, -13.929940] | [-21.730757, -17.332849] | [-25.738877, -13.324730] |
| SSL-AASIST vs LFCC-LCNN | -20.625526 | [-21.171401, -20.079651] | [-25.457669, -15.793384] | [-22.907562, -18.343491] | [-26.214636, -15.036417] |
| SSL-AASIST vs LFCC-GMM | -22.395654 | [-23.028473, -21.762835] | [-27.400672, -17.390636] | [-25.009160, -19.782148] | [-28.398920, -16.392388] |
| SSL-AASIST vs CQCC-GMM | -22.711679 | [-23.406084, -22.017274] | [-27.270137, -18.153221] | [-25.162891, -20.260467] | [-28.122807, -17.300552] |
| RawNet2 vs LFCC-LCNN | -1.093723 | [-1.721589, -0.465857] | [-4.910691, 2.723245] | [-2.894162, 0.706716] | [-5.527954, 3.340508] |
| RawNet2 vs LFCC-GMM | -2.863851 | [-3.654035, -2.073667] | [-9.005362, 3.277660] | [-5.579829, -0.147872] | [-9.948626, 4.220925] |
| RawNet2 vs CQCC-GMM | -3.179876 | [-4.003326, -2.356426] | [-8.450051, 2.090299] | [-5.647123, -0.712628] | [-9.284290, 2.924538] |
| LFCC-LCNN vs LFCC-GMM | -1.770128 | [-2.426145, -1.114111] | [-5.651004, 2.110748] | [-3.851880, 0.311624] | [-6.490406, 2.950150] |
| LFCC-LCNN vs CQCC-GMM | -2.086153 | [-2.765372, -1.406934] | [-5.280776, 1.108471] | [-4.168667, -0.003639] | [-6.173476, 2.001170] |
| LFCC-GMM vs CQCC-GMM | -0.316025 | [-0.928617, 0.296567] | [-2.626158, 1.994108] | [-1.817707, 1.185656] | [-3.369889, 2.737839] |

**Machine-readable selectors.** In `evidence/ABLATION-RESULTS.json`, use
`arms.<arm>.summary.pairs["A vs B"].simultaneous`, `.delta_eer_pts` and
`.resolved_simultaneous`, where `<arm>` is `trial`, `speaker_only`, `attack_only` or
`speaker_attack`. Critical values are at `arms.<arm>.summary.supt_critical_value`;
counts at `arms.<arm>.counts`; the loss inventory at `lost_separations`; and the
procedure, input and verification records at `method`, `seed_rule`, `inputs.sha256`
and `verification`. Replicate-array hashes and execution identifiers are at `replicates` and `environment`
in that JSON; these tables require only its aggregate records. The result is limited to this fixed primary-21DF
roster. In the separate exploratory SpoofCeleb comparison, speaker-only separates 5/6
and attack-only 3/6, with attack-only matching the joint indicator vector. Neither roster
establishes a universal dominant factor.

### S4b. Attack-only Monte Carlo stability

The near-zero endpoint is LFCC-LCNN minus CQCC-GMM, gap -2.086153 points. All calculations
retain the original empirical weights, refitted EER thresholds and full 28-pair maximum.
The five fresh streams were specified before inspecting their endpoints using
`SeedSequence(2026091601).spawn(5)`, with spawn keys 0 through 4. The original stream is
master `2026081604`, spawn key 3. The pooled estimate uses the five fresh streams only;
it supplements rather than replaces the recorded-seed 5,000-draw result.

| Attack-only calculation | Draws | Upper endpoint (points) | Separated /28 | Organizer /6 |
|---|---:|---:|---:|---:|
| Recorded seed† | 5,000 | -0.003639 | 22/28 | 3/6 |
| Fresh stream 0 | 5,000 | +0.030313 | 21/28 | 2/6 |
| Fresh stream 1 | 5,000 | +0.011967 | 21/28 | 2/6 |
| Fresh stream 2 | 5,000 | +0.046927 | 21/28 | 2/6 |
| Fresh stream 3 | 5,000 | -0.032615 | 22/28 | 3/6 |
| Fresh stream 4 | 5,000 | +0.025310 | 21/28 | 2/6 |
| Five fresh streams pooled | 25,000 | +0.014968 | 21/28 | 2/6 |

Four of five fresh seeds lose the recorded-seed separation; no other indicator changes.
Thus attack-only reproduces four or five of the eight joint losses across Monte Carlo
repeats. The dagger preserves the original result rather than silently selecting a seed.
Resampling complete rows of the original attack array 1,000 times (5,000 draws per resample,
recomputing pair SDs and all-pair max-t each time) gives endpoint percentiles
[-0.052384, +0.046514]; 56.2% remain below zero. These measure simulation noise conditional
on the saved perturbation distribution, not detector-performance uncertainty. The exact
seed and endpoint quantiles are at `seed_rule.mc_rows_seed` and `saved_attack_endpoint_mc`.
The historical 2026091601 repeat study covers attack-only; the separate September 20 study below adds fresh streams for trial, speaker-only and joint resampling. Selectors: `results.attack_only`, `results.attack_repeat_0` through
`results.attack_repeat_4`, and `results.attack_repeats_pooled_25000`, with `.count` and
`.pairs["LFCC-LCNN vs CQCC-GMM"].hi`.

### S4b.1. Additional primary Monte Carlo verification

The new conditional check uses NumPy 2.4.6 and `SeedSequence(2026092001).spawn(3)` in trial, speaker_attack, speaker_only order, with 1,000 successive complete-row resamples of size 5,000 per arm.
Every resample recomputes all 28 contrasts, sample SDs with `ddof=1`, the centered maximum and the default linear 0.95 quantile, using unrounded original hats from `evidence/diagnostics.json`.
No separation indicator changes; all-pair, SSL and organizer count ranges are respectively 26–26/28, 5–5/6 and 5–5/6 for trial, and 18–18/28, 2–2/6 and 0–0/6 for speaker-only and joint.
This assesses Monte Carlo noise conditional on the saved rows, not independent streams, unobserved tails or population coverage.

The separate fresh study fixes `SeedSequence(2026092002).spawn(3)` in the same arm order, then `.spawn(5)` for each arm, before examining results, with 5,000 score-level draws per stream.
All 15 streams preserve every recorded primary separation indicator, including all sixteen cross-cohort contrasts; trial counts are 26/28 overall, 5/6 SSL and 5/6 organizer, while speaker-only and joint give 18/28, 2/6 and 0/6.
Every draw refits all eight thresholds under the original first-minimum EER rule; the Numba loop (no fastmath) matches both the NumPy estimator and the first ten archived draws per primary arm with zero maximum error.
The fresh study measures stability under the declared resampling laws, without validating them as population sampling models.

`evidence/REVISION-MC-PLAN.md` fixes both protocols; `code/revision_mc.py` produces the checks.
`evidence/revision-conditional.json` and `revision-conditional-traces.npz` contain the conditional counts and complete q/SD/indicator traces; `revision-fresh.json` and `revision-fresh-replicates.npz` contain every fresh endpoint and all fifteen eight-system arrays.
The separately implemented `code/verify_revision_mc.py` recomputes conditional results using row multiplicities and weighted moments, then explicitly interpolates the sorted maximum distribution; it also reconstructs every fresh band from the archived arrays.
The conditional arithmetic differs by at most 3.87e-14, with identical indicators; `evidence/revision-mc-verification.json` binds all inputs and outputs and records the verification.

### S4c. Mean displacement, sign frequency and paired cancellation

For Mamba minus Conformer, the original gap is -0.389234 points. Mean shift is
`mean_b Delta_b - Delta_hat`; pair SD uses `ddof=1`. Opposite sign means
`Delta_b * Delta_hat < 0`. The main table rounds these same quantities.

| Law | Mean shift (points) | Pair SD (points) | Opposite-sign draws | Frequency | Full-family band excludes zero? |
|---|---:|---:|---:|---:|:---:|
| Trial | -0.002492 | 0.061488 | 0/5,000 | 0.00% | yes |
| Speaker-only | -0.003175 | 0.270826 | 210/5,000 | 4.20% | no |
| Attack-only | -0.010235 | 0.147333 | 37/5,000 | 0.74% | no |
| Joint | -0.010135 | 0.319971 | 463/5,000 | 9.26% | no |

The joint displacement is -0.010135 points, or -0.032 SD: its magnitude is too small to
explain zero inclusion by changing the band center. Its opposite-sign frequency is 9.26%,
with Monte Carlo SE 0.41 percentage points. For attack-only, just 0.74% of draws have the
opposite sign, and the pointwise percentile interval is [-0.665064, -0.093474], yet the
simultaneous original-estimate-centered band includes zero. Band inclusion is therefore
not a sign-frequency statement. All these values are at
`results.<law>.pairs["XLSR-Mamba vs XLSR-Conformer"]` in `evidence/diagnostics.json`:
`mean_shift`, `sd`, `mean_shift_over_sd`, `opposite_sign_frequency`, `sign_frequency_mcse`
and `percentiles_2p5_97p5`.

Joint Mamba/Conformer EER correlation is 0.777092 (0.777 in the paper). The paired-to-unpaired
variance ratio is 0.248131:
`Var(EER_A-EER_B)/(Var(EER_A)+Var(EER_B))`.
Thus covariance cancellation removes 75.19% (about 75%) of the sum of marginal variances.
The paired SD nevertheless rises from 0.06149 to 0.31997 points between the trial and
joint laws. This is covariance algebra on the paired draws. The JSON selectors are
`correlation` and `paired_over_unpaired_variance` in the same pair record.

**Comparison-family and roster checks.** Recomputing the maximum over only the six SSL
pairs yields the following separate sensitivity check; these are not the subset counts
in Table 1, which retain the full 28-pair maximum.

| Law | Six-SSL-family separated /6 | Shared Mamba/SLS/SSL-AASIST subset under original 28-pair maximum |
|---|---:|---:|
| Trial | 5/6 | 2/3 |
| Speaker-only | 2/6 | 2/3 |
| Attack-only | 4/6 | 2/3 |
| Joint | 2/6 | 2/3 |

All three primary within-SSL trial-to-joint losses involve Conformer. The three detectors
shared with SpoofCeleb retain 2/3 separated in every primary arm. Selectors:
`results.<law>.ssl_six_family` for the restricted family, and the three named `.pairs`
records for the shared-roster subset. This post-result family restriction leaves the
primary all-28 construction unchanged.

### S4d. Weighted distinct-score threshold check

On identical weights, the diagnostic recomputes the position-wise and distinct-score-boundary
EER sweeps for all eight systems in each of nine runs, 45,000 weighted replicates in total.
Each convention uses its corresponding original point estimators and complete max-t bands.

| Run | Replicates | Max single EER change (points) | Max pair-band endpoint change (points) | Changed indicators |
|---|---:|---:|---:|---:|
| trial | 5,000 | 0.010088 | 0.000110 | 0 |
| speaker_only | 5,000 | 0.007122 | 0.000100 | 0 |
| attack_only | 5,000 | 0.003363 | 0.000233 | 0 |
| speaker_attack | 5,000 | 0.019166 | 0.000121 | 0 |
| attack_repeat_0 | 5,000 | 0.003363 | 0.000109 | 0 |
| attack_repeat_1 | 5,000 | 0.003363 | 0.000109 | 0 |
| attack_repeat_2 | 5,000 | 0.003363 | 0.000112 | 0 |
| attack_repeat_3 | 5,000 | 0.003363 | 0.000118 | 0 |
| attack_repeat_4 | 5,000 | 0.003363 | 0.000160 | 0 |

Every separation indicator is preserved. The maximum endpoint change is 0.000233 point
(bounded above by the paper's 0.00024); the maximum single-replicate change is 0.019166 point.
Consequently, the less-than-0.001 point-estimate statement must not be applied to every
weighted replicate. This check covers the primary empirical-weight arms and the five fresh
attack-only streams; it does not cover all alternative-weight cells or external datasets.
Selectors: `results.<run>.tie_check.max_replicate_eer_difference`,
`.max_pair_endpoint_difference`, `.changed_indicators` and `.summary`.
The diagnostic reports exact original-summary reproduction for all four primary arms and
zero estimator-validation error (`primary_validation_max_error`); input hashes match S4a.

### S4e. Delete-one-group influence (historical ordering)

This subsection retains the original producer's score-tie convention and result
for provenance. FIX5's Table 2 uses the explicit trial-ID ordering in S4f; the
Conformer–SSL-AASIST top-five share changes from 75.73% to 75.74%.

VCC2SM3 contains 315 evaluation trials, all bona fide from VCC2018 and none spoof; independent protocol parsing and its input hash are recorded in `evidence/revision-mc-verification.json`.

Delete each of the 93 speaker groups and each of the 110 attack groups in turn, removing
all of its trials and refitting all eight EERs. For pair p and grouping G, define
`d_g = Delta_{-g} - mean_g Delta_{-g}`. A group's concentration share is
`d_g^2 / sum_g d_g^2`. The sum of squares uses the mean of the delete-one estimates, not
the full-data estimate; deletion gaps below remain on the original signed EER-point scale.
The associated jackknife variance is `(G-1)/G * sum_g d_g^2`.

| Pair | Largest speaker contributor | Share of squared deviations | Top five share | Full gap | Gap after deleting largest contributor |
|---|---|---:|---:|---:|---:|
| XLSR-Mamba vs XLSR-Conformer | VCC2SM3 | 77.09% | 90.03% | -0.389234 | -0.129429 |
| XLS-R+SLS vs XLSR-Conformer | VCC2SM3 | 55.85% | 78.47% | -0.357105 | -0.130970 |
| XLSR-Conformer vs SSL-AASIST | VCC2SF2 | 23.85% | 75.73% | -0.578369 | -0.441137 |

VCC2SM3 contributes 77.09% for Mamba–Conformer and 55.85% for SLS–Conformer. Its deletion
moves the former from -0.389 to -0.129 points at manuscript precision. The measured
concentration concerns observed groups and is not a population effective sample size.
No group is excluded from the principal analysis. The same procedure is applied to attacks;
all 28 pairs for both factors, their largest contributors and jackknife variances are at
`results.speaker.pairs` and `results.attack.pairs` in `evidence/influence.json`.
Fields are `jackknife_variance`, `top_one_ss_share`, `top_five_ss_share`, and
`top_groups` (including `speaker_label` for speakers, group `index`, `ss_share`, and `deletion_gap`).
The 203 group refits agree with `exp/results_floor.json` components to that file's
four-decimal precision. Input and driver hashes accompany the output; this analysis uses
the same fixed scores as S4a.

### S4f. FIX5 deterministic delete-one ordering

For the delete-one analysis, equal scores are ordered by trial ID (ascending
lexicographic order). The ordered-position EER and squared, mean-centered
speaker-deletion definition in S4e are otherwise unchanged. The public producer
`code/influence_trial_id.py` and result `evidence/influence-trial-id.json` supersede
S4e's three printed speaker rows for the current manuscript. The producer checks
all nine public input hashes and refits the four SSL systems after each of the
93 speaker deletions. It uses stable score sorting on ascending trial IDs.

| Pair | Largest speaker contributor | Share of squared deviations | Top five share | Full gap | Gap after deleting largest contributor |
|---|---|---:|---:|---:|---:|
| **XLSR-Mamba vs XLSR-Conformer** | VCC2SM3 | 77.09% | 90.03% | -0.389234 | -0.129429 |
| **XLS-R+SLS vs XLSR-Conformer** | VCC2SM3 | 55.85% | 78.47% | -0.357105 | -0.130970 |
| **XLSR-Conformer vs SSL-AASIST** | VCC2SF2 | 23.85% | 75.74% | -0.578369 | -0.441137 |

The resampling-band tie check in S4d remains a separate check. No bootstrap
replicates were regenerated for this deletion-order repair.


## S5. Fixed alternative weighting rules

Let each class have total mass one. For a named hierarchy, mass is split equally among
observed children at each successive level; trials split the terminal group mass equally.
No observed trial receives zero weight.

| Component | Operational definition |
|---|---|
| B0 | equal mass per bona-fide trial (empirical trial weighting) |
| B1 | 1/3 per source, then equal per trial within source |
| B2 | 1/3 per source, then equal per observed speaker, then equal per trial |
| S0 | equal mass per spoof trial (empirical trial weighting) |
| S1 | 1/5 per spoof stratum, then equal per trial within stratum |
| S2 | 1/5 per stratum, then equal per observed speaker×attack cell, then equal per trial |
| S3 | 1/5 per stratum, then equal per attack family, attack and observed speaker in that order, then equal per trial |

The twelve rules are `B0×S0`, `B0×S1`, `B0×S2`, `B0×S3`, `B1×S0`, `B1×S1`,
`B1×S2`, `B1×S3`, `B2×S0`, `B2×S1`, `B2×S2` and `B2×S3`. They were generated
from metadata without loading scores. For nonempirical endpoint `w1`, the fixed path is
`w(lambda)=(1-lambda)w0+lambda*w1`, with no further normalization because both endpoints
already have unit class mass. Its distance is

`max_c 0.5 * sum_i |w_c(i)-w0_c(i)|`.

Under at least one of the 12 endpoints, six of the 12 within-cohort pairs reverse their
point ordering (five within-baseline, one within-SSL) and none of the 16 cross-cohort pairs
does. One of the eleven paths from `B0×S0` reverses before distance 0.10.

**Bands under each rule (EXP-116, computed after the point results).** After inspecting the
weighting rules' point results, we recomputed both perturbation laws with each rule's weight
vector as the base weight of every trial (`B=5000` per cell, seeds `20260909+100k+l`, same
threshold refitting and max-t construction as S2). The plan, frozen before computation and
after the point orderings were known, fixed one reading: all 16 cross-cohort pairs separated
in all 24 rule×law cells, or the manuscript reports point-order stability only.
Result: 384/384 cross-cohort indicators. The cross-cohort band endpoint closest to zero is -12.79 points
(SSL-AASIST vs RawNet2, rule B0×S1, PW law). The `B0×S0` cells reproduce the manuscript's
26/28 and 18/28.

| Rule | Trial q.95 | Trial cross | Trial within-SSL | Trial within-baseline | PW q.95 | PW cross | PW within-SSL | PW within-baseline |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B0xS0 | 2.938 | 16/16 | 5/6 | 5/6 | 2.957 | 16/16 | 2/6 | 0/6 |
| B0xS1 | 2.904 | 16/16 | 6/6 | 5/6 | 2.976 | 16/16 | 2/6 | 0/6 |
| B0xS2 | 2.957 | 16/16 | 5/6 | 5/6 | 2.965 | 16/16 | 2/6 | 0/6 |
| B0xS3 | 2.919 | 16/16 | 5/6 | 3/6 | 2.955 | 16/16 | 2/6 | 0/6 |
| B1xS0 | 2.975 | 16/16 | 5/6 | 3/6 | 2.969 | 16/16 | 2/6 | 0/6 |
| B1xS1 | 2.944 | 16/16 | 6/6 | 3/6 | 2.988 | 16/16 | 2/6 | 0/6 |
| B1xS2 | 2.917 | 16/16 | 6/6 | 3/6 | 2.962 | 16/16 | 2/6 | 0/6 |
| B1xS3 | 3.005 | 16/16 | 5/6 | 6/6 | 2.965 | 16/16 | 2/6 | 0/6 |
| B2xS0 | 2.986 | 16/16 | 5/6 | 3/6 | 3.004 | 16/16 | 2/6 | 0/6 |
| B2xS1 | 2.932 | 16/16 | 6/6 | 3/6 | 2.965 | 16/16 | 2/6 | 0/6 |
| B2xS2 | 2.924 | 16/16 | 5/6 | 3/6 | 2.996 | 16/16 | 2/6 | 0/6 |
| B2xS3 | 2.985 | 16/16 | 5/6 | 6/6 | 2.979 | 16/16 | 2/6 | 0/6 |

The later constructive search is explicitly post-result. It searches interior masses on
the 3-group bona-fide and 5-group spoof simplexes. Its two frozen search backends are:

- scrambled Sobol, dimension 8, seed `20260829`, `2^18` endpoints, retaining the best 32
  sign-changing directions per pair and objective;
- constrained differential evolution over six free logits, seed `20260828`, bounds
  `[-16,16]`, population multiplier 12, 240 generations and tolerance `1e-8`, followed by
  SLSQP (`maxiter=1000`, `ftol=1e-12`).

For each retained direction, it scans lambda in 0.01 increments, bisects the first sign
change for 60 steps, rounds upward to a 0.0001 grid, and tests at most 100 additional grid
points. Acceptance requires the reversing sign under integer group-count, direct
per-trial, and distinct-score-boundary EER computations. The independent verifier
reconstructed all 729 accepted direction endpoints. It found verified constructive bounds
for all 12 within-cohort pairs, including five at distance at most 0.10. For XLSR-Mamba minus XLS-R+SLS, the
best verified witness has distance `0.010218020325485883`, masses

`q_bona=(0.5437879658, 0.2440021693, 0.2122098648)`

and

`q_spoof=(0.1326209970, 0.2343431879, 0.1166358631, 0.2225363181, 0.2938636338)`.

At manuscript rounding, maximum classwise total variation is .010218, with
bona-fide masses (.544,.244,.212) and spoof-stratum masses (.133,.234,.117,.223,.294),
in the order above and rounded: bona-fide sources are ASVspoof, VCC2018, VCC2020;
spoof strata are ASVspoof, VCC2018 HUB, VCC2018 SPO, VCC2020 Task 1, VCC2020 Task 2.
The reversing sign holds under the original position sweep and at distinct-score boundaries.

It changes the signed delta from `-0.0321296825` to `+0.0006988360` points. This is a
verified constructive upper bound, not a minimum, and is too small to imply practical superiority.
The search found no cross-cohort reversal, which is not a proof that none exists; failure to find
a witness is not an absence result.

## S6. Composition-preserving PW control (withdrawn from the manuscript)

FIX5 withdraws this control from the manuscript and from the public regeneration
promise. The exact producer and complete joint draw law are unavailable in this
release; the embedded results permit arithmetic checks, not independent
regeneration. S6 and the archived paragraph below are historical records, not
support for a current claim that source-composition movement has been ruled out.

The constrained PW arm resamples speakers and attacks within each bona-fide source and each
of the five spoof strata, redraws a replicate only when a class loses all support in a
stratum (7 rejected attempts out of 1,007 for VCC2018, all for lost spoof support; no
rejections elsewhere), and then rescales each class-specific source or stratum mass exactly
to its observed value. It uses 1,000 retained draws and seed `20260824`; the primary arms
use 5,000 draws and seed `2026081604`. Its endpoints reproduce
the unconstrained PW arm: 0/6 organizer-baseline and 18/28 all-pair separations. The maximum
measured classwise stratum-mass displacement was `5.44e-13`. A total-only normalization
control used the same diagnostic, moved bona-fide source mass by median `0.0534447`, and
separated 16/28 pairs. Thus the near-zero displacement is measured by a diagnostic that can
and does return a nonzero value; it is not accepted merely because restoration was coded.

The arm (1,000 draws, seed 20260824) was designed after the main result. This computation followed a failed original arm and is a robustness control, not a
prospective causal decomposition. Result of record: `results_v2.json`; clean producer
commit: `ebf47f5649ea22a286f75eb9ad79a45385b6f5c0`.

## S7. Coverage simulation specification

For system `k` and bona-fide trial `i`, the imposed score model is

`Y_bik = u_b,spk(i),k + e_bik`.

For spoof trial `i`, it is

`Y_sik = mu_sk + u_s,spk(i),k + v_attack(i),k + w_cell(i),k + e_sik`.

Each pair of system effects is bivariate with the fitted correlation for that component.
Random effects are Gaussian or standardized Student-t(5); residuals are Gaussian. The
calibration vectors below are `(system 0, system 1)`. The organizer regime fits
RawNet2/LFCC-LCNN; the low-EER regime fits XLSR-Mamba/XLS-R+SLS.

| Regime | Component | SD vector | Correlation |
|---|---|---|---:|
| organizer | bona speaker | (3.849218, 6.039629) | 0.916657 |
| organizer | bona residual | (2.501772, 5.686650) | 0.284407 |
| organizer | spoof speaker | (0.322602, 2.460239) | 0.183290 |
| organizer | spoof attack | (1.445018, 7.521309) | 0.484480 |
| organizer | spoof residual | (2.348117, 6.593308) | 0.211285 |
| low-EER | bona speaker | (1.661044, 1.571879) | 0.952834 |
| low-EER | bona residual | (1.789746, 2.406410) | 0.864253 |
| low-EER | spoof speaker | (0.061790, 0.287587) | 0.745670 |
| low-EER | spoof attack | (0.152316, 1.041165) | 0.825219 |
| low-EER | spoof residual | (0.335433, 1.094528) | 0.670900 |

The base EER is 22.383342% in the organizer regime and 3% in the low-EER regime. For
interaction share `h`, speaker and attack SDs are multiplied by `sqrt(1-h)`, interaction SD
is `sqrt(h*(speaker_SD^2+attack_SD^2))`, and its cross-system correlation is the mean of the
speaker and attack correlations. Spoof offsets are recalibrated to target deltas 0, 0.5 or
2 points using analytic Gaussian quantiles or four million fixed-seed Student-t draws, then
checked on one million independent draws. The 48 cells are

`2 regimes × 4 h values {0,.25,.50,.75} × 2 tails {Gaussian,t5} × 3 deltas {0,.5,2}`.

Each cell uses `R=1000`, base seed `20260824`; each PW-percentile interval uses `B=500`.
For delete-one speaker, attack and observed-cell refits, let their jackknife variances be
`V_s`, `V_a`, and `V_sa`. The raw exact-cell inclusion-exclusion interval uses
`V_raw=V_s+V_a-V_sa`; the component-floor version uses
`V_floor=max(V_raw,V_s,V_a)`. Both use `1.9599639845*sqrt(V)`. The third method is the
speaker×attack PW percentile interval.

Organizer-regime coverage ranges are `.928-.957` for the two jackknife versions and
`.946-.968` for PW percentile. Low-EER minima in that same order are `.845`, `.845`, and
`.855`. Coverage fell below .90 in 16/24 low-EER cells for each jackknife interval and 11/24 for PW percentile; all three failed in the same 11 cells. The fitted DGP has not been shown
adequate for 21DF. This simulation evaluates pointwise candidate intervals under those imposed
models, not the all-pair bands in the paper; it does not establish that either model describes 21DF.

An additional trace-retaining `R=200` organizer-regime run produced the following separate
Wilson intervals; it is not pooled with the 48-cell grid:

| Procedure | Covered/R | Coverage | 95% Wilson interval |
|---|---:|---:|---:|
| Trial-IID percentile | 37/200 | 18.5% | [13.73%, 24.46%] |
| Speaker×attack PW percentile | 196/200 | 98.0% | [94.97%, 99.22%] |
| Two-way jackknife | 195/200 | 97.5% | [94.28%, 98.93%] |
| Wild-cluster diagnostic | 195/200 | 97.5% | [94.28%, 98.93%] |

## S8. External checks and provenance identifiers

### SpoofCeleb

This is an off-domain sensitivity check, not a comparison of competitive SpoofCeleb systems.
After observing this result, separate speaker-only and attack-only bootstraps separated 5/6
and 3/6; attack-only matched the PW indicator vector. Their result is embedded at
`audit/audit.json` → `spoofceleb_factor_decomposition.result` (the full six-pair family).
The prospective design and analyzer were committed as `c2efa63` (2026-08-29 15:38:58 -03)
in the authors' working repository while official repository access was pending and no
SpoofCeleb audio, scores or metrics were present locally. The plan is released here as
`plans/EXP-114-spoofceleb.PREREG.md`, SHA-256
`3300801277eb74c1f17110163d9a1b415ec7d0e993cb105f90e457f5f6aba994`, with its freeze
manifest (SHA-256 `9a2f34ab152e9e96be090bff1a4e328122eb63b3c20d3c1be8cd5e0082ccac73`).
The commit timestamp is the authors' own record; it is not an independently attested
timestamp, and the paper claims no more than that. The first access event was the later successful authenticated download.
The acquired release revision was `9b66238412b72117515aaf0ec41b77f7845b89fe`; all 27
archive parts matched their official LFS hashes. Acquisition and manifest construction were
committed as `938510f` before scoring.

The archived plan did not bind the scoring code or full runtime surface. A later re-scoring from freshly cloned, commit-pinned detector repositories is reproducibility evidence only, not a second confirmation. The first three score files were byte-identical (AASIST, SLS and SSL-AASIST). XLSR-Mamba had
25,866 changed float32 scores, maximum absolute difference
`1.430511474609375e-6` (conservative ceiling 1.44e-6), unchanged order at the EER threshold, and unchanged EERs and all six
separation indicators: every EER and separation indicator was unchanged. The SpoofCeleb EERs are 57.93%, 24.51%, 26.72%, and 27.58% for AASIST, SLS, SSL-AASIST, and Mamba. Joint resampling retains only the three comparisons with AASIST. The trial arm of this
check is the pooled (unstratified) trial bootstrap fixed by the archived plan, not the
class-stratified law of S2. A class-stratified recomputation on the same manifest and score
tables (EXP-118, B=5000, seed 20260909) also separates 6/6 with the same indicators; band
endpoints move by at most 0.02 points (`exp118/RESULTS.json`).

### ASVspoof 5

The four-detector check uses all 680,774 Track 1 trials and EER only to transfer the paper's DeltaEER resampling
contrast; it is not comparative benchmark reporting. Its resampling law draws 367 target-speaker
multiplicities, 370 bona-fide-only speaker multiplicities and 16 attack multiplicities as three
independent multinomial samples; a target count applies to that speaker's bona-fide and spoof
rows, a bona-fide-only count to its bona-fide rows, and spoof weights multiply target-speaker
and attack counts. The two criteria were frozen in `plans/EXP-106-asv5.AMENDMENT-5.md`
(2026-08-16 15:10 -03, SHA-256
`6fe9b97570812955366f5ca1cfcc3fa244e2a3d2f579f8d01e2ba260d9aff854`) before scoring completed.
Trial resampling separates 6/6 pairs and the role-stratified law 5/6 (SSL-AASIST vs XLS-R+SLS
is the pair that ceases to separate). ASVspoof 5's primary Track 1 metric is
minDCF. It is not a system-performance replication or population claim.
The ASVspoof 5 SSL-AASIST and AASIST score files lack their originating run logs.
Its two declared criteria were: at least one trial-bootstrap separation disappears
under role-stratified speaker×attack resampling, and the median simultaneous-band width
ratio is at least 2. Both passed; the observed median ratio was 27.2676 (27.27 at paper precision).

### Artifact paths and content bindings

The preceding submission's artifact version was `m1-impact-20260916-v1`, in
[`rvirgilli/asvspoof2021-df-clustered-uncertainty`](https://github.com/rvirgilli/asvspoof2021-df-clustered-uncertainty/tree/m1-impact-20260916-v1).
That historical version added the three `evidence/` files and S4b–S4e. The revised manuscript cites a successor commit containing the additional Monte Carlo checks below. The prior
release remains at commit `a171aad9bd949fdc92c67344c51153f1c69217dd`.
Paths below are relative to the root of that release, not to `paper/`.
`MANIFEST.json` supplies byte counts and SHA-256 digests for the released files.

- Complete 21DF bands: `derived/results_matched_iid.json`. The bare filename in S2
  identifies this same public file; use its stated pair and field selectors.
- Point EERs: `derived/point_eers.json` (two-column extract). The legacy member
  `derived/results_selection.json` remains in the tree for provenance only; its rank and
  "certified" fields belong to a withdrawn earlier analysis, are outside the submitted
  claims and carry no certification or confidence-coverage meaning. Current procedure
  bands are in S4 and `derived/results_matched_iid.json`.
- Source deletions: `derived/results_source.json`, key `leave_one_corpus_out`.
- Weight rules and paths: `derived/results_composition.json`.
- Constructive search: `derived/secondary_v2_results.json`, SHA-256 of the **public file**
  `6ed59cb2dba15b73f05189b95c3ecc0753fd6c5b4669c887224344ab57b6d627`.
  This is the file bound by `MANIFEST.json` and the `results_sha256` field of
  `derived/secondary_v2_verification.json` (verification-file SHA-256
  `6e8dc6f42dd5afa45816b8d39ae8307b5e4beaa11b91017c0249047fff0ec369`).
  The verifier is `code/exp108/verify_secondary_v2.py` (SHA-256
  `73bb29895dd831df8075f691f5fad8f520bd31ab86368f7cb5ad9de31f449307`). The S5 witness is at
  `pairs["XLSR-Mamba vs XLS-R+SLS"].objectives.r_TV.best_overall.witness` in the public result.
  The **archived original** is the authors' working-repository file
  `experiments/EXP-108-m1-composition-robustness/secondary_v2_results.json`, SHA-256
  `b12a8784c3fcb0bc02596d375aa16a93fed3661ec5c4d3badac4ea3b8b029616`, recorded separately at
  `audit/audit.json` → `composition_sensitivity.artifact_sha256["secondary_v2_results.json"]`.
  That original is recoverable in the author archive and was hashed for this repair, but
  is not a separately downloadable member of the public release: the public result adapts
  `preoutput_contract` for the release layout. The selected witness is identical in both
  files. The original digest cannot authenticate the different public bytes.
- Composition-preserving arm: `audit/audit.json` →
  `composition_fixed_sampling_control.result`. The same object contains `run_receipt`,
  `archival_closure`, `portable_verification`, `independent_reproduction`, and
  `artifact_sha256` for the original members, including `results_v2.json` named in S6.
- Bands under each weighting rule: `exp116/RESULTS.json`, SHA-256
  `d0bbafbc3a505dcf99a9d0ff683d6651279fba098df58a3549b9b3ec0ba18cdd`.
- SpoofCeleb class-stratified trial arm: `exp118/RESULTS.json`, SHA-256
  `8e55047790c3472cbf96c3309f0d62302f3348639ebe6728f1ff2bc24e86541a`.
- Coverage grid: `derived/results_coverage_interaction_recalibrated.json` and
  `derived/results_exp105_verified.json`.
- Trace-retaining coverage run: `audit/audit.json` → `coverage_witnessed_replacement.result`.
  That object also contains `run_receipt`, `closure`, `provenance_addendum`,
  `independent_verification`, and `artifact_sha256` for the original members, including
  `results-v2.json` and `trace-v2.jsonl`.
- SpoofCeleb provenance package: `audit/audit.json` →
  `spoofceleb_sampling_unit_confirmation.provenance_rerun_result`, with sibling
  `provenance_rerun_comparison`, `provenance_rerun_receipt`, `mamba_score_comparison`,
  `independent_reproduction`, and `artifact_sha256`. The original `RESULTS.json` is bound at
  `spoofceleb_sampling_unit_confirmation.artifact_sha256["RESULTS.json"]`; it is not a
  standalone public file or a sibling `result` payload. Use the released rerun result and
  comparison records to inspect the reproducibility evidence and original/rerun differences.
- SpoofCeleb analysis plan: `plans/EXP-114-spoofceleb.PREREG.md` with
  `plans/EXP-114-spoofceleb.FREEZE.sha256`; ASVspoof 5 criteria:
  `plans/EXP-106-asv5.AMENDMENT-5.md`. Their SHA-256 values in the unchanged prose above
  were recomputed from the released files for this repair.

- Primary one-factor bands: `evidence/ABLATION-RESULTS.json`, `arms.<law>.summary.pairs` (S4a).
- Repeat seeds, paired mean/sign, covariance and ties: `evidence/diagnostics.json`, `results` (S4b–S4d).
- Group deletion: `evidence/influence.json`, `results.speaker.pairs` and `results.attack.pairs` (S4e).
- Arena: `derived/results_arena.json`, `schemes.iid` and `schemes.clustered`; the median ratio of PW to trial bootstrap standard deviations over the 55 pairs is 8.45 (not a band-width ratio).

The three embedded packages replace the former public-facing `experiments/EXP-111-…`,
`experiments/EXP-112-…`, and `experiments/EXP-114-…` locators. Those paths do not exist in
the public tree. Their original standalone byte serializations cannot be recovered from
that tree: the release distributes embedded records and original-member hashes instead.
Re-serializing a selected JSON object does not reproduce or verify the original file hash.
The original files remain available in the author archive and their `artifact_sha256`
bindings were checked for this repair; independent public verification uses the container
`audit/audit.json`, SHA-256
`33741f645b0d6cdb492e31add6ca4feffa4ea540a0d65a7ceaa0d918e3b49d02`, and the selectors above.

From the repository root, compare `sha256sum PATH` with the matching entry in
`MANIFEST.json` (also compare the byte count); use the explicitly printed public digest
for the constructive result. `artifact_sha256` inside an audit package refers to its
original members, not to the containing JSON file. These checks authenticate bytes against
the records; they do not supply independent timing attestation or rerun the experiments.

The public release excludes upstream-licensed score/audio inputs. Its manifest binds every
released code, aggregate, paper and provenance member; the data README gives upstream
retrieval and hash instructions.

## S9. Retained scope of secondary checks

Passing both checks does not guarantee an ordering under every possible reweighting or select a deployment ranking.

Speaker-only matches the primary joint indicators; attack-only does so on SpoofCeleb.

The source-deletion construction preserves all 16 cross-cohort separations without a coverage guarantee.

The reversing sign also holds at distinct-score boundaries.

The factor agreement concerns these particular score collections and different rosters; it does not identify a causal factor or a corpus-general variance pattern. Source-deletion methods and endpoints remain in S2, and the constructive search remains in S5; neither is needed to interpret the revised submission.


## S10. Historical manuscript record retained by the concentration rewrite

The following superseded manuscript excerpts preserve prior semantic obligations and
secondary results. They are not premises of the rewritten PDF; its table numbers and
artifact locator supersede those in these historical excerpts.

In a separate simulation using the 21DF incidence and Gaussian speaker/attack effects fitted to RawNet2/LFCC-LCNN scores, nominal 95\% pointwise percentile intervals covered a true 0.5-point EER difference in 37/200 datasets (18.5\%) under trial resampling and 196/200 (98.0\%) under speaker$\times$attack resampling, using 300 bootstrap draws per dataset.

Recomputing both bootstraps with each rule's weights as base weights (computed after the primary results, 5,000 draws per rule and bootstrap) separates all 16 cross-cohort pairs in all 24 rule$\times$law cells; the closest band endpoint to zero is $-12.79$ points.

In a separate 24-cell low-EER grid varying interaction strength, effect tails and the true gap, speaker$\times$attack percentile coverage fell below 90\% in 11 cells, reaching 85.5\% (1,000 datasets per cell; 500 bootstrap draws).

For comparisons intended to withstand changes in the weights of observed speakers and attacks, report the point EER difference and both trial and group-resampling bands for the same comparison family.

One-factor perturbations and group deletions locate sensitivity within the observed 21DF score collection; a single-source SpoofCeleb check tests whether between-source reweighting is necessary.

For XLSR-Mamba versus XLSR-Conformer, this occurs despite pairing removing about 75\% of summed marginal variance; the paired standard deviation increases 5.2-fold.

These models have not been validated for 21DF, and these pointwise intervals differ from our all-pair bands; neither result establishes coverage for those bands.

If only the trial band excludes zero, report that separation depends on the resampling law; do not infer equality or population significance from the group band.

On the observed ASVspoof~2021~DF scores, changing the resampling unit changes paired EER separation even after substantial variation cancels between detectors.

For each other primary arm, 1,000 resamples of its saved 5,000 complete detector-output rows, recomputing all bands, leave every indicator unchanged.

Comparing detectors on the same trials cancels shared variation, but does it remove sensitivity to which speakers and attacks receive weight?

The matched trial/PW comparison uses 5,000 replicates and seed 2026081604; seeds of the other analyses accompany their released outputs.

Mamba--Conformer illustrates this with about 75\% covariance cancellation and a 5.2-fold increase in paired standard deviation.

Bottom: primary separation counts, retaining the 28-pair correction; every arm retains 16/16 SSL-versus-baseline separations.

Top: primary 21DF EER (\%), with 14,869 bona-fide and 519,059 spoof trials and weights normalized within class.

A separate eleven-detector roster on the same corpus changes from 52 of 55 to 38 of 55 bands excluding zero.

All sixteen SSL-versus-baseline comparisons survive the tested resampling laws and fixed weighting rules.

This locates influence in an observed genuine-speech group; it does not identify a causal speaker effect.

The sixteen SSL-versus-baseline contrasts survive the tested resampling laws and fixed weighting rules.

Their $3\times4$ crossing gives 12 positive, class-normalized rules fixed without inspecting scores.

Middle: paired bands in percentage points; primary 21DF uses all 28 pairs, Arena all 55 pairs.

This assesses Monte Carlo noise conditional on saved draws, not independent-seed stability.

WHEN RESAMPLING CHANGES PAIRED DETECTOR COMPARISONS ON ASVSPOOF 2021 DF

Primary Monte Carlo checks are described in the text.

### Arena example, retained numerical provenance

\textbf{Arena comparison.} On the eleven complete Speech DF Arena score files for the same 533,928 trials, trial and PW bands separate 52/55 and 38/55 pairs. For HuBERT-ECAPA versus WavLM-ECAPA, the $-2.153$-point gap has bands $[-2.761,-1.544]$ and $[-5.241,0.936]$. Its joint pointwise percentile interval remains below zero, [$-4.252$, $-0.277$]; the loss is specifically under the 55-pair simultaneous band.


The SSL pair is Mamba--SLS (gap -0.032 points), already unseparated under trial resampling.


Fixed rules reverse 5/6 organizer-baseline, 1/6 within-SSL and 0/16 cross-cohort point orderings.

## S14. FIX5 archived composition paragraph

The following is the withdrawn paragraph from submission `36bc6c0`. It preserves
its exact text and deletion-tested obligations as history. Its final inference
is not asserted by the current paper; the incomplete producer/draw law prevents
public regeneration. No composition-control result has been rerun for FIX5.

```latex
\textbf{Composition-preserving control.} A post-result PW control resamples speakers and attacks within each bona-fide source or spoof stratum, rejects draws with no class support in any required stratum, and rescales the three bona-fide source masses and five spoof-stratum masses to their observed values. This control uses seed 20260824. The bona-fide sources are ASVspoof, VCC2018 and VCC2020; the spoof strata split VCC2018 into HUB/SPO and VCC2020 into Task~1/Task~2. VCC2018 required 1,007 attempts, with seven rejected for lost spoof support; no other stratum required rejections. Across 1,000 retained draws it separates 18/28 pairs and 0/6 organizer pairs. For Mamba--Conformer, the control band is $[-1.280,0.501]$, beside the primary joint band $[-1.348,0.570]$. Thus movement of these eight masses is not required for the loss of separation; this does not remove influence from groups within a source or stratum.
```
