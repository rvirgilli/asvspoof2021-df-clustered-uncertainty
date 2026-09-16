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
