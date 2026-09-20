# Concentrated speaker-group influence rewrite

The paper now asks how concentrated observed speaker-group influence is on
paired detector comparisons on ASVspoof 2021 DF. Its contribution is the measured
three-pair deletion pattern inside a complete 28-pair family: speaker-only
reproduces the primary joint decisions, but attacks still change distributions
and some decisions. The weakly transferred SpoofCeleb roster provides a limited
mirror-pattern counterexample. This is fixed-score sensitivity without population
coverage or an exclusive tail explanation.

## Evidence and space decisions

- Print all 28 gaps and trial/joint simultaneous bands, grouped as six SSL, six
  organizer and sixteen cross-cohort comparisons, at three decimals. Single-letter
  system abbreviations sit beside all eight point EERs. A star marks each loss.
- Print the three affected SSL pairs' largest contributor, deletion gap and
  largest/top-five concentration shares. Define the mean-centered squared-deletion
  denominator once in Method. Keep all groups in the principal analysis.
- Keep four-arm counts (including the attack-only range) and the full mean/sign
  table. Add the trial/joint critical values and the SSL-only six-pair control.
- Print the composition-preserving band directly beside the primary band, retained
  draw count, seed and rejection count. The sign of the archived reversed pair is
  explicitly reversed to match Mamba minus Conformer.
- Name all four SpoofCeleb systems and transferred EERs, including AASIST at 57.93%.
  Print all six four-arm decisions and trial/joint numerical bands for the three
  joint losses. We choose trial/joint numerical bands plus four-arm decisions,
  rather than a second complete four-arm endpoint inventory, to preserve legibility.
  The pooled trial law, stratified result and distinct roster limit stay explicit.
- Use 315 of 14,869 bona-fide trials to state the deletion's scale, without adding
  a computed percentage not printed in the permitted source material.
- Remove the Arena headline and every Arena reference from the PDF. Remove both
  fixed-weighting subsections/results, the historical-test reconstruction aside,
  and both simulation summaries. Remove the forest plot and mixed display.
  The complete artifact retains these analyses, original figures and Arena citation.
- Retain the established related-work context, but remove the now-unneeded Arena
  citation. No new experiment, score, model or empirical number is introduced.

The layout replaces the mixed table and forest plot with one complete primary
table and a three-row influence table, separates the existing arm counts, retains
the mean/sign table and adds the compact SpoofCeleb display. Exact measured display
heights and extracted word accounting are recorded with the final PDF in the
external `REWRITE-NOTE.md`; this artifact precedes that PDF by design.

## Interpretation and expected tradeoff

No attacks-null claim: primary speaker-only/joint indicator agreement coexists
with different SDs and sign frequencies. No universal speaker-only prescription:
SpoofCeleb's attack-only decisions mirror its joint decisions. No exclusive tail
mechanism: deleting a genuine-only group also renormalizes the class and refits
thresholds. The concentration is measured, not explained.

The forecast remains novelty/correctness/significance/clarity 3/4/3/4, with
significance upside to 4, not a promised score. Removing Arena and weighting
sacrifices the striking secondary number and breadth to make the strongest primary
evidence inspectable. As the supplied judgement records, the artifact's Arena
RawNet2 release agrees with the maintained leaderboard (40.669% rounded), while
the cited paper's older table gives 22.38% for 2021 DF; removing Arena also removes
that upstream table/release discrepancy from the submitted argument. No Arena
value has been corrected or altered.

## Obligations and two-stage release

All 138 inherited obligations, including all 97 originals, remain. Superseded PDF
wording is explicitly archived in supplement S10 and remains deletion-tested;
current claims and tables have added obligations. The checker changes are forced
by the replaced displays and relocated simulations and add numeric binding for
the newly printed evidence. `paper/OBLIGATION-REWRITE.json` is the complete ledger.
Both guards ran after each logical edit batch, including failed intermediate
iterations. Successful stage outputs are preserved under `paper/rewrite-validation/`;
intermediate outputs remain in the external `validation-history/` directory.

The artifact commit is made first, retaining the predecessor PDF as identified
history. The submission then inserts the full artifact hash, rebuilds `main.pdf`,
and records measured font/page/URL compliance. Neither predecessor commit is
amended; no push or tag move is performed. The fresh external audit and calibrated
PDF-first review are later gates, not results claimed by this local rewrite.
