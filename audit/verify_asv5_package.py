"""Verify the portable ASVspoof 5 fixed-family audit bundle (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
ASV5 = HERE / "asv5"


def load(path: Path):
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, str):
        yield value


audit = load(HERE / "audit.json")["asv5_descriptive_replication"]
result_record = load(ASV5 / "result.portable.json")
contract_record = load(ASV5 / "run-contract.portable.json")
manifest = load(ASV5 / "input-manifest.json")

source_bindings = {
    "analyze_asv5_descriptive.py": "analyzer",
    "asv5_descriptive_core.py": "core",
    "test_analyze_asv5_descriptive.py": "analyzer_tests",
    "test_asv5_descriptive_core.py": "core_tests",
    "AMENDMENT-5-fixed-roster-descriptive.md": "amendment5",
    "AMENDMENT-6-descriptive-executor.md": "amendment6",
    "STATIC-AUDIT-descriptive-executor.md": "static_audit",
}
for filename, contract_key in source_bindings.items():
    expected = contract_record["payload"]["inputs"]["artifacts"][contract_key]["sha256"]
    assert sha256(ASV5 / "source" / filename) == expected, f"source hash mismatch: {filename}"
sealed_reference = ASV5 / "EXP-101-m1-campaign/exp101_matched_iid.py"
expected_reference = contract_record["payload"]["inputs"]["artifacts"]["sealed_reference"]["sha256"]
assert sha256(sealed_reference) == expected_reference, "sealed reference hash mismatch"

for name, expected in audit["portable_files"].items():
    path = ASV5 / name
    assert path.is_file(), f"missing portable file: {name}"
    assert sha256(path) == expected, f"portable hash mismatch: {name}"

assert result_record["sealed_source_sha256"] == audit["result_sha256"]
assert contract_record["sealed_source_sha256"] == audit["run_contract_sha256"]
assert manifest["source_run_contract_sha256"] == audit["run_contract_sha256"]
assert result_record["payload"] == audit["result"]
assert contract_record["payload"]["structure"] == audit["run_contract_structure"]

assert manifest["n_records"] == len(manifest["records"]) == 698
logical_ids = [row["logical_id"] for row in manifest["records"]]
assert len(set(logical_ids)) == len(logical_ids)
for row in manifest["records"]:
    assert set(row) == {"logical_id", "basename", "sha256", "size"}
    assert re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
    assert isinstance(row["size"], int) and row["size"] >= 0

for value in strings({"result": result_record, "contract": contract_record,
                      "manifest": manifest}):
    assert not value.startswith(("/home/", "/mnt/", "/media/")), value

result = result_record["payload"]
assert result["scientific_role"] == (
    "fixed-roster descriptive perturbation sensitivity; not population inference"
)
assert not any(result["interpretation_boundary"].values())
assert result["run_contract"]["path"] == "run-contract.portable.json"
assert result["comparison"]["registered_descriptive_summaries"] == {
    "A_iid_exclusion_absent_under_speaker_attack": True,
    "B_median_width_ratio_at_least_2": True,
    "n_true": 2,
}
assert audit["independent_execution_audit"]["verdict"] == "PASS"
assert audit["independent_execution_audit"]["inputs_rehashed"] == 698
assert audit["independent_execution_audit"]["input_divergences"] == 0
assert "no historical scoring-run sidecars" in audit["legacy_score_provenance"]

print("PASS — portable ASV5 package, source bytes, 698-input manifest, hashes and boundaries verify")
