# Reproduce the diagnostics

This revision ships the portable drivers in `code/`, the regenerated diagnostic
and influence JSONs, and both distinct replicate archives in `evidence/`.
The earlier artifact `4e2ad2fcf080` does not contain these portability repairs.

Use Linux (diagnostics uses `fork`), uv, Python 3.11, NumPy 2.4.6 and SciPy
1.17.1. No detector inference, audio, training or GPU is needed. Obtain the
protocol key and eight score files described in [data/README.md](data/README.md),
approximately 205 MB total. Place them at the release-relative paths under
`inputs.paths` in root `ABLATION-RESULTS.json`. That path map is authenticated
by `MANIFEST.json`; the drivers independently check all nine full input hashes
against immutable `evidence/ABLATION-RESULTS.json`.

From a fresh clone's root, after placing the inputs, run either driver:

```bash
uv run --no-project --python 3.11 --with numpy==2.4.6 --with scipy==1.17.1 python code/strategy_influence.py
uv run --no-project --python 3.11 --with numpy==2.4.6 --with scipy==1.17.1 python code/strategy_diagnostics.py
```

The output is `regenerated/diagnostics/`. Each driver refuses to overwrite its
completed JSON. For another run, choose an empty directory with
`M1_DIAGNOSTICS_OUT`. No path override is required. Optional `M1_RELEASE_ROOT`
selects another release; `M1_INPUT_ROOT` selects a directory containing the
same `external-inputs/` tree, without changing any required input hash.
`M1_DIAGNOSTICS_WORKERS` defaults to 20, one numerical thread per worker;
influence uses one process. The drivers and their imports need only NumPy and
SciPy in addition to the standard library.

Allow about 20 minutes for diagnostics on a 16-core Ryzen 9 9950X with 20
workers; the supplied portability run took 1037.030653 seconds. Influence
took 14.705668 seconds while that run was active. Fewer cores require fewer
workers and more time. These are recorded measurements, not runtime guarantees.

The archives have separate roles: `ABLATION-REPLICATES.npz` holds the two saved
ablation arms; `replicates.npz` holds all eighteen diagnostic arrays. After
diagnostics, the exact archive comparison is:

```bash
cmp evidence/replicates.npz regenerated/diagnostics/replicates.npz
```

JSON byte identity is not claimed: both serializers record newly measured
execution times, and diagnostics records the files protected during that run.
The supplied regenerated JSONs preserve the original statistical results
exactly and bind the portable executable hashes. A fresh influence run must
reproduce every field except its two timing measurements; the complete
comparison, including those differences, belongs in its validation record.
Do not substitute historical timings or protected-file hashes into a rerun.
See [PORTABILITY-NOTE.md](PORTABILITY-NOTE.md) for the historical acceptance
failure and this revision's evidence identities.

## September 20 primary Monte Carlo checks

The original drivers and evidence are unchanged. The revision adds conditional
row-resampling and five fresh score-level streams for each other primary arm.
The predeclared protocol is [REVISION-MC-PLAN.md](evidence/REVISION-MC-PLAN.md).
Run `code/revision_mc.py` as documented there, then independently verify the
released arrays with:

```bash
M1_INPUT_ROOT=/path/to/input-root uv run --frozen python code/verify_revision_mc.py
```

The input root contains the hash-checked `external-inputs/` layout above. The
verifier also reparses the protocol to confirm the influential group's class
composition. The two supplementary copies remain byte-identical. These CPU
checks do not run detector inference or training.

## FIX5 deterministic speaker deletions

The historical driver and evidence above remain unchanged. For the current
Table 2, use the same nine public inputs and the locked environment, then run:

```bash
uv run --frozen python code/influence_trial_id.py
cmp evidence/influence-trial-id.json regenerated/influence-trial-id.json
```

The new producer depends only on Python and NumPy (2.4.6 in `uv.lock`), validates
all nine input hashes and orders score ties by ascending trial ID. It recomputes
all 93 speaker deletions for the four SSL systems and saves the three printed
pairs' top-five summaries. It refuses an existing output; use `--out` for a new
path. There are no timings or machine paths in this deterministic output.
The composition control was withdrawn; this command does not regenerate it.
