# Audited M1 manuscript

This manuscript measures paired comparison sensitivity. The supplement includes
S4a–S4e, and its three evidence JSONs are byte-identical to the root evidence.
The portable drivers, both replicate archives and input acquisition instructions
are described in [REPRODUCE-DIAGNOSTICS.md](../REPRODUCE-DIAGNOSTICS.md).

From the repository root:

```sh
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python code/verify_release_receipt.py
uv run --frozen python verify_release.py
```

Every registered semantic obligation is deletion-tested. The artifact stage
contains the merged source and an inherited predecessor PDF; the submission stage
updates the artifact locator, retires the withdrawn SNAP reference and rebuilds
the PDF. See [revision details](../REVISION-CHANGES.md). The current payload is
bound by RELEASE-RECEIPT-REVISION-ARTIFACT.json and MANIFEST.json. Earlier receipts and
validation directories are historical records for their named revisions.

The revised source is self-contained; the supplement is additional provenance. The new Monte Carlo checks and independent arithmetic verifier are documented in ../REPRODUCE-DIAGNOSTICS.md.
