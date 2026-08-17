# EXP-108 composition robustness

This directory contains the metadata-only contract builder, the 12-policy
composition analysis, independent verifier, post-failure constructive witness
search, three-backend verifier, tests, and the two frozen plans.

Run in a disposable clone after setting `M1_DATA_ROOT` and
`M1_SSL_AASIST_SCORES` as documented in `data/README.md`:

```bash
uv run --frozen python code/exp108/build_contract.py
uv run --frozen python code/exp108/analyze.py
uv run --frozen python code/exp108/verify_results.py
uv run --frozen python code/exp108/search_witnesses_v2.py
uv run --frozen python code/exp108/verify_secondary_v2.py
```

The first three commands regenerate the primary composition multiverse. The
constructive search is substantially longer and does not alter the frozen
primary classification. Compare regenerated outputs with the corresponding
files under `derived/`; public copies differ only in path-bearing provenance
fields and their dependent file hashes.
