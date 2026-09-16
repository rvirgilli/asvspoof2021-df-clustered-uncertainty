# M1 manuscript package — republication 2

`main.pdf` is byte-identical to the supplied repaired revision, SHA-256
`59fee3c22a08a7dc627a137c69de639b41579b12d26aa282775d5f31b3a6828b`. `main.tex`, `refs.bib` and `semantic_obligations.json`
also preserve the supplied bytes. The PDF and figures were not rebuilt.

[SUPPLEMENT.md](SUPPLEMENT.md#s4a-primary-21df-factor-ablation) and
[ABLATION-RESULTS.json](ABLATION-RESULTS.json) publish the primary-21DF ablation
missing from the earlier tag. S4a contains all 28 pair indicators and bands for
each arm; the eight trial-to-joint losses and the four attack-only overlaps;
retained SSL pairs; the estimator, threshold refits, B and seed-stream mapping.
Its complete S4a text is preserved from the supplied supplement. The header
identifies the earlier release by immutable commit to avoid ambiguity after
moving the tag. Local paths in the JSON are descriptive external-input locators;
its scientific values and input hashes are unchanged. Those inputs and the
historical ablation replicate archive are not redistributed by this release.

The protocol audit supplied for this revision recorded FAIL, with one evidence
availability blocker (F1); F2–F6 were wording findings repaired in the supplied
revision. Publishing the missing evidence addresses F1. This package does not
claim a newly performed scientific audit or new bootstrap computation.

From the repository root:

```sh
uv sync --frozen
uv run --frozen python code/verify_release_receipt.py
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python verify_release.py
```

The public figure generator and semantic mutation-test adapter are unchanged.
The number checker retains its public adapters and incorporates the supplied
ablation and wording guards. There are 51 semantic obligations.
`RELEASE-RECEIPT-FINAL.json` is current; `RELEASE-RECEIPT-20260915-1757.json`,
`RELEASE-RECEIPT-20260914.json` and `release-validation/` are historical records.
The external `REPUBLICATION-2-RECEIPT.md` records the actual verification chain,
leased publication and HTTPS read-back. See `UPLOAD-CHECKLIST.md` for fetch commands.
