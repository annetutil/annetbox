"""
NetBox 4.1 flavour of the common data structures (`annetbox.common.models`)
and converters from the raw 4.1 API models.
"""
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone

from adaptix import P
from adaptix.conversion import get_converter, link_constant, link_function

from annetbox.common.models import (
    DeviceIp,
    Entity,
    EntityWithSlug,
    FHRPGroup,
    FHRPGroupAssignment,
    Interface,
    InterfaceType,
    IpAddress,
    IpFamily,
    Label,
    NetboxDevice,
    Prefix,
    Vrf,
)
from . import models as api_models


@dataclass
class DeviceIpV41(DeviceIp):
    family: IpFamily


@dataclass
class FHRPGroupV41(FHRPGroup[DeviceIpV41]):
    pass


@dataclass
class FHRPGroupAssignmentV41(FHRPGroupAssignment[FHRPGroupV41]):
    pass


@dataclass
class PrefixV41(Prefix):
    site: Entity | None = None


@dataclass
class IpAddressV41(IpAddress[PrefixV41]):
    role: Label | None = None
    prefix: PrefixV41 | None = None


@dataclass
class InterfaceV41(Interface[IpAddressV41, FHRPGroupAssignmentV41]):
    def _add_new_addr(
        self, address_mask: str, vrf: Vrf | None, family: IpFamily,
    ) -> None:
        self.ip_addresses.append(
            IpAddressV41(
                id=0,
                display=address_mask,
                address=address_mask,
                vrf=vrf,
                prefix=None,
                family=family,
                created=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                tags=[],
                status=Label(value="active", label="Active"),
                assigned_object_id=self.id,
            ),
        )


@dataclass
class NetboxDeviceV41(NetboxDevice[InterfaceV41, DeviceIpV41]):
    role: EntityWithSlug

    @property
    def device_role(self) -> EntityWithSlug:
        warnings.warn(
            "'device_role' is deprecated, use 'role' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.role

    def __hash__(self) -> int:
        return hash((self.id, type(self)))

    def _make_interface(self, name: str, type: InterfaceType) -> InterfaceV41:
        return InterfaceV41(
            name=name,
            device=self,
            enabled=True,
            description="",
            type=type,
            id=0,
            vrf=None,
            display=name,
            untagged_vlan=None,
            tagged_vlans=[],
            ip_addresses=[],
            connected_endpoints=[],
            mode=None,
        )


convert_device = get_converter(
    api_models.Device,
    NetboxDeviceV41,
    recipe=[
        link_constant(P[NetboxDeviceV41].interfaces, factory=list),
    ],
)

convert_interfaces = get_converter(
    list[api_models.Interface],
    list[InterfaceV41],
    recipe=[
        link_constant(P[InterfaceV41].ip_addresses, factory=list),
        link_constant(P[InterfaceV41].fhrp_groups, factory=list),
        link_constant(P[InterfaceV41].lag_min_links, value=None),
    ],
)

convert_prefixes = get_converter(
    list[api_models.Prefix],
    list[PrefixV41],
)

convert_ip_addresses = get_converter(
    list[api_models.IpAddress],
    list[IpAddressV41],
    recipe=[
        link_constant(P[IpAddressV41].prefix, value=None),
    ],
)

convert_fhrp_group_assignments = get_converter(
    list[api_models.FHRPGroupAssignmentBrief],
    list[FHRPGroupAssignmentV41],
    recipe=[
        link_constant(P[FHRPGroupAssignmentV41].group, value=None),
        link_function(
            lambda model: model.group.id,
            P[FHRPGroupAssignmentV41].fhrp_group_id,
        ),
    ],
)

convert_fhrp_groups = get_converter(
    list[api_models.FHRPGroup],
    list[FHRPGroupV41],
)
