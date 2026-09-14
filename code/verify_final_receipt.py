"""Check a prepared package or fetched Git commit against a retained M1 receipt.

Only reads bytes. Does not build, stage, commit, update tags or publish.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def binding(data: bytes) -> dict:
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workspace", type=Path, help="Read the prepared replacements in place")
    parser.add_argument("--receipt", type=Path, help="Receipt retained before publication")
    parser.add_argument("--commit", help="Read Git objects at this fetched commit; no checkout needed")
    args = parser.parse_args()
    if args.workspace and args.commit:
        parser.error("--workspace and --commit are mutually exclusive")

    def published(name: str) -> bytes:
        if args.commit:
            return subprocess.check_output([
                "git", "-C", str(args.public_root), "show", f"{args.commit}:{name}"
            ])
        return (args.public_root / name).read_bytes()

    receipt_name = "paper/RELEASE-RECEIPT-FINAL.json"
    actual_receipt = ((args.workspace / "RELEASE-RECEIPT-FINAL.json").read_bytes()
                      if args.workspace else published(receipt_name))
    receipt_bytes = args.receipt.read_bytes() if args.receipt else actual_receipt
    if actual_receipt != receipt_bytes:
        raise ValueError("Published receipt differs from the retained receipt")
    receipt = json.loads(receipt_bytes)
    if receipt["schema"] != "m1-final-upload-receipt-v1":
        raise ValueError("Unsupported receipt schema")

    expected = {}
    for name, item in receipt["release_members"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError(f"Invalid release path: {name}")
        if args.workspace:
            source = item["prepared_source"]
            root = args.workspace if source["root"] == "workspace" else args.public_root
            data = (root / source["path"]).read_bytes()
        else:
            data = published(name)
        observed = binding(data)
        expected[name] = {key: item[key] for key in ("sha256", "bytes")}
        if observed != expected[name]:
            raise ValueError(f"Receipt mismatch: {name}")
    expected[receipt_name] = binding(receipt_bytes)
    manifest_bytes = ((args.workspace / "release-prep/MANIFEST.json").read_bytes()
                      if args.workspace else published("MANIFEST.json"))
    if json.loads(manifest_bytes) != expected:
        raise ValueError("Manifest differs from the complete receipt member set plus receipt")
    if args.commit:
        names = set(subprocess.check_output([
            "git", "-C", str(args.public_root), "ls-tree", "-r", "--name-only", args.commit
        ], text=True).splitlines())
        if names != set(expected) | {"MANIFEST.json"}:
            raise ValueError("Commit contains missing or additional files outside the manifest")
    print(f"PASS — {len(receipt['release_members'])} payload members match the receipt; "
          f"manifest binds {len(expected)} members including the receipt.")
    print(f"Receipt SHA-256: {binding(receipt_bytes)['sha256']}")
    print(f"Manifest SHA-256: {binding(manifest_bytes)['sha256']}")
    print("Content consistency only; no new scientific, exact-PDF or publication attestation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
