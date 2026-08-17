# Sampling-unit sensitivity in ASVspoof system comparisons

This repository accompanies **“Five Significant Differences Disappear When
ASVspoof Trials Are Not Treated as Independent.”** It contains the exact
submitted manuscript, code, plans, deviations, and derived artifacts for a
re-analysis of pairwise system comparisons on the ASVspoof 2021 DeepFake (DF)
evaluation set.

## What this is

The DF evaluation set contains 533,928 trials: 14,869 bona fide trials from 93 speakers
and 519,059 spoof trials spanning 110 attack conditions. The significance test published
with the challenge treats trials as independent observations.

This repository contains the estimator, the analysis scripts and a derived audit artifact
for a paired two-way bootstrap that resamples **speakers and attack conditions** rather
than trials, applied to all 28 pairwise comparisons among eight high-provenance author or
organiser releases. A matched post-audit diagnostic recomputes the identical EER threshold
and all-pair max-$t$ rule in both arms: trial-i.i.d. perturbation gives 26/28 and 5/6
organiser zero-exclusions, against 18/28 and 0/6 with speaker×attack weights. A second
construction uses one PSD marginal-sum covariance for every pair SE and the joint critical
value and separately gives 18/28 and 0/6. It is a coherent sensitivity covariance, not
an exact multiway variance estimator or coverage claim. The completed 48-cell EXP-105 audit
**refutes** extension of those intervals to low-EER regimes. A later source/task incidence
audit also rejects the global exchangeability law required for full-21DF population
inference: 85.77% of spoof trials lie in four blocks containing only 4/4/4/6 speakers.
Consequently every full-21DF interval and verdict in this repository is a descriptive
procedure-sensitivity output, including the organiser block. The organiser-like simulation
cells validate implementation behavior under their imposed DGP, not that DGP as a model of
the benchmark. A separate eleven-system Speech DF Arena re-score layer is included for
provenance and descriptive sensitivity and is never mixed into the primary ranking.

The committed release is the artifact a reader needs to check every reported
number and the boundaries placed on its interpretation.

## Contents

| Path | Contents |
|---|---|
| `ANALYSIS-PLAN.md` | the analysis plan, frozen before the campaign ran |
| `DEVIATIONS.md` | every material difference between that plan and the reported analysis |
| `plans/` | frozen preregistrations for the Arena, multiway-correctness and ASV5 additions |
| `audit/audit.json` | the primary audit package, derived rather than transcribed |
| `audit/README.md` | what each key answers, the estimand, and the scope statements |
| `derived/` | committed machine-readable campaign outputs used by the clean-clone checker |
| `paper/` | the exact paper and figure source checked against those outputs |
| `code/` | the estimator, analysis scripts, audit builder, and checkers |
| `data/README.md` | source, sha256, byte and line counts for all nine input files |
| `REPRODUCE.md` | reproduction levels, exact commands, and the raw-data boundary |
| `MANIFEST.json` | sha256 and byte size of every versioned release file |

## Reproducing

The paper-to-result checker is intentionally runnable without third-party data:

```
uv sync --frozen
uv run --frozen python verify_release.py
```

That command authenticates the release and checks `paper/main.tex` against named paths in `derived/`,
including the matched perturbation diagnostic, coherent covariance result, incidence audit
and separate Arena replication. It also verifies the exact historical result identities and
the hashes of the public path-adapted scripts. It does not pretend to regenerate an experiment.

To re-derive the audit package from the third-party score files, obtain the inputs described
in [`data/README.md`](data/README.md), set the listed environment variables, then run:

```
uv run python code/make_audit_package.py
diff -u audit/audit.json audit-regenerated/audit.json
uv run python code/check_tie_safety.py
```

The builder reads the public score files plus the committed campaign outputs in `derived/`
and writes only to ignored `audit-regenerated/`; it never overwrites the canonical artifact.
The individual scripts in `code/` regenerate those derived outputs when their documented
inputs are available. This distinction is explicit: the fast clean-clone check validates the
paper-to-artifact contract, while a full campaign reproduction recomputes the artifacts.

For example, the separate Arena layer can be input-checked without running its 10,000 total
bootstrap replicates, or regenerated with the frozen draw count:

```
uv run python code/analyze_arena.py --check-only
uv run python code/analyze_arena.py
```

Its resumable arrays live under `M1_ARENA_RUN_ROOT`, outside the repository. The complete
artifact-to-script map is in [`derived/README.md`](derived/README.md), and
the separated verification levels are in [`REPRODUCE.md`](REPRODUCE.md).

EXP-105 is a CPU simulation, not detector training or rescoring. Its 48,000 outer-replicate
rows are intentionally checkpointed outside Git. Given a run root containing the released
contracts and shards, the complete closure is regenerated with:

```
export M1_MULTIWAY_COVERAGE_ROOT=/path/to/EXP-105/coverage
uv run --frozen python code/coverage_interaction.py --aggregate
uv run --frozen python code/recalibrate_truth.py --n-half 5000000 --repeats 8 --workers 8
uv run --frozen python code/verify_crosspath_gate.py --draws 32
uv run --frozen python code/diagnose_low_eer.py
uv run --frozen python code/aggregate_verified.py
```

`derived/results_exp105_verified.json` records the contract and content hashes and row count
for every shard. `derived/provenance_exp105.json` distinguishes the exact historical campaign
bytes from the public path-adapted copies; the checker validates both identities instead of
claiming that different source bytes emitted the canonical JSONs.

If a committed machine-readable result disagrees with the paper, the paper is wrong.

Each input file's sha256, byte count and line count is recorded under
`audit.json:provenance`, so a reader can confirm they hold the same bytes used here.

## Scientific target

Two deterministic systems on a frozen trial list have no sampling uncertainty without a
declared sampling law. The source/task audit shows that the benchmark does not support the
global exchangeable-speaker×exchangeable-attack law originally proposed here, and the 93
speakers and 110 attacks are not a probability sample from a named population. This
repository therefore does **not** claim a full-21DF population estimand.

The identified object is computational: how paired ΔEER procedure outputs on the fixed
released scores change when trial-level weighting is replaced by specified speaker×attack
reweighting. With threshold estimation and multiplicity matched, trial-i.i.d. weighting
resolves five of six organiser pairs whereas product weighting resolves zero; a coherent
marginal-sum covariance also resolves zero. That 0/6 label is itself composition-dependent:
three organiser pairs become resolved in at least
one leave-one-corpus-out refit. It is a sensitivity measurement, not corrected significance
inference.

## Known limits

These are stated in full in [`audit/README.md`](audit/README.md). In summary:

- Provenance for the four self-supervised systems is by hash of the released score files.
  Those systems were not retrained or re-scored from audio here.
- EXP-105 crosses two EER regimes, four interaction shares, two tail families and three
  true gaps, with `R=1000` and a `B=500` product bootstrap in each of 48 cells. Organiser
  coverage is `.928--.957` for exact-cell intervals and `.946--.968` for product-percentile.
  Low-EER minima are `.845/.845/.855`; the preregistered universal-coverage claim is Refuted.
- The corpus decomposition rests on three source corpora, i.e. two degrees of freedom. The
  permutation null and the leave-one-corpus-out refits are reported for that reason.
- Source/task stratification leaves almost no empty cells overall, but the dominant VCC
  blocks contain only 4/4/4/6 spoof speakers. No resampling of the existing rows can create
  the missing independent units needed for full-benchmark population inference.
- The former attack-budget extrapolation is withdrawn. The measured speaker term is a
  finite-attack component containing speaker×attack interaction; it is not an
  attack-count asymptote. The exact observed-cell correction does not identify the
  interaction distribution in structurally absent speaker--attack cells.

## License

Code is released under the MIT License (`LICENSE`). The input score files and evaluation
key are covered by their respective original licenses and are not redistributed.
