# Monte Carlo verification fixed before running

The conditional check reproduces RECONSIDERATION.md: NumPy 2.4.6,
SeedSequence(2026092001).spawn(3) in trial, speaker_attack, speaker_only order;
1,000 successive complete-row resamples of size 5,000 per arm; ddof=1,
linear 0.95 quantile of the centered all-28-pair maximum; unrounded saved hats.
Archive the q, SD and indicator arrays. Independently reconstruct them using
row multiplicities and weighted moments.

The fresh check uses SeedSequence(2026092002).spawn(3) in the same arm order,
then each child's spawn(5), all fixed before looking at any endpoints. Every
stream has 5,000 draws. The historical input hashes, estimator, classwise trial
law, joint and speaker laws, system pairing and 28-pair maximum are retained.
No stopping or seed selection follows an observed count. Archive all 15 arrays
and all pair endpoints; report any variation. Numba accelerates the unchanged
first-minimum EER calculation without fastmath; compare the first ten historical
draws per arm both to the NumPy estimator and to the saved outputs before running.
Checkpoint blocks on scratch storage for interruption recovery.

These assess numerical Monte Carlo noise, not population coverage. The fresh
check is verification; it is not a new data collection or detector experiment.

From the release root (inputs as in REPRODUCE-DIAGNOSTICS.md):

```
uv run --frozen python code/revision_mc.py conditional --out regenerated/revision-mc
uv run --frozen python code/revision_mc.py fresh --out regenerated/revision-mc --scratch /tmp/revision-mc-blocks --workers 16
```
