from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Entity:
    id: int
    name: str


@dataclass
class Label:
    value: str
    label: str


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
    family: int


@dataclass
class Interface(Entity):
    device: Entity
    enabled: bool
    display: str = ""  # added in 3.x


@dataclass
class Device(Entity):
    url: str
    display: str  # renamed in 3.x from display_name
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
    tags: list[Entity]
    custom_fields: dict[str, Any]
    created: datetime
    last_updated: datetime


@dataclass
class IpFamily:
    value: int
    label: str


@dataclass
class IpAddress:
    id: int
    assigned_object_id: int
    display: str
    family: IpFamily
    address: str
    status: Label
    tags: list[Entity]
    created: datetime
    last_updated: datetime
