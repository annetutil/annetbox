"""
NetBox 4.2 flavour of the common data structures (`annetbox.common.models`)
and converters from the raw 4.2 API models.
"""
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone

from adaptix import P
from adaptix.conversion import get_converter, link_constant, link_function

from annetbox.common.models import (
    Entity,
    EntityWithSlug,
    Interface,
    InterfaceType,
    IpAddress,
    IpFamily,
    Label,
    NetboxDevice,
    Prefix,
    Vrf,
)
from annetbox.v41.views import (
    DeviceIpV41,
    FHRPGroupAssignmentV41,
    FHRPGroupV41,
)
from . import models as api_models


@dataclass
class PrefixV42(Prefix):
    scope: Entity | None = None
    scope_type: str | None = None

    @property
    def site(self) -> Entity | None:
        if self.scope_type == "dcim.site":
            return self.scope
        return None


@dataclass
class IpAddressV42(IpAddress[PrefixV42]):
    role: Label | None = None
    prefix: PrefixV42 | None = None


@dataclass
class InterfaceV42(Interface[IpAddressV42, FHRPGroupAssignmentV41]):
    def _add_new_addr(
        self, address_mask: str, vrf: Vrf | None, family: IpFamily,
    ) -> None:
        self.ip_addresses.append(
            IpAddressV42(
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
class NetboxDeviceV42(NetboxDevice[InterfaceV42, DeviceIpV41]):
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

    def _make_interface(self, name: str, type: InterfaceType) -> InterfaceV42:
        return InterfaceV42(
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
    NetboxDeviceV42,
    recipe=[
        link_constant(P[NetboxDeviceV42].interfaces, factory=list),
    ],
)

convert_interfaces = get_converter(
    list[api_models.Interface],
    list[InterfaceV42],
    recipe=[
        link_constant(P[InterfaceV42].ip_addresses, factory=list),
        link_constant(P[InterfaceV42].fhrp_groups, factory=list),
        link_constant(P[InterfaceV42].lag_min_links, value=None),
    ],
)

convert_prefixes = get_converter(
    list[api_models.Prefix],
    list[PrefixV42],
)

convert_ip_addresses = get_converter(
    list[api_models.IpAddress],
    list[IpAddressV42],
    recipe=[
        link_constant(P[IpAddressV42].prefix, value=None),
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
