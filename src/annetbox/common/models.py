"""
Version-independent NetBox data structures.

Per-version classes (e.g. `annetbox.v42.views`) derive from these and
provide converters from the raw API models of the corresponding NetBox version.
"""
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from ipaddress import IPv6Interface, ip_interface
from typing import Any, Generic, TypeVar, cast


@dataclass
class Entity:
    id: int
    name: str


@dataclass
class EntityWithSlug(Entity):
    slug: str


@dataclass
class Label:
    value: str
    label: str


@dataclass
class IpFamily:
    value: int
    label: str


@dataclass
class Vrf(Entity):
    rd: str | None  # netbox get null if not present
    # netbox v37 does not include this field in VrfBrief
    description: str | None = None


@dataclass
class Prefix:
    id: int
    prefix: str
    # `site` deprecated since v4.2, replace in derived classes.
    vrf: Vrf | None
    tenant: Entity | None
    vlan: Entity | None
    role: Entity | None
    status: Label
    is_pool: bool
    custom_fields: dict[str, Any]
    created: datetime
    last_updated: datetime
    description: str | None = ""
    tags: list[EntityWithSlug] = field(default_factory=list)


_PrefixT = TypeVar("_PrefixT", bound=Prefix)


@dataclass
class IpAddress(Generic[_PrefixT]):
    id: int
    assigned_object_id: int | None
    display: str
    family: IpFamily
    address: str
    status: Label
    created: datetime
    last_updated: datetime
    prefix: _PrefixT | None = None
    vrf: Vrf | None = None
    tags: list[EntityWithSlug] = field(default_factory=list)


def vrf_object(vrf: str | None) -> Vrf | None:
    if vrf is None:
        return None
    else:
        return Vrf(id=0, name=vrf, description="", rd=None)


@dataclass
class DeviceType:
    id: int
    manufacturer: Entity
    model: str


@dataclass
class DeviceIp:
    id: int
    display: str
    address: str


@dataclass
class InterfaceConnectedEndpoint(Entity):
    device: Entity | None


@dataclass
class InterfaceType:
    value: str
    label: str


@dataclass
class InterfaceMode:
    value: str
    label: str


@dataclass
class InterfaceVlan(Entity):
    vid: int


_IpAddressT = TypeVar("_IpAddressT", bound=IpAddress[Any])

_DeviceIPT = TypeVar("_DeviceIPT", bound=DeviceIp)


@dataclass
class FHRPGroup(Generic[_DeviceIPT]):
    id: int
    group_id: int
    display: str
    protocol: str
    description: str | None

    name: str
    auth_type: str | None
    auth_key: str
    tags: list[EntityWithSlug]
    custom_fields: dict[str, Any]
    ip_addresses: list[_DeviceIPT]
    comments: str | None = None


_FHRPGroupT = TypeVar("_FHRPGroupT", bound=FHRPGroup[Any])


@dataclass
class FHRPGroupAssignment(Generic[_FHRPGroupT]):
    id: int
    display: str
    priority: int
    group: _FHRPGroupT
    fhrp_group_id: int

    interface_type: str | None
    interface_id: int | None


_FHRPGroupAssignmentT = TypeVar(
    "_FHRPGroupAssignmentT",
    bound=FHRPGroupAssignment[Any],
)


@dataclass
class Interface(Entity, Generic[_IpAddressT, _FHRPGroupAssignmentT]):
    device: Entity
    enabled: bool
    description: str
    type: InterfaceType
    connected_endpoints: list[InterfaceConnectedEndpoint] | None
    mode: InterfaceMode | None
    untagged_vlan: InterfaceVlan | None
    tagged_vlans: list[InterfaceVlan] | None
    tags: list[EntityWithSlug] = field(default_factory=list)
    display: str = ""
    vrf: Vrf | None = None
    mtu: int | None = None
    lag: Entity | None = None
    lag_min_links: int | None = None
    speed: int | None = None

    custom_fields: dict[str, Any] = field(default_factory=dict)

    ip_addresses: list[_IpAddressT] = field(default_factory=list)
    count_ipaddresses: int = 0
    fhrp_groups: list[_FHRPGroupAssignmentT] = field(default_factory=list)
    count_fhrp_groups: int = 0

    def set_vrf(self, vrf: str | None) -> None:
        if self.vrf is not None and self.vrf.name == vrf:
            return
        self.vrf = vrf_object(vrf)

    def add_addr(self, address_mask: str, vrf: str | None) -> None:
        addr = ip_interface(address_mask)

        # when comparing ip addressess
        # we dont care about the vrf of an addr
        # because the actual vrf will be
        # determined by an interface's vrf
        # and there can be only one
        #
        # also we dont care about a mask
        # because no device will allow
        # the same addr with multiple masks
        for existing_addr in self.ip_addresses:
            existing = ip_interface(existing_addr.address)
            if existing.ip == addr.ip:
                return

        vrf_obj = vrf_object(vrf)
        if isinstance(addr, IPv6Interface):
            family = IpFamily(value=6, label="IPv6")
        else:
            family = IpFamily(value=4, label="IPv4")
        self._add_new_addr(address_mask, vrf_obj, family)

    @abstractmethod
    def _add_new_addr(
        self, address_mask: str, vrf: Vrf | None, family: IpFamily,
    ) -> None:
        raise NotImplementedError


_InterfaceT = TypeVar("_InterfaceT", bound=Interface[Any, Any])


@dataclass
class NetboxDevice(Entity, Generic[_InterfaceT, _DeviceIPT]):
    url: str

    display: str
    device_type: DeviceType
    # `device_role` deprecated since v4.0, replace in derived classes.
    tenant: Entity | None
    platform: EntityWithSlug | None
    serial: str
    asset_tag: str | None
    site: Entity
    rack: Entity | None
    position: float | None
    face: Label | None
    status: Label
    primary_ip: _DeviceIPT | None
    primary_ip4: _DeviceIPT | None
    primary_ip6: _DeviceIPT | None
    tags: list[EntityWithSlug]
    custom_fields: dict[str, Any]
    created: datetime
    last_updated: datetime
    cluster: Entity | None
    config_context: dict[str, Any] | None
    config_template: dict[str, Any] | None

    interfaces: list[_InterfaceT] = field(default_factory=list, kw_only=True)

    @property
    def neighbors(self) -> list[Entity]:
        return [
            endpoint.device
            for iface in self.interfaces
            if iface.connected_endpoints
            for endpoint in iface.connected_endpoints
            if endpoint.device
        ]

    # compat
    @property
    def neighbours_fqdns(self) -> list[str]:
        return [dev.name for dev in self.neighbors]

    @property
    def neighbours_ids(self) -> list[int]:
        return [dev.id for dev in self.neighbors]

    def __hash__(self) -> int:
        return hash((self.id, type(self)))

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.url == cast("NetboxDevice[Any, Any]", other).url

    @abstractmethod
    def _make_interface(self, name: str, type: InterfaceType) -> _InterfaceT:
        raise NotImplementedError

    def find_interface(self, name: str) -> _InterfaceT | None:
        for iface in self.interfaces:
            if iface.name == name:
                return iface
        return None
