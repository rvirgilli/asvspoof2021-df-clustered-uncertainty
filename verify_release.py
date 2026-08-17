#!/usr/bin/env python3
"""Verify the public release without consulting private project state."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "MANIFEST.json"
IGNORED_PARTS = {".git", ".venv", "__pycache__", "audit-regenerated", "regenerated", "inputs"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out"}


def release_files() -> set[str]:
    files = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or path == MANIFEST_PATH:
            continue
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_PARTS for part in relative.parts) or path.suffix in IGNORED_SUFFIXES:
            continue
        files.add(relative.as_posix())
    return files


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []
    for name, record in manifest.items():
        path = ROOT / name
        if not path.is_file():
            failures.append(f"missing manifest file: {name}")
            continue
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != record["sha256"] or path.stat().st_size != record["bytes"]:
            failures.append(f"manifest mismatch: {name}")

    actual = release_files()
    failures.extend(f"unbound release file: {name}" for name in sorted(actual - set(manifest)))
    failures.extend(f"manifest-only file: {name}" for name in sorted(set(manifest) - actual))

    machine_roots = ("/" + "home" + "/" + "rv", "~" + "/projects", "icassp" + "-runs")
    internal_tokens = ("gpt" + "-5", "claude" + " code", "code" + "x", "xhigh" + " agent")
    for name in sorted(actual):
        path = ROOT / name
        if path.suffix.lower() in {".pdf", ".png", ".jpg", ".pyc"}:
            continue
        value = path.read_text(encoding="utf-8", errors="ignore")
        if any(token in value for token in machine_roots):
            failures.append(f"machine-specific path: {name}")
        if any(token in value.lower() for token in internal_tokens):
            failures.append(f"internal production reference: {name}")
        if "Anonymous" + " ICASSP" in value:
            failures.append(f"anonymous author placeholder: {name}")

    for command in (
        [sys.executable, "code/check_numbers.py"],
        [sys.executable, "audit/verify_asv5_package.py"],
    ):
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            failures.append(f"command failed: {' '.join(command)}")

    if failures:
        print("FAILED — release repository")
        print("\n".join(f"  - {item}" for item in failures))
        return 1
    print("PASS — release repository verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
