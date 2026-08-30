# Amendment 1 — post-run receipt verifier

Added after the frozen EXP-115 analysis completed. The speaker-only and
attack-only outcomes were known when this amendment was written.

The preregistration required changed bootstrap arrays to fail receipt
verification. The frozen analyzer emitted hash bindings but did not include a
consumer that exercised them. This was an operational omission, not a change
to the estimand, RNG streams, bootstrap arrays, summaries, or reading rule.

`verify_receipt.py` now consumes the existing receipt and fails if any frozen
source, result, bootstrap array, EXP-114 result binding, manifest binding, or
score binding differs. It also checks array shape/dtype and the hashes recorded
inside `RESULTS.json`. `test_verify_receipt.py` injects mutations into a frozen
source, each bootstrap array, and the result while reusing the stale receipt;
all must reach the intended failure branch.

The original analysis remains pinned to commit
`49b9057b7edba43c3914897d31fdb7917737c379`. This amendment cannot improve or
change its scientific outcome.
