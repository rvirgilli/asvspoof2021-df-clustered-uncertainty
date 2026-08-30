# Standalone recomputation

`recompute.py` is a second implementation written without importing EXP-114,
EXP-115, or campaign analysis code. It independently parses the licensed
manifest and score tables, constructs the two frozen RNG streams, implements
weighted EER, recomputes all 10,000 factor-only draws, and compares its arrays
and complete max-t summaries with the released EXP-115 delivery.

The implementation was written and run after the frozen result. It is a
reproducibility check, not an independent institution or a new confirmation.
Its input hashes and output are recorded in `RESULT.json`; licensed inputs are
not copied here.
