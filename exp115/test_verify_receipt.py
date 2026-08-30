#!/usr/bin/env python3

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "exp115_verify_receipt", HERE / "verify_receipt.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ReceiptTests(unittest.TestCase):
    @staticmethod
    def copy_delivery(destination: Path) -> None:
        names = {
            "FREEZE.sha256", "RESULTS.json", "RUN-RECEIPT.json",
            "SPEAKER-ONLY-BOOTSTRAP.npy", "ATTACK-ONLY-BOOTSTRAP.npy",
        }
        for raw in (HERE / "FREEZE.sha256").read_text().splitlines():
            _, name = raw.split("  ", 1)
            names.add(name)
        for name in names:
            shutil.copy2(HERE / name, destination / name)

    def test_current_delivery_passes(self):
        result = MODULE.verify_artifacts(HERE)
        self.assertEqual(result["arm_speaker_only"]["simultaneous_excluding_zero"], 5)
        self.assertEqual(result["arm_attack_only"]["simultaneous_excluding_zero"], 3)

    def test_stale_receipt_rejects_each_changed_array(self):
        for name in MODULE.ARRAYS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_delivery(root)
                path = root / name
                payload = bytearray(path.read_bytes())
                payload[-1] ^= 1
                path.write_bytes(payload)
                with self.assertRaisesRegex(ValueError, "receipt binding mismatch"):
                    MODULE.verify_artifacts(root)

    def test_stale_receipt_rejects_changed_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_delivery(root)
            path = root / "RESULTS.json"
            path.write_text(path.read_text().replace('"simultaneous_excluding_zero": 5', '"simultaneous_excluding_zero": 4', 1))
            with self.assertRaisesRegex(ValueError, "receipt binding mismatch"):
                MODULE.verify_artifacts(root)

    def test_frozen_source_mutation_fails_before_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_delivery(root)
            path = root / "analyze.py"
            path.write_text(path.read_text() + "# changed\n")
            with self.assertRaisesRegex(ValueError, "frozen file analyze.py hash mismatch"):
                MODULE.verify_artifacts(root)


if __name__ == "__main__":
    unittest.main()
