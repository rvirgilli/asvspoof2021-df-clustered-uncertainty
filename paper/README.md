# FIX4 manuscript

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
The FIX4 artifact receipt is `RELEASE-RECEIPT-FIX4-ARTIFACT.json` (pass it with
`--receipt` during this artifact stage). `OBLIGATION-FIX4.json` records the nine
wording-match changes and the forced sampling-sentence checker change.
The inherited PDF is historical, from `6f54787`. The submission stage will pin
this artifact and rebuild it; see `SUBMISSION-VERSION.md`.
Prior receipts and validation directories describe their named historical revisions.
