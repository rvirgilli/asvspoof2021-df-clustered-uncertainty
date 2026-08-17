# Post-audit coherent jackknife-family diagnostic

Frozen 2026-08-16 before executing this diagnostic.  It is not a
preregistration: the real-data multiway components and their earlier verdicts
were already known.  An independent reviewer correctly observed that the
existing exact-cell simultaneous output combines a critical value derived from
a PSD-projected raw system covariance with separately floored pair variances;
those pieces do not form one coherent joint covariance model.

## Frozen construction

Using the saved exact delete-one refits, construct the system-level covariance

`Sigma_sum = Sigma_speaker + Sigma_attack`.

Both terms are positive semidefinite by construction.  `Sigma_sum` dominates
each marginal in Loewner order, and it dominates the raw exact-cell
inclusion--exclusion matrix because

`Sigma_sum - (Sigma_speaker + Sigma_attack - Sigma_cell) = Sigma_cell`,

which is also positive semidefinite.  This deliberately retains rather than
subtracts the observed-cell overlap; it is a conservative marginal-sum
sensitivity covariance, not the exact multiway variance estimator.

- Use all eight systems and all 28 pair contrasts.
- Draw 200,000 centered Gaussian system vectors from `Sigma_sum` with seed
  `2026081605`.
- Compute the 95th percentile of the maximum absolute pairwise studentized
  contrast using the pair covariance induced by the same `Sigma_sum`.
- Form every simultaneous output with that same joint covariance and critical
  value.  No pairwise variance floor is applied.
- Primary reading: number of zero-excluding outputs among the six organiser
  baselines; secondary reading: all-28 labels and comparison with product
  reweighting and the earlier floored exact-cell diagnostic.

## Interpretation guard

This is a mathematical-coherence repair for a descriptive sensitivity layer.
It has no coverage claim and does not identify a population sampling law.  The
raw exact-cell inclusion--exclusion components remain reported, but their
floored simultaneous labels must not be used as independent formal evidence.

