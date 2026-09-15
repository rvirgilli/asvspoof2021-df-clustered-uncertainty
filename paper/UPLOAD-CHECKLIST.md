# M1 release verification — 15 September 2026

The republication payload includes the supplied PDF identified by the passing
15 September protocol audit, SHA-256 `bd7fa4243879b7eeaaaf96a99cae4c2adb7f823425672c88204cb95b8e271108`.
The author authorized republication at `icassp2027-submission` on the new branch
`m1-republished-20260915-1757`. The historical 14 September commit is `89a17476a8937a6c548eaf0a997dfc4019419660`.

## Verify the fetched artifact

Fetch into a fresh ref so an existing local tag cannot mask the remote value.
These commands operate in a reader's checkout:

```sh
git fetch --no-tags https://github.com/rvirgilli/asvspoof2021-df-clustered-uncertainty.git refs/tags/icassp2027-submission:refs/verification/m1-20260915
git rev-parse refs/verification/m1-20260915
git rev-parse 'refs/verification/m1-20260915^{}'
git switch --detach 'refs/verification/m1-20260915^{}'
uv sync --frozen
uv run --frozen python code/verify_release_receipt.py
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python verify_release.py
sha256sum paper/main.pdf paper/SUPPLEMENT.md
```

The successor receipt binds every payload file except itself and the manifest
to avoid circular digests. `MANIFEST.json` binds all other release files,
including the receipt. The Git commit binds every tracked file, including the
manifest. The release verifier checks membership, digests, sizes, scientific
guards, provenance packages and five-page compliance.

Check S2 for the source-deletion inclusion–exclusion covariance, eigenvalue
clipping, projected contrast standardization, 200,000 draws and 0.95 quantile.
S3 lists the eight point EERs and S4 all 28 paired bands. The main table includes
the same eight primary EERs. S8 records the earlier release as a historical event.

## Record interpretation

`RELEASE-RECEIPT-20260914.json` preserves the predecessor receipt. Its workflow
statements and `release-validation/` outputs describe their original measurement
date. The successor receipt supplies current bindings. The external auditor's
`REPUBLICATION-RECEIPT.md` records fresh verification exits, the actual tag object
and commit, the leased push and HTTPS read-back.

The passing audit authorizes submission of the supplied manuscript as is.
Republication preserves its bytes and adds no experiments.
