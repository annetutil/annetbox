#!/usr/bin/env python
"""
Fixture generator for Netbox integration tests.

Discovers version directories and generates test cases with isolated cassettes.
No hardcoded version mappings - everything is discovered dynamically.

Usage:
    # Generate fixtures for all versions
    python -m tests.integration.generate_fixtures

    # Fixtures are saved in tests/integration/fixtures/
"""
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import vcr
import yaml

from .helpers import discover_client_class, get_netbox_url, save_lock_file

# Configuration
BASE_DIR = Path(__file__).parent
FIXTURES_DIR = BASE_DIR / "fixtures"


# Register custom YAML constructor for !from_call
def from_call_constructor(loader, node):
    return loader.construct_mapping(node)


yaml.SafeLoader.add_constructor("!from_call", from_call_constructor)


def extract_value(obj: Any, path: str) -> Any:
    """Extract value from nested object using dot/bracket notation."""
    parts = re.split(r"(\[[^\]]+\])|\.", path)
    parts = [p for p in parts if p and p != "." and p is not None]

    current = obj
    for part in parts:
        if part.startswith("[") and part.endswith("]"):
            key = part[1:-1]
            if key.isdigit():
                current = current[int(key)]
            else:
                current = current[key.strip('\'"')]
        else:
            current = getattr(current, part)

    return current


def resolve_args(args: dict, client: Any) -> dict:
    """Resolve args, handling !from_call directives."""
    resolved = {}

    for key, value in args.items():
        if isinstance(value, dict) and "call" in value and "extract" in value:
            # This is a !from_call directive
            call_method = value["call"]
            call_args = value.get("args", {})
            extract_path = value["extract"]

            # Make the API call
            method = getattr(client, call_method)
            result = method(**call_args)

            # Extract the value
            resolved[key] = extract_value(result, extract_path)
        else:
            resolved[key] = value

    return resolved


def generate_test_case(
    version: str,
    test_def: dict,
    version_dir: Path,
):
    """Generate a single test case with its own cassette."""
    test_id = test_def["id"]
    method = test_def["method"]
    args = test_def["args"]

    # Create test case directory
    test_dir = version_dir / test_id
    test_dir.mkdir(parents=True, exist_ok=True)

    cassette_path = test_dir / "cassette.yaml"
    expected_path = test_dir / "expected.yaml"

    # Delete old cassette to avoid appending
    if cassette_path.exists():
        cassette_path.unlink()

    # Dynamically get client class and URL
    client_class = discover_client_class(version)
    netbox_url = get_netbox_url(version)

    # Filter out volatile headers from responses
    def filter_response_headers(response):
        """Remove headers that change on every request."""
        volatile_headers = {"date", "x-request-id", "set-cookie"}
        response["headers"] = {
            k: v for k, v in response["headers"].items()
            if k.lower() not in volatile_headers
        }
        return response

    # Create VCR for this specific test case
    my_vcr = vcr.VCR(
        cassette_library_dir=str(test_dir),
        record_mode="all",  # Always re-record
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_headers=[("authorization", "DUMMY")],
        decode_compressed_response=True,
        serializer="yaml",
        before_record_response=filter_response_headers,
    )

    with my_vcr.use_cassette("cassette.yaml"):
        client = client_class(url=netbox_url)

        # Resolve args (handle !from_call directives)
        resolved_args = resolve_args(args, client)

        # Call the main method
        method_callable = getattr(client, method)
        result = method_callable(**resolved_args)

        # Save test case with new schema (preserve types in output)
        test_case_data = {
            "definition": {
                "id": test_id,
                "method": method,
                "args": args,  # Original args with !from_call
            },
            "call": {
                "client_call": method,
                "client_call_args": [],
                "client_call_kwargs": resolved_args,
            },
            "output": result,  # Keep as dataclass for type preservation
        }

        with expected_path.open("w") as f:
            f.write("# AUTO-GENERATED - DO NOT EDIT\n")
            f.write("# This file is generated from definitions.yaml\n")
            f.write(
                "# To regenerate: "
                "python -m tests.integration.generate_fixtures\n",
            )
            f.write("\n")
            # Use Dumper to preserve type information in output
            yaml.dump(
                test_case_data,
                f,
                Dumper=yaml.Dumper,
                default_flow_style=False,
                sort_keys=False,
            )



def process_version(
    version: str, version_dir: Path, all_tests: list[dict],
) -> tuple[list[str], list[str]]:
    """Process all tests for a specific version."""
    # Filter tests that include this version
    tests = [
        test for test in all_tests
        if version in test.get("versions", [])
    ]

    if not tests:
        return [], []

    fixtures_ok: list[str] = []
    fixtures_failed: list[str] = []
    for test_def in tests:
        try:
            generate_test_case(version, test_def, version_dir)
            fixtures_ok.append(test_def)
        except Exception:  # noqa: BLE001, PERF203
            traceback.print_exc()
            fixtures_failed.append(test_def)

    # Generate lock file with hashes of all generated files
    save_lock_file(version_dir)
    return fixtures_ok, fixtures_failed


def main():
    # Load shared definitions
    definitions_file = FIXTURES_DIR.parent / "definitions.yaml"
    if not definitions_file.exists():
        print(f"Error: {definitions_file} not found")  # noqa: T201
        return 1

    with definitions_file.open() as f:
        definitions = yaml.safe_load(f)

    all_tests = definitions.get("tests", [])

    # Extract all unique versions from test definitions
    versions = set()
    for test in all_tests:
        versions.update(test.get("versions", []))

    if not versions:
        print("No versions found in definitions.yaml")  # noqa: T201
        return 1

    versions = sorted(versions)

    fails: list[str] = []
    for version in versions:
        version_dir = FIXTURES_DIR / version
        # Create version directory if it doesn't exist
        version_dir.mkdir(parents=True, exist_ok=True)

        print(f"Processing {version}/")  # noqa: T201
        fixtures_ok, fixtures_failed = process_version(
            version,
            version_dir,
            all_tests,
        )
        print(  # noqa: T201
            f"\tOk: {len(fixtures_ok)}",
            f"Failed: {len(fixtures_failed)}",
        )
        fails.extend([
            f"{version}/{x['id']}"
            for x in fixtures_failed
        ])
    if fails:
        print(  # noqa: T201
            "Fails:\n",
            "\n".join([f"\t{x}" for x in fails]),
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
