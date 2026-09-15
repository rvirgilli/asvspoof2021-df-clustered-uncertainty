# M1 manuscript package — 15 September 2026

`main.pdf` is byte-identical to the supplied manuscript identified by the passing
15 September protocol audit: SHA-256 `bd7fa4243879b7eeaaaf96a99cae4c2adb7f823425672c88204cb95b8e271108`.
`RELEASE-RECEIPT-FINAL.json` binds the current payload and every changed historical
binding. `UPLOAD-CHECKLIST.md` gives reader verification commands.

Table 1 adds eight primary 21DF point EERs; the abstract is shorter and the first
detector roster declares SLS. Supplement S2 specifies source-deletion Gaussian
calibration, S3 lists point EERs and aliases, and S8 records the 14 September
publication as a historical event. The supplied manuscript source, PDF and
supplement are preserved exactly. No manuscript or figure was rebuilt.

The public figure generator and semantic mutation-test adapter are unchanged
from the 14 September remote baseline. The public number checker retains its
repository adapters with the finding 1 and 2 guard edits. All 46 semantic
obligations remain registered. The forest figure shows six within-SSL pairs from
the full 28-pair family; the unused floor figure and generator inputs are retained.

From the repository root:

```sh
uv sync --frozen
uv run --frozen python code/verify_release_receipt.py
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python verify_release.py
```

`RELEASE-RECEIPT-20260914.json` and `release-validation/` preserve historical
records for their original bytes and dates. `code/verify_final_receipt.py` is
retained as the verifier for that historical schema and its original commits;
use `code/verify_release_receipt.py` for this successor receipt.
Fresh verification and publication evidence are in the auditor's external
`REPUBLICATION-RECEIPT.md`.

An optional rebuild runs `uv run --frozen python paper/figures_m1.py`, then
`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` in `paper/`.
A rebuilt PDF can have different bytes and needs a new content binding.
