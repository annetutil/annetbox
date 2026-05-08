"""
Consistency validation tests for integration test fixtures.

Validates that:
1. Lock file SHA256 hash integrity
2. Test case file hashes match lock file
3. Definitions match generated expected.yaml files
"""
from pathlib import Path
from typing import Any

import pytest
import yaml

from .helpers import (
    compute_data_hash,
    compute_file_hash,
    reconstruct_lock_data_for_hash,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
DEFINITIONS_FILE = Path(__file__).parent / "definitions.yaml"


def from_call_constructor(loader, node):
    """Handle !from_call tags in YAML."""
    return loader.construct_mapping(node)


yaml.SafeLoader.add_constructor("!from_call", from_call_constructor)


def load_definitions_for_version(version: str) -> dict[str, Any]:
    """
    Load test definitions for a specific version from shared definitions.yaml.
    """
    if not DEFINITIONS_FILE.exists():
        return {}

    with DEFINITIONS_FILE.open() as f:
        all_definitions = yaml.safe_load(f)

    # Filter tests by version
    all_tests = all_definitions.get("tests", [])
    version_tests = [
        test for test in all_tests
        if version in test.get("versions", [])
    ]

    return {"tests": version_tests}


def load_consistency_test_cases():
    """
    Load all test cases for consistency validation.

    Creates test cases for:
    - Lock file validation (v42/lock.yaml)
    - Each test case validation (v42/dcim_devices_01)
    """
    test_cases = []

    # Scan for version directories
    for version_dir in sorted(FIXTURES_DIR.glob("v*")):
        if not version_dir.is_dir():
            continue

        version = version_dir.name
        lock_file = version_dir / "lock.yaml"

        # Add lock file test case
        if lock_file.exists():
            test_cases.append({
                "test_id": f"{version}/lock.yaml",
                "type": "lock_file",
                "version": version,
                "version_dir": version_dir,
                "lock_file": lock_file,
            })

        # Load lock file data
        if not lock_file.exists():
            continue

        with lock_file.open() as f:
            lock_data = yaml.safe_load(f)

        # Load definitions for this version
        definitions_data = load_definitions_for_version(version)
        definitions_tests = definitions_data.get("tests", [])
        definitions_map = {test["id"]: test for test in definitions_tests}

        # Add test case validation for each test
        test_cases_data = lock_data.get("test_cases", [])
        for test_case_entry in test_cases_data:
            test_case_id = test_case_entry.get("test_case")
            test_dir = version_dir / test_case_id
            expected_file = test_dir / "expected.yaml"

            if not expected_file.exists():
                continue

            definition = definitions_map.get(test_case_id)

            test_cases.append({
                "test_id": f"{version}/{test_case_id}",
                "type": "test_case",
                "version": version,
                "version_dir": version_dir,
                "test_case_id": test_case_id,
                "test_dir": test_dir,
                "expected_file": expected_file,
                "definition_from_yaml": definition,
                "lock_entry": test_case_entry,
            })

    return test_cases


# Load test cases
test_cases = load_consistency_test_cases()
test_ids = [tc["test_id"] for tc in test_cases]


@pytest.mark.parametrize("test_case", test_cases, ids=test_ids)
def test_consistency(test_case):
    """
    Validate consistency of test fixtures.

    For lock files: Validates SHA256 self-hash
    For test cases: Validates file hashes and definition consistency
    """
    test_type = test_case["type"]

    if test_type == "lock_file":
        # Validate lock file self-hash
        lock_file = test_case["lock_file"]

        with lock_file.open() as f:
            lock_data = yaml.safe_load(f)

        stored_sha256 = lock_data.get("sha256")
        assert stored_sha256 is not None, (
            f"{test_case['test_id']}: Lock file missing sha256 field"
        )

        # Recalculate sha256 (without the sha256 field)
        lock_data_without_hash = reconstruct_lock_data_for_hash(lock_data)
        calculated_sha256 = compute_data_hash(lock_data_without_hash)

        assert stored_sha256 == calculated_sha256, (
            f"{test_case['test_id']}: SHA256 validation failed!\n"
            "  Lock file has been manually modified.\n"
            "  Regenerate: python -m tests.integration.generate_fixtures"
        )

    elif test_type == "test_case":
        # Validate test case files and definition
        test_id = test_case["test_id"]
        test_dir = test_case["test_dir"]
        expected_file = test_case["expected_file"]
        definition_from_yaml = test_case["definition_from_yaml"]
        lock_entry = test_case["lock_entry"]

        # Validate file hashes
        for file_entry in lock_entry.get("files", []):
            file_name = file_entry.get("path")
            expected_hash = file_entry.get("sha256")
            file_path = test_dir / file_name

            assert file_path.exists(), (
                f"{test_id}: File missing: {file_name}"
            )

            actual_hash = compute_file_hash(file_path)
            assert actual_hash == expected_hash, (
                f"{test_id}: {file_name} hash mismatch!\n"
                "  File has been manually modified.\n"
                "  Regenerate: python -m tests.integration.generate_fixtures"
            )

        # Validate definition consistency
        with expected_file.open() as f:
            # Use UnsafeLoader since output contains typed objects
            expected_data = yaml.load(f, Loader=yaml.UnsafeLoader)  # noqa: S506

        stored_definition = expected_data["definition"]

        # Check definition exists in definitions.yaml
        assert definition_from_yaml is not None, (
            f"{test_id}: Test case missing from definitions.yaml\n"
            "Add to tests/integration/definitions.yaml with versions: "
            f"[\"{test_case['version']}\"]"
        )

        # Validate stored definition matches definitions.yaml
        if True:
            # Compare full definition structure (including !from_call)
            expected_def_id = definition_from_yaml.get("id")
            expected_method = definition_from_yaml.get("method")
            expected_args = definition_from_yaml.get("args", {})

            stored_def_id = stored_definition.get("id")
            stored_method = stored_definition.get("method")
            stored_args = stored_definition.get("args", {})

            # Validate ID matches
            assert stored_def_id == expected_def_id, (
                f"{test_id}: Test ID mismatch\n"
                f"  definitions.yaml: {expected_def_id}\n"
                f"  expected.yaml:    {stored_def_id}\n"
                f"Regenerate: python -m tests.integration.generate_fixtures"
            )

            # Validate method matches
            assert stored_method == expected_method, (
                f"{test_id}: Method mismatch\n"
                f"  definitions.yaml: {expected_method}\n"
                f"  expected.yaml:    {stored_method}\n"
                f"Regenerate: python -m tests.integration.generate_fixtures"
            )

            # Validate args match (including !from_call structures)
            assert stored_args == expected_args, (
                f"{test_id}: Args mismatch\n"
                f"  definitions.yaml: {expected_args}\n"
                f"  expected.yaml:    {stored_args}\n"
                "Regenerate: python -m tests.integration.generate_fixtures"
            )
