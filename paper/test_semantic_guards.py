"""Deletion-mutation tests for M1's load-bearing scientific qualifications.

Every obligation in semantic_obligations.json is removed from a temporary copy
of its declared manuscript or supplement source.  The production checker must reject that copy and name the removed
obligation.  Repository files are never modified.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
CHECKER = Path(os.environ.get("M1_CHECKER_PATH", HERE.parent / "code/check_numbers.py"))
PAPER = Path(os.environ.get("M1_PAPER_ROOT", HERE))
OBLIGATIONS = json.loads((PAPER / "semantic_obligations.json").read_text())["obligations"]
SOURCES = {name: (PAPER / name).read_text() for name in ("main.tex", "SUPPLEMENT.md")}


class SemanticGuardMutationTests(unittest.TestCase):
    def test_every_registered_deletion_fails_its_named_guard(self) -> None:
        for obligation in OBLIGATIONS:
            with self.subTest(obligation=obligation["id"]):
                needle = obligation["match"]
                target = obligation.get("source", "main.tex")
                source = SOURCES[target]
                self.assertEqual(
                    source.count(needle), 1,
                    f"obligation {obligation['id']} must match exactly once",
                )
                mutated = source.replace(needle, "", 1)
                with tempfile.TemporaryDirectory(prefix="m1-semantic-mutation-") as tmp:
                    path = Path(tmp) / target
                    path.write_text(mutated)
                    env = dict(os.environ)
                    env["M1_TEX_PATH" if target == "main.tex" else "M1_SUPPLEMENT_PATH"] = str(path)
                    run = subprocess.run(
                        [sys.executable, str(CHECKER)],
                        cwd=HERE.parent,
                        env=env,
                        capture_output=True,
                        text=True,
                    )
                output = run.stdout + run.stderr
                self.assertNotEqual(run.returncode, 0, output)
                self.assertIn(f"OBLIGATION {obligation['id']}", output)


if __name__ == "__main__":
    unittest.main()
