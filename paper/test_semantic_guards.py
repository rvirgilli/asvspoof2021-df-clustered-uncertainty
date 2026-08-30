"""Deletion-mutation tests for M1's load-bearing scientific qualifications.

Every obligation in semantic_obligations.json is removed from a temporary copy
of main.tex.  The production checker must reject that copy and name the removed
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
CHECKER = HERE.parent / "code/check_numbers.py"
OBLIGATIONS = json.loads((HERE / "semantic_obligations.json").read_text())["obligations"]
SOURCE = (HERE / "main.tex").read_text()


class SemanticGuardMutationTests(unittest.TestCase):
    def test_every_registered_deletion_fails_its_named_guard(self) -> None:
        for obligation in OBLIGATIONS:
            with self.subTest(obligation=obligation["id"]):
                needle = obligation["match"]
                self.assertEqual(
                    SOURCE.count(needle), 1,
                    f"obligation {obligation['id']} must match exactly once",
                )
                mutated = SOURCE.replace(needle, "", 1)
                with tempfile.TemporaryDirectory(prefix="m1-semantic-mutation-") as tmp:
                    path = Path(tmp) / "main.tex"
                    path.write_text(mutated)
                    env = dict(os.environ)
                    env["M1_TEX_PATH"] = str(path)
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
