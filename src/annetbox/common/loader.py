"""
Loading of the common data models from a NetBox.

The loader of a NetBox version (for example `annetbox.v42.loader`) has
the client and the converters of the version, the logic is the same for
all of them.
"""
from collections.abc import Callable, Sequence
from ipaddress import ip_interface
from typing import Any, Generic, TypeVar

from .models import (
    FHRPGroup,
    FHRPGroupAssignment,
    Interface,
    IpAddress,
    NetboxDevice,
    Prefix,
)

_DeviceT = TypeVar("_DeviceT", bound=NetboxDevice[Any, Any])
_InterfaceT = TypeVar("_InterfaceT", bound=Interface[Any, Any])
_IpAddressT = TypeVar("_IpAddressT", bound=IpAddress[Any])
_PrefixT = TypeVar("_PrefixT", bound=Prefix)
_FHRPGroupT = TypeVar("_FHRPGroupT", bound=FHRPGroup[Any])
_FHRPGroupAssignmentT = TypeVar(
    "_FHRPGroupAssignmentT", bound=FHRPGroupAssignment[Any],
)


class NetboxLoader(
    Generic[
        _DeviceT,
        _InterfaceT,
        _IpAddressT,
        _PrefixT,
        _FHRPGroupT,
        _FHRPGroupAssignmentT,
    ],
):
    """
    Devices and everything attached to them, as the common data models.

    The client is there for everything the loader does not do, call
    its methods directly.
    """

    def __init__(
        self,
        client: Any,
        *,
        convert_device: Callable[[Any], _DeviceT],
        convert_interfaces: Callable[[Any], list[_InterfaceT]],
        convert_ip_addresses: Callable[[Any], list[_IpAddressT]],
        convert_prefixes: Callable[[Any], list[_PrefixT]],
        convert_fhrp_group_assignments: Callable[
            [Any], list[_FHRPGroupAssignmentT],
        ],
        convert_fhrp_groups: Callable[[Any], list[_FHRPGroupT]],
    ) -> None:
        self.client = client
        self.convert_device = convert_device
        self.convert_interfaces = convert_interfaces
        self.convert_ip_addresses = convert_ip_addresses
        self.convert_ip_prefixes = convert_prefixes
        self.convert_fhrp_group_assignments = convert_fhrp_group_assignments
        self.convert_fhrp_groups = convert_fhrp_groups

    def list_fqdns(
        self, query: dict[str, list[str]] | None = None,
    ) -> list[str]:
        query = query or {}
        return [
            d.name for d in self.client.dcim_all_devices_brief(**query).results
        ]

    def list_devices(self, query: dict[str, list[str]]) -> list[_DeviceT]:
        return [
            self.convert_device(dev)
            for dev in self.client.dcim_all_devices(**query).results
        ]

    def get_device(self, device_id: int) -> _DeviceT:
        return self.convert_device(self.client.dcim_device(device_id))

    def list_interfaces_by_devices(
        self, device_ids: list[int],
    ) -> list[_InterfaceT]:
        return self.convert_interfaces(
            self.client.dcim_all_interfaces(device_id=device_ids).results,
        )

    def list_interfaces(self, ids: list[int]) -> list[_InterfaceT]:
        return self.convert_interfaces(
            self.client.dcim_all_interfaces(id=ids).results,
        )

    def list_ipaddr_by_ifaces(
        self, iface_ids: list[int],
    ) -> list[_IpAddressT]:
        return self.convert_ip_addresses(
            self.client.ipam_all_ip_addresses(interface_id=iface_ids).results,
        )

    def list_ipprefixes(self, prefixes: list[str]) -> list[_PrefixT]:
        return self.convert_ip_prefixes(
            self.client.ipam_all_prefixes(prefix=prefixes).results,
        )

    def list_fhrp_group_assignments(
        self, iface_ids: list[int],
    ) -> list[_FHRPGroupAssignmentT]:
        raw_assignments = (
            self.client.ipam_all_fhrp_group_assignments_by_interface(
                interface_id=iface_ids,
            )
        )
        return self.convert_fhrp_group_assignments(raw_assignments.results)

    def list_fhrp_groups(self, ids: list[int]) -> list[_FHRPGroupT]:
        raw_groups = self.client.ipam_all_fhrp_groups_by_id(id=list(ids))
        return self.convert_fhrp_groups(raw_groups.results)

    def fill_interfaces(self, devices: Sequence[_DeviceT]) -> None:
        """Load the interfaces of the devices, with addresses and groups."""
        device_mapping = {d.id: d for d in devices}
        interfaces = self.list_interfaces_by_devices(list(device_mapping))
        for interface in interfaces:
            device_mapping[interface.device.id].interfaces.append(interface)
        self._fill_interface_fhrp_groups(interfaces)
        self._fill_interface_ipaddress(interfaces)

    def _fill_interface_fhrp_groups(
        self, interfaces: list[_InterfaceT],
    ) -> None:
        interface_mapping = {
            i.id: i for i in interfaces if i.count_fhrp_groups
        }
        assignments = self.list_fhrp_group_assignments(
            list(interface_mapping),
        )
        group_ids = {r.fhrp_group_id for r in assignments}
        groups = {g.id: g for g in self.list_fhrp_groups(list(group_ids))}
        for assignment in assignments:
            assignment.group = groups[assignment.fhrp_group_id]
            assert assignment.interface_id is not None  # noqa: S101
            interface_mapping[assignment.interface_id].fhrp_groups.append(
                assignment,
            )

    def _fill_interface_ipaddress(
        self, interfaces: list[_InterfaceT],
    ) -> None:
        interface_mapping = {
            i.id: i for i in interfaces if i.count_ipaddresses
        }
        ips = self.list_ipaddr_by_ifaces(list(interface_mapping))
        for ip in ips:
            assert ip.assigned_object_id is not None  # noqa: S101
            interface_mapping[ip.assigned_object_id].ip_addresses.append(ip)
        self._fill_ipaddr_prefixes(ips)

    def _fill_ipaddr_prefixes(self, ips: list[_IpAddressT]) -> None:
        ip_to_cidrs = {
            ip.address: str(ip_interface(ip.address).network) for ip in ips
        }
        prefixes = self.list_ipprefixes(list(ip_to_cidrs.values()))
        cidr_to_prefix = {x.prefix: x for x in prefixes}
        for ip in ips:
            cidr = ip_to_cidrs[ip.address]
            ip.prefix = cidr_to_prefix.get(cidr)

    # Deprecated, for the migration period only, kept so that old code does
    # not break. These are the methods of the adapter of annet, use `client`
    # in new code, nothing is going to be added here.
    # They are going to be removed in the next major release.
    def get_site(self, site_id: int) -> Any:
        return self.client.dcim_site(site_id)

    def list_sites(self) -> Any:
        return self.client.dcim_all_sites().results

    def get_site_group(self, site_group_id: int) -> Any:
        return self.client.dcim_site_group(site_group_id)

    def list_site_groups(self) -> Any:
        return self.client.dcim_all_site_groups().results

    def get_location(self, location_id: int) -> Any:
        return self.client.dcim_location(location_id)

    def list_locations(self) -> Any:
        return self.client.dcim_all_locations().results

    def get_region(self, region_id: int) -> Any:
        return self.client.dcim_region(region_id)

    def list_regions(self) -> Any:
        return self.client.dcim_all_regions().results

    def get_tenant(self, tenant_id: int) -> Any:
        return self.client.tenancy_tenant(tenant_id)

    def list_tenants(self) -> Any:
        return self.client.tenancy_all_tenants().results

    def get_tenant_group(self, tenant_group_id: int) -> Any:
        return self.client.tenancy_tenant_group(tenant_group_id)

    def list_tenant_groups(self) -> Any:
        return self.client.tenancy_all_tenant_groups().results

    def list_all_vrfs(self) -> Any:
        return self.client.ipam_all_vrfs().results

    def list_all_vlans(self) -> Any:
        return self.client.ipam_all_vlans().results

    def get_circuit(self, circuit_id: int) -> Any:
        return self.client.circuit(circuit_id)

    def list_circuits(self, query: dict[str, list[str]]) -> Any:
        return self.client.circuits_all(**query).results

    def trace_interface(self, iface_id: int) -> Any:
        return self.client.dcim_interface_trace(iface_id)
