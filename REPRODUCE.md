# Reproduction guide

## Level 1 — paper from frozen public artifacts

This CPU-only level uses only versioned repository files:

```bash
uv sync --frozen
uv run --frozen python verify_release.py
```

The gate authenticates every release file, runs the scientific contract checker and
the 29-case caveat-deletion mutation suite, verifies the exact nonlicensed EXP-115
delivery and failure-injection tests, and independently verifies the portable ASVspoof 5
bundle. It does not access
third-party score files or rerun any scoring model.

Individual commands are:

```bash
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python exp115/verify_receipt.py
uv run --frozen python -m unittest -v exp115/test_analyze.py exp115/test_verify_receipt.py
uv run --frozen python audit/verify_asv5_package.py
```

## Level 2 — rebuild figures and the raw-score audit core

Figures use committed derived data:

```bash
uv run --frozen python paper/figures_m1.py
```

To rebuild the raw-score core of `audit.json`, obtain the nine public inputs listed in
`data/README.md`, set `M1_DATA_ROOT` and `M1_SSL_AASIST_SCORES`, and run:

```bash
uv run --frozen python code/make_audit_package.py
uv run --frozen python code/compare_audit_core.py
```

The builder writes `audit-regenerated/audit-core.json`. The comparator requires
all 16 reconstructed blocks to equal the corresponding blocks in the canonical
composite package. The nine later closures embedded in `audit/audit.json` are
verified from their hash-bound public envelopes at Level 1 and regenerated through
their documented campaigns; Level 2 does not claim to rerun them.

## Level 3 — full CPU campaigns

The code-to-artifact map and required run roots are in `derived/README.md`.
Long bootstrap and coverage campaigns checkpoint under paths selected by
`M1_ARENA_RUN_ROOT`, `M1_MULTIWAY_RUN_ROOT`, and
`M1_MULTIWAY_COVERAGE_ROOT`. Defaults point to ignored `regenerated/`
directories; high-volume runs should use a fast external work volume.

EXP-105 has 48,000 outer-replicate rows. Its committed closure records every
external shard's SHA-256 and row count, so Level 1 verifies the sealed campaign
without pretending to recompute it.

## Score and model boundary

No detector training is needed. The 21DF analyses consume third-party released
per-trial scores. The ASVspoof 5 extension consumes fixed score shards whose
698 logical identities and hashes are recorded in `audit/asv5/input-manifest.json`.
Those score files are not redistributed.
SpoofCeleb is also license-gated. Its public layer contains aggregate results,
comparisons, hash-bound receipts, EXP-115 bootstrap arrays and nonlicensed analysis code;
it contains no audio, manifest or score table. `audit/PUBLIC-PACKAGING.json` binds the
path-sanitized composite to the exact internal audit-package hash and to
`code/make_public_audit.py`.
