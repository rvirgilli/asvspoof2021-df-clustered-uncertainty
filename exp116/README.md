# EXP-116 — bands under each registered weighting rule (post-result verification)

`PREREG.md`, `REPORT.md`, `RESULTS.json` and `run.log` are byte-identical to the private
run of record except that `run.log` has its absolute output path replaced by `exp116`.
`FREEZE.sha256` binds the private `PREREG.md`, `run_policy_bands.py` and `pyproject.toml`;
the copy of `run_policy_bands.py` here differs from the frozen script in one line, the
import path of the EXP-108 weight builder (`code/exp108/`), and therefore has a different
hash. `RESULTS.json` records the frozen script hash under `script_sha256`.

Rerunning needs the official DF key metadata and the eight score files described in
`data/README.md`; the estimator gate then reproduces `derived/results_composition.json`
contrasts to 1e-9 before resampling.
