#!/usr/bin/env python3
"""Verify the public release without consulting private project state."""

from __future__ import annotations

import hashlib
import json
import shutil
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
    for name in sorted(actual):
        path = ROOT / name
        if path.suffix.lower() in {".pdf", ".png", ".jpg", ".pyc"}:
            continue
        value = path.read_text(encoding="utf-8", errors="ignore")
        if any(token in value for token in machine_roots):
            failures.append(f"machine-specific path: {name}")
        if "Anonymous" + " ICASSP" in value:
            failures.append(f"anonymous author placeholder: {name}")

    for command in (
        [sys.executable, "code/check_numbers.py"],
        [sys.executable, "-m", "unittest", "-v", "paper/test_semantic_guards.py"],
        [sys.executable, "audit/verify_asv5_package.py"],
    ):
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            failures.append(f"command failed: {' '.join(command)}")

    if not shutil.which("pdfinfo") or not shutil.which("pdftotext"):
        failures.append("pdfinfo/pdftotext unavailable for the page-compliance gate")
    else:
        info = subprocess.run(
            ["pdfinfo", "paper/main.pdf"], cwd=ROOT, capture_output=True, text=True
        )
        if info.returncode or "Pages:           5" not in info.stdout:
            failures.append("paper/main.pdf is not exactly five pages")
        page5 = subprocess.run(
            ["pdftotext", "-f", "5", "-l", "5", "-layout", "paper/main.pdf", "-"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if page5.returncode:
            failures.append("could not extract page 5")
        elif any(heading in page5.stdout.upper() for heading in (
                "DISCUSSION", "CONCLUSION", "EXPERIMENTS", "METHOD")):
            failures.append("page 5 contains technical-section content")
        elif not any(f"[{index}]" in page5.stdout for index in range(1, 31)):
            failures.append("page 5 does not contain reference entries")

    if failures:
        print("FAILED — release repository")
        print("\n".join(f"  - {item}" for item in failures))
        return 1
    print("PASS — release repository verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
