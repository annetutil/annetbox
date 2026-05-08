"""
Generic data-driven integration tests for all Netbox versions.

Discovers test cases from fixtures/{version}/{test_id}/ directories.
Each test case has its own cassette and expected response.
"""
from pathlib import Path

import pytest
import vcr
import yaml

from .helpers import discover_client_class, get_netbox_url

# Test token for integration tests
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_test_cases():
    """Load all test cases by scanning version directories."""
    test_cases = []

    # Scan for version directories (v42, v41, v37, etc.)
    for version_dir in sorted(FIXTURES_DIR.glob("v*")):
        if not version_dir.is_dir():
            continue

        version = version_dir.name

        # Scan for test case directories
        for test_dir in sorted(version_dir.iterdir()):
            if not test_dir.is_dir():
                continue

            test_id = test_dir.name
            cassette_file = test_dir / "cassette.yaml"
            expected_file = test_dir / "expected.yaml"

            if not cassette_file.exists() or not expected_file.exists():
                continue

            # Load test case data (UnsafeLoader preserves types)
            with expected_file.open() as f:
                test_case_data = yaml.load(f, Loader=yaml.UnsafeLoader)  # noqa: S506

            call = test_case_data["call"]

            test_cases.append({
                "test_id": f"{version}/{test_id}",
                "version": version,
                "client_call": call["client_call"],
                "client_call_args": call.get("client_call_args", []),
                "client_call_kwargs": call.get("client_call_kwargs", {}),
                "cassette_dir": str(test_dir),
                "expected_response": test_case_data["output"],
            })

    return test_cases


# Load test cases
test_cases = load_test_cases()
test_ids = [tc["test_id"] for tc in test_cases]


@pytest.mark.parametrize("test_case", test_cases, ids=test_ids)
def test_api_call(test_case):
    """
    Generic test for any Netbox version.

    Dynamically imports the client class, uses the test's cassette,
    calls the method, and validates the response.
    """
    version = test_case["version"]
    client_call = test_case["client_call"]
    call_args = test_case["client_call_args"]
    call_kwargs = test_case["client_call_kwargs"]
    expected_response = test_case["expected_response"]
    cassette_path = Path(test_case["cassette_dir"]) / "cassette.yaml"

    # Dynamically get client class and URL for this version
    client_class = discover_client_class(version)
    netbox_url = get_netbox_url(version)

    # Create VCR instance
    my_vcr = vcr.VCR(
        record_mode="none",
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_headers=[("authorization", "DUMMY")],
        decode_compressed_response=True,
        serializer="yaml",
    )

    # Use the test case's cassette
    with my_vcr.use_cassette(str(cassette_path)):
        # Create client and call method
        client = client_class(url=netbox_url)
        method = getattr(client, client_call)

        # Call with args and kwargs
        actual_result = method(*call_args, **call_kwargs)

    # Compare dataclasses directly (preserves type checking)
    assert actual_result == expected_response, (
        f"Response mismatch for {client_call}\n"
        f"Test: {test_case['test_id']}"
    )
