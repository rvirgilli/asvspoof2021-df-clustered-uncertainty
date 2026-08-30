#!/usr/bin/env python3
"""Create a path-sanitized public copy of the composite M1 audit package.

Only absolute local path strings are replaced. Numeric, Boolean and hash fields
are byte-for-byte JSON values from the internal composite package. A deterministic
receipt binds the internal and public files plus this implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable(value: object, trail: tuple[str, ...] = ()) -> object:
    if isinstance(value, dict):
        return {key: portable(item, trail + (str(key),)) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item, trail + (str(index),)) for index, item in enumerate(value)]
    if isinstance(value, str) and (value.startswith("/") or value.startswith("~/")):
        leaf = Path(value).name
        logical = "/".join(trail)
        return f"external-local/{logical}/{leaf}" if leaf else f"external-local/{logical}"
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    source = json.loads(args.input.read_text())
    rendered = json.dumps(portable(source), indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    receipt = {
        "schema": "m1-public-audit-packaging-v1",
        "transformation": "replace absolute local path strings; preserve all other JSON values",
        "source": {"bytes": args.input.stat().st_size, "sha256": sha256(args.input)},
        "public": {"bytes": args.output.stat().st_size, "sha256": sha256(args.output)},
        "implementation": {
            "name": Path(__file__).name,
            "bytes": Path(__file__).stat().st_size,
            "sha256": sha256(Path(__file__)),
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
