# Deviation ledger

This ledger distinguishes the frozen analysis plan from the analysis that is
reported. It is not evidence of a public timestamp: the original freeze lived
in private project history, and no retroactive timestamp is claimed.

Files under `plans/` are retained as historical records rather than silently
rewritten. In particular, EXP-105's report and the stopped EXP-107-v1 plan still
contain their then-current recommendation to retain organizer-only formal
inference. That recommendation is superseded by the later source/task incidence
audit, the post-audit diagnostics, this ledger and the current paper; it is not
the repository's present scientific position.

| Frozen plan | Executed analysis | Reason and consequence |
|---|---|---|
| `B=1000` | `B=5000` for the primary pairwise campaign | Monte Carlo precision was increased; seeds and replicate counts are recorded in the artifacts. |
| Adjacent pairs, with Holm over the adjacent family | All 28 pairs, with one sup-t band over all 28 | Adjacency is selected by observed scores. Expanding to the full family avoids post-selection inference and is more conservative than the frozen family. |
| “Certified trio”: product bootstrap, a subtraction-based pigeonhole variant, and jackknife | Product bootstrap plus delete-one jackknife; pigeonhole variant withdrawn | The subtraction formula was not Owen's correction. Coverage at `R=200` is described as a failure check, never certification. |
| One Bengio--Mariéthoz reconstruction attributed to the overview | Independent and paired-decision reconstructions, with no cell-level attribution | The overview cites the source but does not disclose which variant produced its figure. Both reconstructions yield 5/6; speaker×attack product perturbation yields a 0/6 numerical output. |
| Eight “official-score” systems | Eight high-provenance author/organiser releases as the primary layer | The original wording overstated the pool. Eleven Speech DF Arena re-scores are now analysed only in a separate provenance stratum. |
| Pair-specific floor language treated the speaker term as an attack-count asymptote | The term is called a finite-attack speaker component; the attack-budget extrapolation is withdrawn | Delete-speaker variation also contains speaker×attack interaction divided by the observed attack count. |
| Floor-count bootstrap drew speakers independently per pair | One shared speaker draw per replicate across all ten unresolved pairs | The original implementation destroyed cross-pair covariance. The corrected interval is `[5,10]`, with `P(count>=5)=0.997`. |
| Approximate intersection term `V_speaker + V_attack - V_iid` | Exact observed speaker×attack-cell delete-one term audited in EXP-105 | The approximation's direction was not guaranteed. The smooth CRVE path failed its strict linearization gate and is not used for claims; exact-cell coverage is evaluated separately. |
| Trial-i.i.d. and clustered calculations used non-identical threshold handling | Post-audit matched diagnostic refits the same non-interpolated EER threshold in every replicate in both arms | The 5/6 versus 0/6 organiser contrast remains, isolating the specified perturbation unit rather than threshold treatment. This is descriptive fixed-data sensitivity, not a new preregistered population analysis. |
| Pair-specific marginal floors were used with a different joint covariance for max-$t$ | One PSD covariance, $\Sigma_s+\Sigma_a$, supplies every pair SE and the joint critical value | The coherent construction deliberately retains the observed-cell overlap and is a Loewner-dominating sensitivity covariance, not an exact multiway estimator or coverage guarantee. It gives 18/28 and 0/6 organiser zero-exclusions, matching product weights. |
| No public re-score replication | EXP-104, frozen before pairwise Arena inference | All eleven complete Arena files form one separate 55-pair family; its registered numerical procedure output was reproduced, but later coverage and incidence audits withdrew inferential interpretation. |
| No second-benchmark replication | EXP-106, frozen before two new ASVspoof 5 score passes | Four detectors and all six pairs are analysed after the registered GPU scoring job completes. |

Additional source-corpus, leave-one-corpus-out, width-scaling and finite-attack
diagnostics were added after the initial plan. They are supporting analyses and
their scripts, seeds and complete outputs are released; none changes the frozen
primary pairwise estimand.
