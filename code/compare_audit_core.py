#!/usr/bin/env python3
"""Compare a regenerated raw-score audit core with the canonical composite.

The public ``audit/audit.json`` contains this core and five later closures with
their own artifact verifiers.  This checker prevents either layer from being
misrepresented as the other while still requiring exact equality for every
core value.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CORE_KEYS = (
    "provenance",
    "intersection",
    "cluster_size",
    "eer_rule",
    "incidence",
    "contrasts",
    "seeds",
    "multiway_intersection",
    "floor_scope",
    "coverage_mc",
    "variant_by_pair",
    "width_ratios",
    "finite_A_marginal_component_ratios",
    "finite_A_component_count",
    "source_corpus_test",
    "leave_one_corpus_out",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--regenerated",
        type=Path,
        default=ROOT / "audit-regenerated" / "audit-core.json",
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=ROOT / "audit" / "audit.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    regenerated = json.loads(args.regenerated.read_text(encoding="utf-8"))
    canonical = json.loads(args.canonical.read_text(encoding="utf-8"))
    failures: list[str] = []

    if tuple(regenerated) != CORE_KEYS:
        failures.append(
            "regenerated key order/set differs from the declared raw-score core"
        )
    missing = [key for key in CORE_KEYS if key not in canonical]
    if missing:
        failures.append(f"canonical package lacks core keys: {missing}")
    for key in CORE_KEYS:
        if key in regenerated and key in canonical and regenerated[key] != canonical[key]:
            failures.append(f"core payload differs: {key}")

    if failures:
        print("FAIL — regenerated audit core")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"PASS — {len(CORE_KEYS)} raw-score audit blocks match the composite package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
