# Concentration rewrite manuscript

The PDF prints all 28 primary point gaps and trial/joint bands, the three-row
speaker-deletion table, four-arm counts, mean/sign diagnostics, the composition
control band and the SpoofCeleb factor contrast. The full technical record remains
in the byte-identical root and paper supplements.

From the repository root:

```sh
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python code/verify_release_receipt.py
uv run --frozen python verify_release.py
```

All 303 semantic obligations are deletion-tested; all 138 predecessor obligations
and all 97 originals are retained. `OBLIGATION-REWRITE.json` records each relocation
and the manuscript edit forcing each checker change.
The current submission receipt is `RELEASE-RECEIPT-REWRITE-FINAL.json`.
The submission cites artifact `260e1e15e1ac6f79d4a7b083f5a51716dc8d7516` and rebuilds the PDF.
The artifact commit retains the predecessor PDF as identified history. Prior receipts and validation directories describe their
named historical revisions. See `../REWRITE-CHANGES.md`.
