# Reconsideration implementation

The revision makes the central result assessable inside the PDF, assuming no reviewer follows an external pointer. The corpus boundary, numerical stability and limits of the reporting recommendation are explicit. No detector training, rescoring, new dataset or population-validity claim was added.

## Decisions and space

- Keep the six-pair within-SSL figure and mean/sign table: they expose the modern comparisons and the distinction between band separation and sign frequency. The complete 28-pair record stays in the artifact.

- Keep Arena as a second roster on the same corpus; print its joint pointwise interval and identify the 55-pair correction.

- Print the matched trial/PW coverage contrast beside adverse low-EER results. Omit the two 97.5% results because they introduce unnecessary jackknife/wild procedures.

- Retain SpoofCeleb solely as a single-source, off-domain control, with the full original six-pair correction; do not invert scores, retrain or claim a universal factor pattern.

- Retain the twelve fixed weighting rules and their all-cross-cohort positive control. Cut constructive-search paths and witness details, which support no retained main-text result.

- Cut the entire tie-accounting, ASVspoof 5 experiment and source-deletion paragraphs. Their complete technical record and limitations remain in the supplement; no original obligation ID is removed.

- Run and retain both conditional Monte Carlo and the predeclared fresh streams. All fresh primary indicators are unchanged, so keep recorded primary counts and print observed ranges only for attack-only. Add one fresh-stream sentence after the conditional qualification.

- Preserve acknowledgment and ethics on page four; start Discussion on page four and use an ordinary column break before Artifact. No smaller fonts, scaling or margin changes fund the revision.

- Retain the bounded reporting recommendation; neither favorable simulation nor numerical stability establishes coverage for the principal bands.

## Checker change rationale

Every changed checker hunk follows a changed sentence, relocated claim, table cell or release binding. Literal checks follow the exact revised phrases. The main matrix derives attack extrema from all six archived runs. The removed SpoofCeleb table row is checked in its replacement paragraph; all original external-result checks remain. Influence checks bind the deletion gap and independently parsed class composition; original concentration-share checks remain in the supplement. New checks bind conditional and fresh arrays, the verifier and producer, the preserved seed contracts, the Arena pointwise qualification, class counts, SD ratio and inline coverage counts. The supplement copies must agree, and S2–S8 pointers may not return to the PDF. The receipt verifier follows the new receipt. `paper/OBLIGATION-REVISION.json` records every obligation transition.

## Exact before and after text

### 1. MAJOR-2

Put the measured corpus in the title.

Before:

```tex
WHEN RESAMPLING CHANGES PAIRED AUDIO-DEEPFAKE DETECTOR COMPARISONS
```

After:

```tex
WHEN RESAMPLING CHANGES PAIRED DETECTOR COMPARISONS ON ASVSPOOF 2021 DF
```

### 2. MAJOR-2/5

Lead with the scoped pairing result and its claim boundary.

Before:

```tex
We measure the sensitivity of paired equal-error-rate (EER) differences on fixed detector scores. We call a pair separated when its all-pair sensitivity band excludes zero; these bands carry no population-coverage claim. A 2.153-point EER advantage between two Speech DF Arena detectors loses simultaneous-band separation when speakers and attacks replace trials as the resampling unit. The same change occurs for XLSR-Mamba versus XLSR-Conformer, despite substantial cancellation from system pairing. Trial-to-joint separation falls from 26/28 to 18/28 on primary ASVspoof~2021~DF; a separate four-detector SpoofCeleb roster changes from 6/6 to 3/6. Speaker-only matches the primary joint indicators; attack-only does so on SpoofCeleb. Measured sensitivity concentrates in particular observed groups, while all SSL-versus-baseline comparisons survive the tested perturbations. Paired comparisons can therefore remain sensitive to group perturbations after substantial common variation cancels.
```

After:

```tex
Comparing detectors on the same trials cancels shared variation, but does it remove sensitivity to which speakers and attacks receive weight? On fixed ASVspoof~2021~DF scores from eight detectors, we refit equal-error-rate (EER) thresholds under trial and joint speaker--attack resampling and construct simultaneous bands for all 28 EER differences. The number of bands excluding zero falls from 26 to 18. For XLSR-Mamba versus XLSR-Conformer, this occurs despite pairing removing about 75\% of summed marginal variance; the paired standard deviation increases 5.2-fold. A separate eleven-detector roster on the same corpus changes from 52 of 55 to 38 of 55 bands excluding zero. All sixteen comparisons between the four self-supervised detectors and four organizer baselines survive. These are sensitivity results for observed score collections, without population-coverage guarantees.
```

### 3. MAJOR-2/4

Remove the broad factor contrast and source-deletion detour.

Before:

```tex
One-factor perturbations and delete-one-group refits localize that sensitivity, and a single-source SpoofCeleb check gives a contrasting factor pattern. The SSL-versus-baseline boundary survives every tested resampling, fixed-weight and source-deletion check.
```

After:

```tex
One-factor perturbations and group deletions locate sensitivity within the observed 21DF score collection; a single-source SpoofCeleb check tests whether between-source reweighting is necessary. All sixteen SSL-versus-baseline comparisons survive the tested resampling laws and fixed weighting rules.
```

### 4. MAJOR-2/4/5

Conclusion follows the narrowed empirical claim.

Before:

```tex
Trial-resampling separation disappears under speaker--attack perturbations for Arena HuBERT--WavLM and primary Mamba--Conformer; for the latter, this occurs despite 75\% marginal-variance cancellation from pairing. Speaker-only matches the joint indicators on primary 21DF; attack-only does so on the separate SpoofCeleb roster, where trial-to-joint separation falls from 6/6 to 3/6. Cross-cohort separation survives the tested laws, weights and source deletions, while modern within-cohort comparisons expose concentrated group sensitivity.
```

After:

```tex
On the observed ASVspoof~2021~DF scores, changing the resampling unit changes paired EER separation even after substantial variation cancels between detectors. Mamba--Conformer illustrates this with about 75\% covariance cancellation and a 5.2-fold increase in paired standard deviation. The sixteen SSL-versus-baseline contrasts survive the tested resampling laws and fixed weighting rules. These results support reporting sensitivity to observed-group weights, without establishing population confidence or a universal factor pattern across corpora.
```

### 5. MAJOR-2

Replace unexplained concentration shares with class composition and deletion gap.

Before:

```tex
\textbf{Observed-group influence.} The observed speaker group VCC2SM3 supplies 77.09\% of Mamba--Conformer's delete-one-speaker sum of squared deviations and 55.85\% for SLS--Conformer. Deleting that group moves the Mamba--Conformer gap from $-0.389$ to $-0.129$ points, locating much of the sensitivity in this observed group (S4e).
```

After:

```tex
\textbf{Observed-group influence.} Deleting VCC2SM3, which contains 315 bona-fide VCC2018 trials and no spoof trials, changes the Mamba--Conformer gap from $-0.389$ to $-0.129$ percentage points. This locates influence in an observed genuine-speech group; it does not identify a causal speaker effect.
```

### 6. MAJOR-4

Keep the single-source control and name the losses under the six-pair correction.

Before:

```tex
\textbf{Check on single-source SpoofCeleb.} On all 91,130 evaluation trials \cite{jung25spoofceleb}, pooled trial resampling separates 6/6 pairs (a class-stratified recomputation also separates 6/6) and joint resampling 3/6. This is an off-domain sensitivity check on a different roster. The SpoofCeleb EERs are 57.93\%, 24.51\%, 26.72\%, and 27.58\% for AASIST, SLS, SSL-AASIST, and Mamba. Joint resampling retains only the three comparisons with AASIST. Every base item has one bona-fide and nine spoof renditions under one source label, so between-source mass cannot move; speaker and spoof-attack multiplicities still vary. Attack-only matches the joint indicator vector, whereas speaker-only retains 5/6. The three detectors shared with primary 21DF have 2/3 separated in every primary arm under the original 28-pair correction (S4c); the contrasting factor patterns therefore depend on the score collections. Access chronology and scoring provenance are in S8.
```

After:

```tex
\textbf{Check on single-source SpoofCeleb.} On all 91,130 SpoofCeleb evaluation trials \cite{jung25spoofceleb}, pooled trial resampling separates 6/6 pairs and joint resampling 3/6; class-stratified trial resampling also gives 6/6. EERs are 57.93\%, 24.51\%, 26.72\% and 27.58\% for AASIST, SLS, SSL-AASIST and Mamba. Under the original six-pair correction, all three comparisons among SLS, SSL-AASIST and Mamba lose separation; the three AASIST contrasts retain it. Every base item has one bona-fide and nine spoof renditions under one source label, so between-source mass cannot change. This is a control on a weakly transferred, off-domain roster, not evidence that attack effects generally dominate speaker effects on another corpus.
```

### 7. MAJOR-3

Report attack ranges where counts are read and identify recorded counts.

Before:

```tex
\caption{Top: primary 21DF point EER (\%); $n=533,928$, empirical class-normalized trial weights. Middle: paired bands (points); primary 21DF uses a 28-pair family, Arena a separate 55-pair family on the same trials. Bottom: separated pairs; primary subsets retain the 28-pair correction and all four arms retain 16/16 cross-cohort separations. SpoofCeleb uses AASIST, SLS, SSL-AASIST and Mamba, its own six-pair family and pooled trial law (stratified check: S8). *One-factor status: Method. $\dagger$Recorded-seed attack counts: four of five fresh seeds give 21/28 and 2/6 organizer separations (S4b).}
```

After:

```tex
\caption{Top: primary 21DF EER (\%), with 14,869 bona-fide and 519,059 spoof trials and weights normalized within class. Middle: paired bands in percentage points; primary 21DF uses all 28 pairs, Arena all 55 pairs. Bottom: primary separation counts, retaining the 28-pair correction; every arm retains 16/16 SSL-versus-baseline separations. Attack ranges span the original and five fresh 5,000-draw runs; other entries are recorded-run counts. Primary Monte Carlo checks are described in the text. One-factor analyses are exploratory.}
```

### 8. MAJOR-3

Make table headers self-contained.

Before:

```tex
Spk.* & Atk.*
```

After:

```tex
Speaker & Attack
```

### 9. MAJOR-3

Observed original-plus-five-stream range.

Before:

```tex
$22/28\dagger$
```

After:

```tex
21--22/28
```

### 10. MAJOR-3

Observed original-plus-five-stream range.

Before:

```tex
$3/6\dagger$
```

After:

```tex
2--3/6
```

### 11. MAJOR-4/5

Drop the peripheral factor row; retain essential control counts in prose.

Before:

```tex
SpoofCeleb & 6/6 & 5/6 & 3/6 & 3/6 \\

```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 12. MAJOR-3

Print conditional Monte Carlo assessment and its limitation.

Before:

```tex
\textbf{Primary 21DF result.} The matched all-28-pair bootstrap refits the same weighted EER in every replicate. Trial and joint bands separate 26/28 and 18/28 pairs (Table~\ref{tab:eers}); within SSL, the counts fall from 5/6 to 2/6. Mamba--Conformer remains at $-0.389$ points: its trial band is $[-0.570,-0.208]$, its joint band $[-1.348,0.570]$. Speaker-only reproduces all eight joint losses; attack-only reproduces four or five of the eight joint losses across Monte Carlo repeats (S4b). All primary within-SSL losses involve Conformer.
```

After:

```tex
\textbf{Primary 21DF result.} The matched all-28-pair bootstrap refits the same weighted EER in every replicate. Trial and joint bands separate 26/28 and 18/28 pairs (Table~\ref{tab:eers}); within SSL, the counts fall from 5/6 to 2/6. Mamba--Conformer remains at $-0.389$ points: its trial band is $[-0.570,-0.208]$, its joint band $[-1.348,0.570]$. Speaker-only reproduces all eight joint losses; attack-only reproduces four or five of the eight joint losses across Monte Carlo repeats (S4b). All primary within-SSL losses involve Conformer.

Across five fresh attack-only runs, separation counts range from 21 to 22 overall and from two to three among organizer baselines; within-SSL counts remain three. For each other primary arm, 1,000 resamples of its saved 5,000 complete detector-output rows, recomputing all bands, leave every indicator unchanged. This assesses Monte Carlo noise conditional on saved draws, not independent-seed stability.
```

### 13. MAJOR-1

State exactly what the reporting recommendation warrants.

Before:

```tex
\textbf{Reporting decision rule.} Choose the perturbation to match the reporting question: individual trials, or weights of observed speakers and attacks. Report the point gap and both bands when a comparison is intended to withstand both checks. If the separation indicators disagree, label the comparison procedure-sensitive within the full comparison family and do not present trial-only separation as evidence that it survives the group check. Publish trial-to-speaker/attack membership and source weights alongside these results.
```

After:

```tex
\textbf{Reporting decision rule.} For comparisons intended to withstand changes in the weights of observed speakers and attacks, report the point EER difference and both trial and group-resampling bands for the same comparison family. If only the trial band excludes zero, report that separation depends on the resampling law; do not infer equality or population significance from the group band. Publish the group memberships and weighting rules needed to reproduce the check.
```

### 14. MAJOR-1

Place supportive and adverse simulations together, with procedure and model limits.

Before:

```tex
\textbf{Coverage boundary.} Coverage fell below .90 in 16/24 low-EER cells for each jackknife interval and 11/24 for PW percentile; all three failed in the same 11 cells (S7). These imposed-model simulations evaluate different intervals from the principal all-pair bands and do not establish a population sampling model for 21DF.
```

After:

```tex
\textbf{Coverage boundary.} In a separate simulation using the 21DF incidence and Gaussian speaker/attack effects fitted to RawNet2/LFCC-LCNN scores, nominal 95\% pointwise percentile intervals covered a true 0.5-point EER difference in 37/200 datasets (18.5\%) under trial resampling and 196/200 (98.0\%) under speaker$\times$attack resampling, using 300 bootstrap draws per dataset. In a separate 24-cell low-EER grid varying interaction strength, effect tails and the true gap, speaker$\times$attack percentile coverage fell below 90\% in 11 cells, reaching 85.5\% (1,000 datasets per cell; 500 bootstrap draws). These models have not been validated for 21DF, and these pointwise intervals differ from our all-pair bands; neither result establishes coverage for those bands.
```

### 15. MAJOR-5

Define class-normalized FRR and FAR within the PDF.

Before:

```tex
At each ordered position, bona-fide mass at or below it is the false-reject rate (FRR) and spoof mass above it is the false-accept rate (FAR); the first position minimizing $|\mathrm{FRR}-\mathrm{FAR}|$ is selected and EER is their mean, without interpolation.
```

After:

```tex
At each ordered position, the false-reject rate (FRR) is the fraction of bona-fide weight at or below it and the false-accept rate (FAR) the fraction of spoof weight above it; we select the first position minimizing their absolute difference and take their mean as EER, without interpolation.
```

### 16. MAJOR-5

Specify uniform draws and observed factor counts in the PDF.

Before:

```tex
In the speaker$\times$attack product-weight (PW) bootstrap \cite{owen07,oweneckles12}, speakers and spoof attacks are independently resampled with replacement; a spoof trial receives the product of its speaker and attack multiplicities, while a bona-fide trial receives only its speaker multiplicity.
```

After:

```tex
In the speaker$\times$attack product-weight (PW) bootstrap \cite{owen07,oweneckles12}, we independently draw speakers and spoof attacks uniformly with replacement, drawing as many of each as observed; a spoof trial receives the product of its speaker and attack multiplicities, and a bona-fide trial receives only its speaker multiplicity.
```

### 17. MAJOR-5

Retain the scope and design-status limits with less repeated prose.

Before:

```tex
\textbf{Interpretation.} The identified object is the change in $\Delta\mathrm{EER}$ and $I_{p,h}$ on the fixed scores, not population uncertainty. These are fixed-score sensitivity bands, not population confidence intervals or confidence sets for ranks. Four VCC spoof strata contain only 4/4/4/6 speakers, so no 21DF separation result transfers to new speakers or attacks. Conservatism results for crossed-array means \cite{oweneckles12} do not establish EER coverage. The one-factor, Monte Carlo, mean/sign, pairing, tie and influence diagnostics (S4a--S4e) were designed after examining the primary trial-versus-joint results and are exploratory, not preregistered. Indicator agreement is not a decomposition of the effect or a causal attribution to speaker identity: observed groups bundle trials, attacks and recording provenance, not intrinsic voice properties. Different detector rosters prevent attributing the primary/SpoofCeleb factor contrast to dataset alone. A band containing zero means the procedure does not separate that pair; it does not establish equality. Passing both checks does not guarantee an ordering under every possible reweighting or select a deployment ranking. Population confidence requires a defensible acquisition model and an inferential procedure valid under its dependence structure.
```

After:

```tex
\textbf{Interpretation.} These bands describe sensitivity of fixed scores to the stated weights, not confidence about future speakers or attacks. Four VCC spoof strata contain only 4, 4, 4 and 6 speakers. Coverage results for crossed-array means do not establish coverage for refitted EER differences \cite{oweneckles12}. The one-factor, Monte Carlo, mean/sign, pairing, tie and group-deletion diagnostics were designed after the primary results and are exploratory. Matching separation decisions does not decompose variance or identify a causal speaker effect. A band containing zero establishes neither equality nor a deployment ranking.
```

### 18. MAJOR-5

Define the acceptance rule and the exact mass constraint.

Before:

```tex
\textbf{Composition-preserving control.} Using 1,000 retained replicates, a constrained PW arm resamples within each bona-fide source or spoof stratum, conditions on retained class support, and restores each source and stratum mass to its observed value; it also separates 18/28 and 0/6 organizer pairs. This arm was designed after the main result and is a robustness check, not prospective evidence (S6). Thus neither threshold handling nor movement of these eight class-specific masses is necessary for the contrast.
```

After:

```tex
\textbf{Composition-preserving control.} A post-result PW control resamples speakers and attacks within each bona-fide source or spoof stratum, rejects draws with no class support in any required stratum, and rescales the three bona-fide source masses and five spoof-stratum masses to their observed values. Across 1,000 retained draws it separates 18/28 pairs and 0/6 organizer pairs. Thus movement of these eight masses is not required for the loss of separation; this does not remove influence from groups within a source or stratum.
```

### 19. REVIEW-70 MINOR-1

Identify that the loss occurs only under simultaneous correction.

Before:

```tex
A comparison separated under trial perturbations thus loses separation when observed speakers and attacks vary, even at this larger gap.
```

After:

```tex
Its joint pointwise percentile interval remains below zero, [$-4.252$, $-0.277$]; the loss is specifically under the 55-pair simultaneous band.
```

### 20. CUT tie check

Fourth-decimal tie accounting is reproducibility detail; the estimator remains explicit.

Before:

```tex
Across the eight systems and twelve fixed weighting rules, evaluating EER only at distinct-score boundaries changes each point EER by less than 0.001 percentage point. Recomputing distinct-score thresholds on all 45,000 checked weighted replicates preserved every separation indicator; the maximum band-endpoint change was 0.00024 point (supplement, S4d).
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 21. CUT ASVspoof 5

Peripheral experiment is unnecessary to the primary claim; full record remains in S8.

Before:

```tex
\textbf{ASVspoof 5 check.} An EER-only four-detector check also changes separation from 6/6 under trial resampling to 5/6; the SSL-AASIST and AASIST score files lack their originating run logs (S8).
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 22. CUT source deletion

Removes a secondary algorithm whose specification required leaving the PDF; S2 retains it.

Before:

```tex
\textbf{Surviving modern comparisons.} Of the two within-SSL pairs separated by joint resampling, Mamba--SSL-AASIST loses separation when VCC2018 is omitted (gap $-0.968\to-0.270$ points); SLS--SSL-AASIST loses it when VCC2020 is omitted ($-0.935\to-0.760$). For source deletion we use our jackknife sensitivity construction defined in S2, with the contrast variance floored at the larger one-factor variance and Gaussian max-$t$ calibration over all 28 pairs. Related to max-se methods \cite{mackinnon24}, it preserves all 16 cross-cohort separations without a coverage guarantee. The first loss combines gap shrinkage with the changed band; the second retains a sizeable gap but gains uncertainty.
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 23. CUT path definition

Used only by the removed constructive search; S5 retains it.

Before:

```tex
 For endpoint $w^1$, the path from empirical weights is $w(\lambda)=(1-\lambda)w^0+\lambda w^1$, $0\leq\lambda\leq1$. Distance is maximum classwise total variation (S5).
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 24. CUT witness

Retain the twelve-rule test and its positive control; remove searched reversal details.

Before:

```tex
 S5 gives a constructive Mamba--SLS reversal and its searched masses. The reversing sign also holds at distinct-score boundaries (supplement, Sec.~S5).
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 25. Ethics dependency

Match the datasets remaining in the PDF; keep both statements on page four.

Before:

```tex
This study analyzed previously collected ASVspoof~2021, ASVspoof~5 and SpoofCeleb recordings and detector scores.
```

After:

```tex
This study analyzed previously collected ASVspoof~2021 and SpoofCeleb recordings and detector scores.
```

### 26. MAJOR-5

Remove a provenance pointer after making its retained result self-contained.

Before:

```tex
 (S4a)
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 27. MAJOR-5

Remove a provenance pointer after making its retained result self-contained.

Before:

```tex
 (S2a)
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 28. MAJOR-5

Remove a provenance pointer after making its retained result self-contained.

Before:

```tex
 (S4b)
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 29. MAJOR-5

Remove a provenance pointer after making its retained result self-contained.

Before:

```tex
 (S4c)
```

After:

```tex
[Deleted from submitted PDF; complete technical record retained in supplement.]
```

### 30. MAJOR-5

One provenance locator; final artifact hash will be inserted after the artifact commit.

Before:

```tex
\textbf{Artifact.} Supplement S4a--S4e supplies the complete four-arm bands, Monte Carlo repeats, mean/sign and pairing diagnostics, weighted-tie checks and group influence. The three evidence JSON files and analysis code accompany artifact version \texttt{4ee170b035f46097832f0973aff534418fc54157} at \mbox{github.com/rvirgilli/asvspoof2021-df-clustered-uncertainty}; S8 gives file selectors and hashes.
```

After:

```tex
\textbf{Artifact.} Code, score provenance, complete numerical results and additional reproducibility checks are available in the public artifact. Artifact version \texttt{4ee170b035f46097832f0973aff534418fc54157} at \mbox{github.com/rvirgilli/asvspoof2021-df-clustered-uncertainty}.
```

### 31. MAJOR-3 fresh-stream verification

The predeclared fresh streams are now archived and independently recomputed; conditional and fresh evidence stay distinct.

Before:

```tex
This assesses Monte Carlo noise conditional on saved draws, not independent-seed stability.
```

After:

```tex
This assesses Monte Carlo noise conditional on saved draws, not independent-seed stability. Five fresh 5,000-draw runs for each of the trial, speaker-only and joint arms also preserve every recorded separation indicator.
```
