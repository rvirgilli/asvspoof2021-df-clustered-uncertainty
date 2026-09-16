# M1 republication 2 — reader verification

The supplied repaired PDF has SHA-256 `59fee3c22a08a7dc627a137c69de639b41579b12d26aa282775d5f31b3a6828b`.
The publication branch is `m1-republished-2-20260915-2245`; the tag is `icassp2027-submission`.
The earlier tag commit was `e7768ffbcb0dfd504b08ebf23483bfd67b9a4397`.

Fetch a fresh verification ref so a stale local tag cannot mask the remote state:

```sh
git fetch --no-tags https://github.com/rvirgilli/asvspoof2021-df-clustered-uncertainty.git refs/tags/icassp2027-submission:refs/verification/m1-republication-2
git rev-parse refs/verification/m1-republication-2
git rev-parse 'refs/verification/m1-republication-2^{}'
git switch --detach 'refs/verification/m1-republication-2^{}'
uv sync --frozen
uv run --frozen python code/verify_release_receipt.py
uv run --frozen python code/check_numbers.py
uv run --frozen python -m unittest -v paper/test_semantic_guards.py
uv run --frozen python verify_release.py
sha256sum ABLATION-RESULTS.json paper/ABLATION-RESULTS.json paper/SUPPLEMENT.md paper/main.pdf
```

Both JSON paths must be reachable and identical. Supplement S4a names the eight
lost separations, the four attack-only overlaps, and the two SSL pairs retained
by speaker-only and joint resampling. It also identifies the extra SSL pair
retained by attack-only. All 28 four-arm indicator rows and bands, the one-factor
laws, position-wise EER, per-replicate threshold refit, B=5000 and seed rule
`SeedSequence(2026081604).spawn(4)` must be present.

The successor receipt binds every payload member except itself and the manifest;
the manifest binds the receipt; the Git commit binds all tracked files. The
predecessor receipts and `release-validation/` remain historical. The external
`REPUBLICATION-2-RECEIPT.md` records fresh exits, computed digests for every member,
the actual tag object and commit, the leased push and HTTPS retrieval results.
Publishing this evidence does not relabel the supplied audit as a new PASS.
