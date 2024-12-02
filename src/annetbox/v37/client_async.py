from collections.abc import Iterable
from datetime import datetime

import dateutil.parser
from adaptix import Retort, loader, name_mapping
from dataclass_rest import delete, get, post
from dataclass_rest.client_protocol import FactoryProtocol

from annetbox.base.client_async import BaseNetboxClient, collect
from annetbox.base.models import PagingResponse
from .models import (
    Cable,
    ConsolePort,
    Device,
    Entity,
    Interface,
    IpAddress,
    ItemToDelete,
    NewCable,
    Prefix,
)


class NetboxV37(BaseNetboxClient):
    def _init_response_body_factory(self) -> FactoryProtocol:
        return Retort(recipe=[loader(datetime, dateutil.parser.parse)])

    def _init_request_body_factory(self) -> FactoryProtocol:
        return Retort(
            recipe=[
                name_mapping(NewCable, omit_default=True),
            ],
        )

    # dcim
    @get("dcim/interfaces/")
    async def dcim_interfaces(
        self,
        id: list[int] | None = None,
        device: list[str] | None = None,
        device__n: list[str] | None = None,
        device_id: list[int] | None = None,
        device_id__n: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Interface]:
        pass

    dcim_all_interfaces = collect(dcim_interfaces, field="device_id")
    dcim_all_interfaces_by_id = collect(dcim_interfaces, field="id")

    @get("dcim/interfaces/{id}/")
    async def dcim_interface(self, id: int) -> Interface:
        pass

    @get("dcim/console-ports/")
    async def dcim_console_ports(
        self,
        id: list[int] | None = None,
        device: list[str] | None = None,
        device__n: list[str] | None = None,
        device_id: list[int] | None = None,
        device_id__n: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[ConsolePort]:
        pass

    dcim_all_console_ports = collect(dcim_console_ports, field="device_id")
    dcim_all_console_ports_by_id = collect(dcim_console_ports, field="id")

    @get("dcim/console-ports/{id}/")
    async def dcim_console_port(self, id: int) -> ConsolePort:
        pass

    @get("dcim/cables/")
    async def dcim_cables(
        self,
        device: list[str] | None = None,
        device_id: list[int] | None = None,
        interface_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Cable]:
        pass

    dcim_all_cables = collect(dcim_cables, field="interface_id")

    @post("dcim/cables/")
    async def dcim_cable_create(self, body: NewCable) -> Cable:
        pass

    @post("dcim/cables/")
    async def dcim_cable_bulk_create(
        self,
        body: list[NewCable],
    ) -> list[Cable]:
        pass

    @delete("dcim/cables/")
    async def _dcim_cable_bulk_delete(self, body: list[ItemToDelete]) -> None:
        pass

    async def dcim_cable_bulk_delete(self, body: Iterable[int]) -> None:
        return await self._dcim_cable_bulk_delete(
            [ItemToDelete(id=x) for x in body],
        )

    @delete("dcim/cables/{id}/")
    async def dcim_cable_delete(self, id: int) -> None:
        pass

    @get("dcim/devices/")
    async def dcim_devices(
        self,
        name: list[str] | None = None,
        name__empty: bool | None = None,
        name__ic: list[str] | None = None,
        name__ie: list[str] | None = None,
        name__iew: list[str] | None = None,
        name__isw: list[str] | None = None,
        name__n: list[str] | None = None,
        name__nic: list[str] | None = None,
        name__nie: list[str] | None = None,
        name__niew: list[str] | None = None,
        name__nisw: list[str] | None = None,
        id: list[int] | None = None,
        tag: list[str] | None = None,
        role: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Device]:
        pass

    dcim_all_devices = collect(dcim_devices)
    dcim_all_devices_by_id = collect(dcim_devices, field="id")


    @get("dcim/devices/?brief=1")
    async def dcim_devices_brief(
        self,
        name: list[str] | None = None,
        name__empty: bool | None = None,
        name__ic: list[str] | None = None,
        name__ie: list[str] | None = None,
        name__iew: list[str] | None = None,
        name__isw: list[str] | None = None,
        name__n: list[str] | None = None,
        name__nic: list[str] | None = None,
        name__nie: list[str] | None = None,
        name__niew: list[str] | None = None,
        name__nisw: list[str] | None = None,
        id: list[int] | None = None,
        tag: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Entity]:
        pass

    dcim_all_devices_brief = collect(dcim_devices_brief)
    dcim_all_devices_brief_by_id = collect(dcim_devices_brief, field="id")

    @get("dcim/devices/{device_id}/")
    async def dcim_device(
        self,
        device_id: int,
    ) -> Device:
        pass

    # ipam
    @get("ipam/ip-addresses/")
    async def ipam_ip_addresses(
        self,
        interface_id: list[int] | None = None,
        device_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[IpAddress]:
        pass

    ipam_all_ip_addresses = collect(ipam_ip_addresses, field="interface_id")

    @get("ipam/ip-addresses/{id}/")
    async def ipam_ip_address(
        self,
        id: int,
    ) -> IpAddress:
        pass

    @get("ipam/prefixes/")
    async def prefixes(
        self,
        prefix: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Prefix]:
        pass

    ipam_all_prefixes = collect(prefixes, field="prefix")
