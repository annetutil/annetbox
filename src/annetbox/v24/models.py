from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Entity:
    id: int
    name: str


@dataclass
class Label:
    value: int
    label: str


@dataclass
class DeviceType:
    id: int
    manufacturer: Entity
    model: str


@dataclass
class DeviceIp:
    id: int
    address: str
    family: int


@dataclass
class Device(Entity):
    url: str
    display_name: str
    device_type: DeviceType
    device_role: Entity
    tenant: Entity | None
    platform: Entity | None
    serial: str
    asset_tag: str | None
    site: Entity
    rack: Entity | None
    position: float | None
    face: Label | None
    status: Label
    primary_ip: DeviceIp | None
    primary_ip4: DeviceIp | None
    primary_ip6: DeviceIp | None
    tags: list[str]
    custom_fields: dict[str, Any]
    created: datetime
    last_updated: datetime


@dataclass
class Interface(Entity):
    device: Entity
    enabled: bool


@dataclass
class Vrf(Entity):
    rd: str


@dataclass
class IpAddress:
    id: int
    family: int
    address: str
    vrf: Vrf | None
    tenant: Any  # ???
    status: Label
    description: str | None
    custom_fields: dict[str, Any]
    tags: list[str]
    created: datetime
    last_updated: datetime

    interface: Entity

    nat_inside: Any  # ???
    nat_outside: Any  # ???
