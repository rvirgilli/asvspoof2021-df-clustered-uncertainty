# Final M1 package — prepared 14 September 2026

`RELEASE-RECEIPT-FINAL.json` binds the intended source, supplied built PDF,
repaired supplement, figure, generator, guards and obligation manifest.
`UPLOAD-CHECKLIST.md` records publication status and verification instructions.
The current package has no inherited exact-PDF audit, deterministic-build or
whole-release PASS from September 9 or the September 13 sentence extension.

The forest figure displays the six within-SSL pairs from the full 28-pair
simultaneous family. `figures_m1.py` reads the committed `derived/` aggregates;
its only change from the bound author-workspace generator is that input path.
It also retains the unused `floor.pdf` generator and its two derived inputs.
The guard checks all 46 obligations; its mutation suite deletes each in turn.

From the repository root, verify the prepared bytes before regenerating anything:

```sh
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python verify_release.py
```

For an optional rebuild, `uv run --frozen python paper/figures_m1.py` regenerates
both figures. Compile in `paper/` with `latexmk -pdf -interaction=nonstopmode
-halt-on-error main.tex`. Such a rebuild can change PDF bytes. It does not replace
the supplied receipt-bound upload PDF without a new binding and explicit scope
confirmation. No manuscript or figure rebuild was performed for this receipt.
