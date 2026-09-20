# FIX5 manuscript

The PDF retains the primary 28-pair table, three speaker-deletion rows, four-arm
counts, mean/sign diagnostics and limited SpoofCeleb contrast. The composition
control is withdrawn and explicitly archived in supplement S6/S14.

```sh
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python code/verify_release_receipt.py --receipt paper/RELEASE-RECEIPT-FIX5-FINAL.json
uv run --frozen python verify_release.py
```

All 303 inherited semantic obligations remain; seven audit-repair obligations
are added. `OBLIGATION-FIX5.json` records every forced wording or location change.
See `SUBMISSION-VERSION.md` for the artifact pin. Historical receipts, evidence
and validation directories describe their named revisions.
