from datetime import datetime

import dateutil.parser
from adaptix import Retort, loader
from dataclass_rest import get
from dataclass_rest.client_protocol import FactoryProtocol

from annetbox.base.client_async import BaseNetboxClient, collect
from annetbox.base.models import PagingResponse
from .models import Device, Interface, IpAddress


class NetboxV37(BaseNetboxClient):
    def _init_response_body_factory(self) -> FactoryProtocol:
        return Retort(recipe=[loader(datetime, dateutil.parser.parse)])

    # dcim
    @get("dcim/interfaces")
    async def dcim_interfaces(
        self,
        device: list[str] | None = None,
        device_n: list[str] | None = None,
        device_id: list[int] | None = None,
        device_id_n: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Interface]:
        pass

    dcim_all_interfaces = collect(dcim_interfaces, field="device_id")

    @get("dcim/cables")
    def dcim_cables(
        self,
        device: list[str] | None = None,
        device_id: list[int] | None = None,
        interface_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ):
        pass

    dcim_all_cables = collect(dcim_cables, field="interface_id")

    @get("dcim/devices")
    async def dcim_devices(
        self,
        name: list[str] | None = None,
        name_empty: bool | None = None,
        name_ic: list[str] | None = None,
        name_ie: list[str] | None = None,
        name_iew: list[str] | None = None,
        name_isw: list[str] | None = None,
        name_n: list[str] | None = None,
        name_nic: list[str] | None = None,
        name_nie: list[str] | None = None,
        name_niew: list[str] | None = None,
        name_nisw: list[str] | None = None,
        tag: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Device]:
        pass

    dcim_all_devices = collect(dcim_devices)

    @get("dcim/devices/{device_id}")
    async def dcim_device(
        self,
        device_id: int,
    ) -> Device:
        pass

    # ipam
    @get("ipam/ip-addresses")
    async def ipam_ip_addresses(
        self,
        interface_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[IpAddress]:
        pass

    ipam_all_ip_addresses = collect(ipam_ip_addresses, field="interface_id")
