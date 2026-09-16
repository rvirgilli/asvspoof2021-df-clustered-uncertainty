# M1 impact revision

This manuscript measures paired comparison sensitivity. Table 1 contains the two-roster
four-arm comparison; Table 2 separates mean displacement, sign frequency and band exclusion.
The supplement documents all newly cited evidence at S4a–S4e. Three files under `evidence/`
are byte-identical to the root copies, so the supplement's Markdown links resolve here too.
The raw evidence contains historical input locators; input acquisition instructions remain
in `../data/README.md`. Diagnostic drivers preserve the original execution code and hashes;
they require the historical inputs and path mapping rather than providing a one-command
raw-score rerun in this aggregate release.

From the repository root:

```sh
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python verify_release.py
```

The semantic suite retains the original 51 obligations and adds 25, all deletion-tested.
Prior RELEASE-RECEIPT files and release-validation outputs are historical records.
The current release is authenticated by MANIFEST.json and its immutable Git commit.
