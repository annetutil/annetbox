"""
NetBox 3.7 flavour of the common data structures (`annetbox.common.models`)
and converters from the raw 3.7 API models.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from adaptix import P
from adaptix.conversion import (
    allow_unlinked_optional,
    get_converter,
    link_constant,
    link_function,
)

from annetbox.common.models import (
    DeviceIp,
    Entity,
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
class DeviceIpV37(DeviceIp):
    family: int


@dataclass
class FHRPGroupV37(FHRPGroup[DeviceIpV37]):
    pass


@dataclass
class FHRPGroupAssignmentV37(FHRPGroupAssignment[FHRPGroupV37]):
    pass


@dataclass
class PrefixV37(Prefix):
    site: Entity | None = None


@dataclass
class IpAddressV37(IpAddress[PrefixV37]):
    role: Label | None = None
    prefix: PrefixV37 | None = None


@dataclass
class InterfaceV37(Interface[IpAddressV37, FHRPGroupAssignmentV37]):
    def _add_new_addr(
        self, address_mask: str, vrf: Vrf | None, family: IpFamily,
    ) -> None:
        self.ip_addresses.append(
            IpAddressV37(
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
class NetboxDeviceV37(NetboxDevice[InterfaceV37, DeviceIpV37]):
    device_role: Entity

    def __hash__(self) -> int:
        return hash((self.id, type(self)))

    def _make_interface(self, name: str, type: InterfaceType) -> InterfaceV37:
        return InterfaceV37(
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
    NetboxDeviceV37,
    recipe=[
        link_constant(P[NetboxDeviceV37].interfaces, factory=list),
    ],
)

# 3.7 VrfBrief does not have the description field
convert_interfaces = get_converter(
    list[api_models.Interface],
    list[InterfaceV37],
    recipe=[
        link_constant(P[InterfaceV37].ip_addresses, factory=list),
        link_constant(P[InterfaceV37].fhrp_groups, factory=list),
        link_constant(P[InterfaceV37].lag_min_links, value=None),
        allow_unlinked_optional(P[Vrf].description),
    ],
)

convert_prefixes = get_converter(
    list[api_models.Prefix],
    list[PrefixV37],
    recipe=[
        allow_unlinked_optional(P[Vrf].description),
    ],
)

convert_ip_addresses = get_converter(
    list[api_models.IpAddress],
    list[IpAddressV37],
    recipe=[
        link_constant(P[IpAddressV37].prefix, value=None),
        allow_unlinked_optional(P[Vrf].description),
    ],
)

convert_fhrp_group_assignments = get_converter(
    list[api_models.FHRPGroupAssignmentBrief],
    list[FHRPGroupAssignmentV37],
    recipe=[
        link_constant(P[FHRPGroupAssignmentV37].group, value=None),
        link_function(
            lambda model: model.group.id,
            P[FHRPGroupAssignmentV37].fhrp_group_id,
        ),
    ],
)

convert_fhrp_groups = get_converter(
    list[api_models.FHRPGroup],
    list[FHRPGroupV37],
)
