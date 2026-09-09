# Supplementary methods and complete numerical results

Version: repository tag `icassp2027-submission`

This document supplies the operational definitions and complete numerical tables cited by
the ICASSP 2027 manuscript. The paper's inferential object is fixed-score procedure
sensitivity. None of the bands below is claimed to be a population confidence interval.

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

The trial bootstrap resamples trials independently within class. The speaker×attack
product-weight bootstrap independently samples 93 speaker multiplicities and 110 attack
multiplicities. A spoof trial's weight is their product; a bona-fide trial has no attack and
receives only its speaker multiplicity. Both use `B=5000`, seed `2026081604`, shared system
weights and all 28 contrasts. For procedure `h`, with bootstrap scale `s[p,h]`, its max-t
critical value is the empirical 0.95 quantile of

`max_p |Delta[p,h,b] - mean_b Delta[p,h,b]| / s[p,h]`.

The reported band is `Delta_hat[p] +/- q[.95,h] s[p,h]`.

**Source-deletion construction.** Leave-one-source-out refits use a third construction: with
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

The secondary additive marginal-jackknife Gaussian sensitivity analysis uses
`Sigma_plus = Sigma_speaker + Sigma_attack`. It projects the symmetric matrix to positive
semidefinite form by clipping negative eigenvalues at zero, draws 200,000 vectors
`Z ~ N_8(0,Sigma_plus)` with seed `20260824`, forms and standardizes all 28 contrasts, and
uses `sqrt(max(contrast variance,1e-18))` for a zero-scale guard. Its max-t critical value is
`2.878444888` (`2.878` to three decimals); it separates 18/28 pairs and 0/6
organizer-baseline pairs. For RawNet2 minus CQCC-GMM its band is `[-8.76,2.40]`. Because the cell
overlap is not subtracted, this is a deliberately variance-inflating sensitivity analysis,
not an exact multiway estimator or a coverage guarantee.

## S3. Complete 21DF point results

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

**Bands under each rule (EXP-116, post-result verification).** After the 2026-09-08
exact-PDF audit noted that the manuscript asserted separation stability under the rules
without having computed bands, both perturbation laws were rerun with each rule's weight
vector as the base weight of every trial (`B=5000` per cell, seeds `20260909+100k+l`, same
threshold refitting and max-t construction as S2). The plan was written after the rules and
their point orderings were known and is disclosed as such. Registered reading: the strong
sentence is allowed only if all 16 cross-cohort pairs are separated in all 24 cells.
Result: 384/384. The cross-cohort band endpoint closest to zero is -12.79 points
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

It changes the signed delta from `-0.0321296825` to `+0.0006988360` points. This is a
verified constructive upper bound, not a minimum. Failure to find a cross-cohort witness
is not an absence result.

## S6. Composition-preserving PW control

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

This computation followed a failed original arm and is a robustness control, not a
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
`.855`; all three are below `.90` in the same 11/24 cells. The fitted DGP has not been shown
adequate for 21DF, so these are conditional simulation results only.

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

The original plan did not bind the assessment executable and full runtime surface. The
post-result clean-source rerun is therefore reproducibility evidence, not a second
confirmation. It reproduced AASIST, SLS and SSL-AASIST scores byte-for-byte. XLSR-Mamba had
25,866 changed float32 scores, maximum absolute difference
`1.430511474609375e-6`, unchanged order at the EER threshold, and unchanged EERs and all six
separation indicators. The detector point EERs are 57.93%, 24.51%, 26.72% and 27.58%.

### ASVspoof 5

The four-detector Track 1 check uses EER only to transfer the paper's DeltaEER resampling
contrast; it is not comparative benchmark reporting. Its resampling law draws 367 target-speaker
multiplicities, 370 bona-fide-only speaker multiplicities and 16 attack multiplicities as three
independent multinomial samples; a target count applies to that speaker's bona-fide and spoof
rows, a bona-fide-only count to its bona-fide rows, and spoof weights multiply target-speaker
and attack counts. The two criteria were frozen in `plans/EXP-106-asv5.AMENDMENT-5.md`
(2026-08-16 15:10 -03, SHA-256
`6fe9b97570812955366f5ca1cfcc3fa244e2a3d2f579f8d01e2ba260d9aff854`) before scoring completed.
Trial resampling separates 6/6 pairs and the role-stratified law 5/6 (SSL-AASIST vs XLS-R+SLS
is the pair that ceases to separate). ASVspoof 5's primary Track 1 metric is
minDCF. Its two declared criteria were: at least one trial-bootstrap separation disappears
under role-stratified speaker×attack resampling, and the median simultaneous-band width
ratio is at least 2. Both passed; the observed median ratio was 27.2676.

### Artifact paths and content bindings

- Complete 21DF bands: `derived/results_matched_iid.json`.
- Point EERs: `derived/results_selection.json`.
- Source deletions: `derived/results_source.json`.
- Weight rules and paths: `derived/results_composition.json`.
- Constructive search: `derived/secondary_v2_results.json`, independently verified result SHA-256
  `b12a8784c3fcb0bc02596d375aa16a93fed3661ec5c4d3badac4ea3b8b029616`.
- Bands under each weighting rule: `exp116/RESULTS.json`, SHA-256
  `d0bbafbc3a505dcf99a9d0ff683d6651279fba098df58a3549b9b3ec0ba18cdd`.
- Coverage grid: `derived/results_coverage_interaction_recalibrated.json` and
  `derived/results_exp105_verified.json`.
- The composition-preserving arm, trace-retaining coverage run, and SpoofCeleb provenance
  package are embedded under `composition_fixed_sampling_control`,
  `coverage_witnessed_replacement`, and `spoofceleb_sampling_unit_confirmation` in
  `audit/audit.json`; that file binds their original member hashes.
- SpoofCeleb analysis plan: `plans/EXP-114-spoofceleb.PREREG.md` with
  `plans/EXP-114-spoofceleb.FREEZE.sha256`; ASVspoof 5 criteria:
  `plans/EXP-106-asv5.AMENDMENT-5.md`.

The public release excludes upstream-licensed score/audio inputs. Its manifest binds every
released code, aggregate, paper and provenance member; the data README gives upstream
retrieval and hash instructions.
