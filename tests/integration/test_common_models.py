"""
Tests for the common data model made from the recorded API responses.

The input is the recorded response of expected.yaml. The output of the
converters of annetbox.<version>.views is compared with the golden
common.yaml generated along with the fixtures.
"""
import dataclasses
from pathlib import Path
from typing import Any

import pytest
import yaml

from annetbox.common import models as common
from .helpers import COMMON_CONVERTERS, convert_to_common

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REGENERATE = "Regenerate: python -m tests.integration.generate_fixtures"

# common class of the objects made by a converter
COMMON_CLASSES = {
    "convert_ip_addresses": common.IpAddress,
    "convert_prefixes": common.Prefix,
    "convert_device": common.NetboxDevice,
    "convert_interfaces": common.Interface,
}

# Attributes that are not common fields but mean the same in every version,
# for example 4.2 has `scope` and `scope_type` instead of `site`.
SAME_MEANING = {
    "convert_prefixes": ["site"],
}

# The attribute that finds the same object in the data of every NetBox.
IDENTITY = {
    "convert_ip_addresses": "address",
    "convert_prefixes": "prefix",
    "convert_device": "name",
    "convert_interfaces": "name",
}

# Different in every NetBox instance, not a difference between versions.
INSTANCE_SPECIFIC = {"url"}


def load_yaml(path: Path) -> Any:
    with path.open() as f:
        # UnsafeLoader since the output contains typed objects
        return yaml.load(f, Loader=yaml.UnsafeLoader)  # noqa: S506


def load_cases() -> list[dict[str, Any]]:
    cases = []
    for version_dir in sorted(FIXTURES_DIR.glob("v*")):
        test_dirs = (p for p in version_dir.iterdir() if p.is_dir())
        for test_dir in sorted(test_dirs):
            expected_file = test_dir / "expected.yaml"
            if not expected_file.exists():
                continue
            method = load_yaml(expected_file)["call"]["client_call"]
            if method not in COMMON_CONVERTERS:
                continue
            cases.append({
                "test_id": f"{version_dir.name}/{test_dir.name}",
                "version": version_dir.name,
                "case": test_dir.name,
                "method": method,
                "test_dir": test_dir,
            })
    return cases


cases = load_cases()
case_ids = [c["test_id"] for c in cases]


@pytest.mark.parametrize("case", cases, ids=case_ids)
def test_common_golden(case):
    test_id = case["test_id"]
    golden_file = case["test_dir"] / "common.yaml"
    assert golden_file.exists(), (
        f"{test_id}: common.yaml is missing\n{REGENERATE}"
    )

    recorded = load_yaml(case["test_dir"] / "expected.yaml")["output"]
    actual = convert_to_common(case["version"], case["method"], recorded)

    assert actual == load_yaml(golden_file)["output"], (
        f"{test_id}: the common data model differs from common.yaml\n"
        f"{REGENERATE}"
    )


def as_list(output: Any) -> list[Any]:
    return output if isinstance(output, list) else [output]


def common_fields(obj: Any) -> list[str]:
    """The fields that the common class of the object defines."""
    for cls in type(obj).__mro__:
        if cls.__module__ == common.__name__ and dataclasses.is_dataclass(cls):
            names = [f.name for f in dataclasses.fields(cls)]
            return [n for n in names if n not in INSTANCE_SPECIFIC]
    return [f.name for f in dataclasses.fields(obj)]


def plain(obj: Any) -> Any:
    """Plain representation of an object, without version specific details."""
    if dataclasses.is_dataclass(obj):
        skip = set()
        if isinstance(obj, common.Vrf):
            skip.add("description")  # there is no VRF description in 3.7
        return {
            name: plain(getattr(obj, name))
            for name in common_fields(obj)
            if name not in skip
        }
    if isinstance(obj, list):
        return [plain(o) for o in obj]
    return obj


def common_view(obj: Any, converter: str) -> dict[str, Any]:
    """
    The fields of the common class and the attributes that mean the same
    in every version.
    """
    names = [
        f.name
        for f in dataclasses.fields(COMMON_CLASSES[converter])
        if f.name not in INSTANCE_SPECIFIC
    ]
    names += SAME_MEANING.get(converter, [])
    return {name: plain(getattr(obj, name)) for name in names}


# These record the first object of a list, which is not the same object
# in the demo data of every NetBox.
NOT_COMPARABLE = {"dcim_device_01"}


def cross_version_cases() -> list[str]:
    versions = {c["version"] for c in cases}
    by_case: dict[str, set[str]] = {}
    for c in cases:
        by_case.setdefault(c["case"], set()).add(c["version"])
    return sorted(
        name
        for name, found in by_case.items()
        if found == versions and name not in NOT_COMPARABLE
    )


@pytest.mark.parametrize("case_name", cross_version_cases())
def test_common_is_the_same_in_all_versions(case_name):
    """
    The same data of NetBox 3.7, 4.1 and 4.2 gives the same common data model.

    It converts the recorded responses itself, so it does not depend on the
    goldens.
    """
    views = {}
    for c in cases:
        if c["case"] != case_name:
            continue
        converter = COMMON_CONVERTERS[c["method"]]
        recorded = load_yaml(c["test_dir"] / "expected.yaml")["output"]
        converted = as_list(
            convert_to_common(c["version"], c["method"], recorded),
        )
        views[c["version"]] = {
            (o.id, getattr(o, IDENTITY[converter])): common_view(o, converter)
            for o in converted
        }

    versions = sorted(views)
    first = versions[0]
    # the demo data of the versions is not exactly the same
    keys = set.intersection(*(set(v) for v in views.values()))
    assert keys, f"{case_name}: no object is in every version"
    for version in versions[1:]:
        for key in sorted(keys):
            assert views[version][key] == views[first][key], (
                f"{case_name}: {key} of {version} differs from {first}"
            )
