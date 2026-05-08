"""Helper utilities for integration tests."""
import hashlib
import importlib
from pathlib import Path
from typing import Any

import yaml

# ============================================================================
# Lock file utilities
# ============================================================================

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_data_hash(data: dict) -> str:
    """
    Compute SHA256 hash of lock data (excluding sha256).

    Uses canonical YAML serialization to ensure consistent hashing.
    """
    # Serialize data to canonical YAML (sorted keys, consistent formatting)
    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=True)
    return hashlib.sha256(yaml_str.encode("utf-8")).hexdigest()


def reconstruct_lock_data_for_hash(
    lock_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Reconstruct lock data structure for hash calculation.

    Excludes sha256 field to ensure consistent hash calculation
    across generation and validation.
    """
    return {
        "test_cases": lock_data.get("test_cases", []),
    }


def generate_lock_file(version_dir: Path) -> dict[str, Any]:
    """
    Generate lock file data for all test cases in a version directory.

    Returns lock data structure with sha256 self-hash protection.
    """
    # Collect all test cases and their file hashes
    test_cases_data = []

    for test_dir in sorted(version_dir.iterdir()):
        if not test_dir.is_dir():
            continue

        test_case_id = test_dir.name

        # Scan all files in test case directory
        files_data = [
            {
                "path": file_path.name,
                "sha256": compute_file_hash(file_path),
            }
            for file_path in sorted(test_dir.glob("*.yaml"))
        ]

        if files_data:
            test_cases_data.append({
                "test_case": test_case_id,
                "files": files_data,
            })

    # Build lock data without sha256 first
    lock_data_without_hash = {
        "test_cases": test_cases_data,
    }

    # Calculate sha256 hash
    sha256_hash = compute_data_hash(lock_data_without_hash)

    # Add sha256 to the same data structure
    lock_data = lock_data_without_hash.copy()
    lock_data["sha256"] = sha256_hash

    return lock_data


def save_lock_file(version_dir: Path):
    """Generate and save lock file for a version directory."""
    lock_data = generate_lock_file(version_dir)
    lock_file = version_dir / "lock.yaml"

    with lock_file.open("w") as f:
        f.write("# AUTO-GENERATED - DO NOT EDIT\n")
        f.write("# Contains cryptographic hashes to detect tampering\n")
        f.write(
            "# Regenerate: python -m tests.integration.generate_fixtures\n",
        )
        f.write("\n")
        yaml.dump(lock_data, f, default_flow_style=False, sort_keys=False)


def validate_lock_file(version_dir: Path) -> tuple[bool, list[str]]:
    """
    Validate lock file integrity and test case files.

    Returns (is_valid, list_of_errors)
    """
    lock_file = version_dir / "lock.yaml"

    if not lock_file.exists():
        return False, [f"Lock file missing: {lock_file}"]

    with lock_file.open() as f:
        lock_data = yaml.safe_load(f)

    errors = []

    # Validate sha256 first
    stored_sha256 = lock_data.get("sha256")
    if not stored_sha256:
        errors.append("Lock file missing sha256 field")
        return False, errors

    # Recalculate sha256 (without the sha256 field)
    lock_data_without_hash = reconstruct_lock_data_for_hash(lock_data)
    calculated_sha256 = compute_data_hash(lock_data_without_hash)

    if stored_sha256 != calculated_sha256:
        errors.append(
            "lock.yaml: SHA256 validation failed!\n"
            "  Lock file has been manually modified.\n"
            "  Regenerate: python -m tests.integration.generate_fixtures",
        )
        return False, errors

    # Validate each test case
    test_cases = lock_data.get("test_cases", [])

    for test_case_data in test_cases:
        test_id = test_case_data.get("test_case")
        files = test_case_data.get("files", [])

        test_dir = version_dir / test_id

        for file_data in files:
            file_name = file_data.get("path")
            expected_hash = file_data.get("sha256")
            file_path = test_dir / file_name

            if not file_path.exists():
                errors.append(f"{test_id}/{file_name}: File missing")
                continue

            actual_hash = compute_file_hash(file_path)
            if actual_hash != expected_hash:
                errors.append(
                    f"{test_id}/{file_name}: Hash mismatch!\n"
                    "  File has been manually modified.\n"
                    "  Regenerate: "
                    "python -m tests.integration.generate_fixtures",
                )

    return len(errors) == 0, errors


# ============================================================================
# Version discovery utilities
# ============================================================================

def discover_client_class(version: str):
    """
    Dynamically discover and import client class for a version.

    Example: v42 -> annetbox.v42.client_sync.NetboxV42
    """
    module_name = f"annetbox.{version}.client_sync"
    class_name = f"Netbox{version.upper()}"  # v42 -> NetboxV42

    try:
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        msg = f"Client class not found for {version}: {e}"
        raise ValueError(msg) from e


def get_netbox_url(version: str) -> str:
    """
    Get Netbox URL for a version.

    Derives port from version: v42 -> :8042, v41 -> :8041
    """
    # Extract numeric part: v42 -> 42
    version_num = version.lstrip("v")
    port = f"80{version_num}"
    return f"http://localhost:{port}"


def discover_available_versions() -> list[str]:
    """
    Discover available Netbox versions by scanning annetbox package.

    Returns sorted list like: ['v37', 'v41', 'v42']
    """
    try:
        import annetbox

        annetbox_dir = Path(annetbox.__file__).parent

        versions = []
        for item in annetbox_dir.iterdir():
            if (
                item.is_dir()
                and item.name.startswith("v")
                and item.name[1:].isdigit()
            ):
                # Check if client_sync exists
                client_file = item / "client_sync.py"
                if client_file.exists():
                    versions.append(item.name)

        return sorted(versions)
    except Exception:  # noqa: BLE001
        return []
