# Paper source used by the checker

`main.tex`, `refs.bib`, and `figures_m1.py` are the exact source files against
which `code/check_numbers.py` is run. They are versioned here because a checker
cannot substantiate a paper that is absent from the artifact repository.

From the repository root:

```bash
uv run --frozen python paper/figures_m1.py
cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The first command regenerates both PDFs in `paper/figs/` exclusively from the
committed derived JSON files. The second compiles the exact checked source.
`verify_release.py` confirms that the PDF has five pages and page 5 contains references
only. `semantic_obligations.json` and `test_semantic_guards.py` make removal of any of
26 load-bearing caveats fail the production checker.
