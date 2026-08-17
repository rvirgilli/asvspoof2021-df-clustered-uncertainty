# Portable ASVspoof 5 fixed-family bundle

This directory contains a path-sanitized result, run contract, 698-record input
manifest, exact analysis/core source bytes, tests, and the two governing
amendments. No score arrays, checkpoints, protocol rows, or model weights are
redistributed.

From the repository root:

```bash
uv run --frozen python audit/verify_asv5_package.py
```

The verifier authenticates the portable records, checks the logical input
identities and hashes, and binds every released source file to the hash sealed
in the run contract. It verifies the fixed-roster descriptive result; it does
not claim population inference or rerun scoring.
