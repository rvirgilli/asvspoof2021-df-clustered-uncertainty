# Supplementary methods and complete numerical results

Version: `m1-field-native-r2-20260830`

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
speaker×attack cells. “Leave one source out” always means deleting ASVspoof, VCC2018 or
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
receives only its speaker multiplicity. Both use `B=5000`, seed `20260817`, shared system
weights and all 28 contrasts. For procedure `h`, with bootstrap scale `s[p,h]`, its max-t
critical value is the empirical 0.95 quantile of

`max_p |Delta[p,h,b] - mean_b Delta[p,h,b]| / s[p,h]`.

The reported band is `Delta_hat[p] +/- q[.95,h] s[p,h]`.

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

The 12 endpoints reverse 6/12 within-cohort pair orderings and 0/16 cross-cohort pair
orderings. One of the eleven paths from `B0×S0` reverses before distance 0.10.

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

The constrained PW arm resamples speakers and attacks within each of the five spoof strata,
redrawing only when a class loses all support, and then restores each class-specific source
or stratum mass exactly. It uses 1,000 draws and seed `20260824`. Its endpoints reproduce
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

The prospective design and analyzer were committed as `c2efa63` on 29 August 2026 while
official repository access was pending and no SpoofCeleb audio, scores or metrics were
present locally. The first access event was the later successful authenticated download.
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
contrast; it is not comparative benchmark reporting. ASVspoof 5's primary Track 1 metric is
minDCF. Its two declared criteria were: at least one trial-bootstrap separation disappears
under role-stratified speaker×attack resampling, and the median simultaneous-band width
ratio is at least 2. Both passed; the observed median ratio was 27.2676.

### Artifact paths and content bindings

- Complete 21DF bands: `derived/results_matched_iid.json`.
- Point EERs: `derived/results_selection.json`.
- Weight rules and paths: `derived/results_composition.json`.
- Constructive search: `derived/secondary_v2_results.json`, independently verified result SHA-256
  `b12a8784c3fcb0bc02596d375aa16a93fed3661ec5c4d3badac4ea3b8b029616`.
- Coverage grid: `derived/results_coverage_interaction_recalibrated.json` and
  `derived/results_exp105_verified.json`.
- The composition-preserving arm, trace-retaining coverage run, and SpoofCeleb provenance
  package are embedded under `composition_fixed_sampling_control`,
  `coverage_witnessed_replacement`, and `spoofceleb_sampling_unit_confirmation` in
  `audit/audit.json`; that file binds their original member hashes.

The public release excludes upstream-licensed score/audio inputs. Its manifest binds every
released code, aggregate, paper and provenance member; the data README gives upstream
retrieval and hash instructions.
