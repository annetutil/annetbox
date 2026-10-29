import dataclasses
from importlib import import_module
from ipaddress import ip_network
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from annetbox.common.loader import NetboxLoader
from .test_views import VERSIONS, Version

FIXTURES = Path(__file__).parent.parent / "integration" / "fixtures"


def recorded(version: str, case: str) -> list:
    """The results recorded for the integration tests."""
    path = FIXTURES / version / case / "expected.yaml"
    with path.open() as f:
        # UnsafeLoader since the output contains typed objects
        output = yaml.load(f, Loader=yaml.UnsafeLoader)["output"]  # noqa: S506
    return output.results


def paged(results: list) -> SimpleNamespace:
    return SimpleNamespace(results=results)


class FakeClient:
    """The part of a NetBox client that the loader calls."""

    def __init__(
        self, devices, interfaces, ips, prefixes, assignments, groups,
    ):
        self.devices = devices
        self.interfaces = interfaces
        self.ips = ips
        self.prefixes = prefixes
        self.assignments = assignments
        self.groups = groups

    def dcim_all_devices_brief(self, **query):
        return paged(self.devices)

    def dcim_all_devices(self, **query):
        return paged(self.devices)

    def dcim_device(self, device_id):
        return next(d for d in self.devices if d.id == device_id)

    def dcim_all_interfaces(self, device_id=None, id=None):
        return paged([
            i
            for i in self.interfaces
            if i.device.id in (device_id or []) or i.id in (id or [])
        ])

    def ipam_all_ip_addresses(self, interface_id):
        return paged([
            ip for ip in self.ips if ip.assigned_object_id in interface_id
        ])

    def ipam_all_prefixes(self, prefix):
        return paged([p for p in self.prefixes if p.prefix in prefix])

    def ipam_all_fhrp_group_assignments_by_interface(self, interface_id):
        return paged([
            a for a in self.assignments if a.interface_id in interface_id
        ])

    def ipam_all_fhrp_groups_by_id(self, id):
        return paged([g for g in self.groups if g.id in id])


@pytest.fixture(params=VERSIONS)
def version(request) -> Version:
    return Version(request.param)


def make_loader(version: Version, **recorded_data) -> NetboxLoader:
    data = {
        "devices": recorded(version.name, "dcim_all_devices_01"),
        "interfaces": recorded(version.name, "dcim_all_interfaces_01"),
        "ips": [],
        "prefixes": [],
        "assignments": [],
        "groups": [],
    }
    data.update(recorded_data)
    views = version.views
    return NetboxLoader(
        FakeClient(**data),
        convert_device=views.convert_device,
        convert_interfaces=views.convert_interfaces,
        convert_ip_addresses=views.convert_ip_addresses,
        convert_prefixes=views.convert_prefixes,
        convert_fhrp_group_assignments=views.convert_fhrp_group_assignments,
        convert_fhrp_groups=views.convert_fhrp_groups,
    )


def test_version_loader_has_the_converters_of_the_version(version):
    module = import_module(f"annetbox.{version.name}.loader")
    loader = getattr(module, f"NetboxLoaderV{version.name[1:]}")(
        "http://localhost",
    )
    assert loader.convert_device is version.views.convert_device
    assert loader.convert_interfaces is version.views.convert_interfaces
    assert type(loader.client).__name__ == f"Netbox{version.name.upper()}"


def test_list_and_get_devices(version):
    loader = make_loader(version)
    devices = loader.list_devices({})
    assert [d.id for d in devices] == [
        d.id for d in recorded(version.name, "dcim_all_devices_01")
    ]
    assert all(d.interfaces == [] for d in devices)
    assert loader.get_device(devices[0].id).name == devices[0].name
    assert loader.list_fqdns() == [d.name for d in devices]


def test_fill_interfaces(version):
    loader = make_loader(version)
    devices = loader.list_devices({})
    with_interfaces = {i.device.id for i in loader.client.interfaces}
    selected = [d for d in devices if d.id in with_interfaces][:3]
    assert selected

    loader.fill_interfaces(selected)

    for device in selected:
        expected = [
            i for i in loader.client.interfaces if i.device.id == device.id
        ]
        names = [i.name for i in expected]
        assert [i.name for i in device.interfaces] == names
        assert type(device.interfaces[0]).__name__ == (
            f"InterfaceV{version.name[1:]}"
        )


def test_fill_addresses_prefixes_and_groups(version):
    interface = recorded(version.name, "dcim_all_interfaces_01")[0]
    device = next(
        d
        for d in recorded(version.name, "dcim_all_devices_01")
        if d.id == interface.device.id
    )
    prefix = next(
        p
        for p in recorded(version.name, "ipam_all_prefixes_01")
        if ip_network(p.prefix).version == 4
        and ip_network(p.prefix).prefixlen < 30
    )
    network = ip_network(prefix.prefix)
    address = f"{next(network.hosts())}/{network.prefixlen}"
    ip = dataclasses.replace(
        recorded(version.name, "ipam_all_ip_addresses_01")[0],
        address=address,
        assigned_object_id=interface.id,
    )
    assignment = dataclasses.replace(
        version.fhrp_assignment(), interface_id=interface.id,
    )
    group = dataclasses.replace(version.fhrp_group(), id=assignment.group.id)
    loader = make_loader(
        version,
        devices=[device],
        interfaces=[
            dataclasses.replace(
                interface, count_ipaddresses=1, count_fhrp_groups=1,
            ),
        ],
        ips=[ip],
        prefixes=[prefix],
        assignments=[assignment],
        groups=[group],
    )
    (loaded_device,) = loader.list_devices({})

    loader.fill_interfaces([loaded_device])

    (converted,) = loaded_device.interfaces
    (loaded_ip,) = converted.ip_addresses
    assert loaded_ip.address == address
    assert loaded_ip.prefix is not None
    assert loaded_ip.prefix.prefix == prefix.prefix
    (loaded_assignment,) = converted.fhrp_groups
    assert loaded_assignment.group.group_id == group.group_id


# the methods of the adapter of annet and the methods of the client they call
LEGACY_METHODS = {
    "get_site": ("dcim_site", False),
    "list_sites": ("dcim_all_sites", True),
    "get_site_group": ("dcim_site_group", False),
    "list_site_groups": ("dcim_all_site_groups", True),
    "get_location": ("dcim_location", False),
    "list_locations": ("dcim_all_locations", True),
    "get_region": ("dcim_region", False),
    "list_regions": ("dcim_all_regions", True),
    "get_tenant": ("tenancy_tenant", False),
    "list_tenants": ("tenancy_all_tenants", True),
    "get_tenant_group": ("tenancy_tenant_group", False),
    "list_tenant_groups": ("tenancy_all_tenant_groups", True),
    "list_all_vrfs": ("ipam_all_vrfs", True),
    "list_all_vlans": ("ipam_all_vlans", True),
    "get_circuit": ("circuit", False),
    "list_circuits": ("circuits_all", True),
    "trace_interface": ("dcim_interface_trace", False),
}


@pytest.mark.parametrize("method", LEGACY_METHODS)
def test_legacy_methods_call_the_client(version, method):
    client_method, paged_result = LEGACY_METHODS[method]
    calls = []

    def record(*args, **kwargs):
        calls.append((args, kwargs))
        return paged(["result"]) if paged_result else "result"

    loader = make_loader(version)
    setattr(loader.client, client_method, record)
    arguments = ({"site": ["a"]},) if method == "list_circuits" else (7,)
    if paged_result and method != "list_circuits":
        arguments = ()

    result = getattr(loader, method)(*arguments)

    assert result == (["result"] if paged_result else "result")
    if method == "list_circuits":
        expected = ((), {"site": ["a"]})
    else:
        expected = (arguments, {})
    assert calls == [expected]
