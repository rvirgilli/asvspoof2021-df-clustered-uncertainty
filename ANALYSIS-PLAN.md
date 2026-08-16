# Analysis plan (frozen before the campaign ran)

This is the analysis plan for the clustered-inference audit of ASVspoof 2021 DF, frozen before
any campaign result was computed. It is derived from the project's internal pre-registration
record: **the scientific content is reproduced unchanged, and project-internal resourcing and
workflow notes are not included.** No hypothesis, method, criterion or decision rule has been
altered, weakened or added.

Three presentational changes, so the derivation can be checked rather than trusted:

1. **Decision-tree branch names are descriptive**, replacing internal shorthand. Every trigger
   condition and every scientific consequence is reproduced verbatim; only the labels differ.
2. **Two consequences carried internal workflow accounting**, which is removed. Those phrases
   conditioned no scientific outcome; the substantive consequence text is verbatim.
3. **Resourcing estimates are omitted**, including the cell list's budget column. Everything
   else is verbatim, which means a few references point at project-internal material that is
   not published here: the *Method* column names earlier pilot studies (`EXP-0NN`) and internal
   scripts, and the decision tree and addenda cite an internal specification document and its
   limitation labels.

What is *not* changed: the hypothesis (including the clause the campaign later withdrew), the
system pool, every cell and its method, every branch trigger and consequence, the kill guard,
the prohibition on editing the tree after results exist, and both dated addenda with their
"before X was computed" statements intact.

---

## Hypothesis

On official per-trial score files, certified clustered 95% CIs on paired ΔEER are ≥5× wider than
i.i.d. CIs; published adjacent pairs with |Δ| ≤ ~1 pt flip from resolved (fixed-set) to
unresolved (generalization); power curves yield a concrete cluster-count prescription.

*(The third clause was withdrawn during the campaign: the fitted power model was found to be
mis-specified in the low-EER regime and no cluster-count prescription is made. It is reproduced
here because this document records what was frozen, not what survived.)*

## System pool

Official per-trial score files only.

21DF (eval phase, 533,928 trials; locally verified EERs): XLSR-Mamba 1.884 · XLS-R+SLS 1.916 ·
XLSR-Conformer (fixed-size train) 2.273 · SSL-AASIST 2.85 (author release) · RawNet2 22.38 ·
LFCC-LCNN 23.48 · LFCC-GMM 25.25 · CQCC-GMM (organizer). ITW: official author releases for
XLS-R+SLS and XLSR-Mamba; reproductions for SSL-AASIST/AASIST (mixed sourcing stated in the
paper). XLSR-Conformer eval-lv variant (2.583) is a robustness row, not a pool member. TCM
(checkpoint-only) is excluded; an author-email request is a contingency item only if a reviewer
demands it.

## Fixed cell list

| # | Cell | Fills | Method |
|---|---|---|---|
| 1 | Sanity: reproduce published pooled EERs from official files (eval-phase filter), all pool members, 21DF + LA + ITW where released | §4 text | extend EXP-003 loader |
| 2 | ICC / variance components per (system, factor, class) incl. **cross-generation comparison** (GMM → RawNet2 → SSL → Mamba/SLS/Conformer) | §4 diagnostics; feeds power bands | EXP-009 method-of-moments code |
| 3 | Full pairwise inference, 21DF: adjacent pairs of the sorted-EER ladder + Speech-DF-Arena adjacent pairs where both members have official scores; schemes: naive bootstrap, Wang–Yamagishi z-test, unclustered permutation, and the certified trio (two-way percentile, pigeonhole, jackknife); B=1000, seed 20260813 | Table 1 | extend `m1_bootstrap.py` |
| 4 | ITW table: speaker-clustered, same schemes minus attack factor, 4 systems | ITW table | `m1_itw.py` extension |
| 5 | DGP-robustness: coverage at Δ=0.5, 21DF-like, with semi-synthetic replicates (resample real per-cluster residuals from official RawNet2/LFCC-LCNN scores instead of Gaussian draws) | Table 2 row | EXP-009 sim + residual pools |
| 6 | Cluster-count sweep + power curves: calibrated simulator at measured ICCs (cell 2), A ∈ {5,10,20,40,80,110} × S ∈ {12,25,50,93}; P(two-way clustered 95% CI excludes 0) for true Δ ∈ {0.2,0.5,1.0}; MDE at 80% power; **ICC-conditioned bands** across the observed per-system ICC range; empirical subsample cross-check on real scores at 3 grid points; **no headline claims beyond observed cluster counts** | Fig. power | EXP-009 sim |
| 7 | Equivalence-class re-ranking figure (21DF + ITW) from cell 3/4 CIs | Fig. equiv | plotting |
| 8 | Toolkit packaging (two-way crossed scheme, EER/ΔEER, certified-variant defaults) | release artifact | supporting — runs only after cells 1–7 |

**Contingency set:** wild-cluster-style variant added to the tested set, min-tDCF secondary
metric, 21LA official-score table (Mamba 0.93 / Conformer-var 0.87 / SLS 2.87 — Δ down to 0.06),
extra Δ values in power curves.

## Pre-registered decision tree

Evaluated on cell-3 results with the certified trio's consensus (all three agree), per the
spec's margins.

1. **Clustered-inference audit stands (expected):** ≥1 adjacent pair with |Δ| ≤ 1 pt is
   naive-resolved but clustered-unresolved (EXP-003 already guarantees the organizer-generation
   pairs qualify), AND width ratios ≥5× on ≥half the pairs. SOTA-pair outcomes (Δ = 0.03–0.58)
   are reported as measured, including "unresolved under both" (a fixed-set tie is a valid
   verdict, not a failure).
2. **Generation-contrast emphasis (same branch, framing only):** if all SOTA-adjacent pairs are
   unresolved even under naive i.i.d. (deltas below even the i.i.d. floor), the dual-estimand
   table carries a generation-contrast paragraph; no new experiments.
3. **Switch to the miscalibration-as-finding branch** (per its validated constraints) iff
   cell 5's semi-synthetic coverage falls outside [90, 99] for every variant in the certified
   trio — i.e. the Gaussian-DGP certification does not survive real residuals. Supporting cells
   are a subset of this campaign + the contingency wild-cluster variant.
4. **The organizer-baselines-only branch is closed** (its trigger — unobtainable official scores
   — was resolved on 2026-08-14) and cannot be entered.
5. **Kill guard:** if cell 3's certified-trio CIs are narrower than naive CIs on the majority of
   pairs (contradicting EXP-003/EXP-009), the campaign halts and both pilots are re-audited
   before any writing continues.

At most one change of framing after results; tree edits after results exist are prohibited.

## Addendum 2026-08-14 (spec gate — before multiplicity analysis is computed)

- **Multiplicity policy, pre-committed:** the paper reports, alongside per-pair 95% CIs,
  Holm–Bonferroni-adjusted verdicts over the family of adjacent pairs per dataset (7 on 21DF,
  3 on ITW), computed from the same B=1000 cell-3 bootstrap draws (percentile p-values). The
  headline "unresolved" claims are per-pair CI statements; the adjusted column is reported for
  comparability with ASVspoof 5 practice. Policy fixed before any multiplicity-adjusted numbers
  are computed. (Cell-3 raw CIs existed at addendum time; no adjusted analysis had been run.)
- **Contingency items activated at the gate:**
  - C1 low-EER coverage replicate: simulator calibrated to the XLSR-Mamba/XLS-R+SLS measured
    components, certified-trio coverage at S=93, A=110, true Δ = 0.2 pts, R=400.
  - C2 attack-family/codec ICC diagnostic: cell-2 method-of-moments re-grouped by vocoder family
    (metadata col 9) and codec condition (col 3) on 21DF.
  - C3 wild-cluster-style variant added to the tested set: two-way wild bootstrap on jackknife
    influence contributions (Rademacher weights per speaker and per attack, influence scaled so
    total variance matches the inclusion–exclusion V_spk+V_att−V_naive), percentile CI; reported
    next to the certified trio, coverage-checked in C1's run.
- **Rejected at the gate (decided once):** codec/transmission as a third crossed clustering axis
  — answered by limitation L1 + the C2 diagnostic.

## Addendum 2 — 2026-08-14 (C1-b decision rule, agreed BEFORE C1-b results)

If C1-b (semi-synthetic real-residual pools, near-realistic per-cluster counts NB=100/NC=10)
confirms coverage degradation at the low-EER SOTA calibration: the certification claim is
**scoped by EER regime** in prose + a limitation sentence; coverage tables report the regime
split; the headline (organizer-generation flips at Δ 0.36–1.77) stands as-is. Honest scoping
within the primary branch. If C1-b shows the certified trio holds at realistic tails: report
both sims, no scoping needed. Either way the SOTA-pair rows in Table 1 keep their measured
verdicts with whichever caveat applies.

---

*Two terms above did not survive the campaign and are corrected in the paper rather than here,
because this document is the frozen plan: the "certified" variants are described in the paper as
simulation-checked (at R = 200 a coverage estimate near .95 carries roughly ±3 points, which
does not support a certification claim), and the pigeonhole variant was withdrawn as not being
Owen's correction.*
