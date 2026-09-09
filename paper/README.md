# Paper source used by the checker

`main.tex`, `refs.bib`, and `figures_m1.py` are the exact source files against
which `code/check_numbers.py` is run. They are versioned here because a checker
cannot substantiate a paper that is absent from the artifact repository.

From the repository root:

```bash
uv run --frozen python paper/figures_m1.py
cd paper && SOURCE_DATE_EPOCH=1788120000 FORCE_SOURCE_DATE=1 \
  latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The first command regenerates both PDFs in `paper/figs/` exclusively from the
committed derived JSON files. The second compiles the exact checked source with the
release timestamp fixed at 2026-08-30 20:00:00 UTC, making the canonical PDF bytes
independent of rebuild time and checkout path.
`verify_release.py` confirms that the PDF has five pages and page 5 contains references
only. `semantic_obligations.json` and `test_semantic_guards.py` make removal of any of
40 load-bearing caveats fail the production checker. Fig. 1 uses matched all-28-pair
simultaneous bands for both the trial-i.i.d. and speaker--attack arms.
