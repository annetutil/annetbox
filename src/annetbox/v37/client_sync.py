from datetime import datetime

import dateutil.parser
from adaptix import Retort, loader
from dataclass_rest import get
from dataclass_rest.client_protocol import FactoryProtocol

from annetbox.base.client_sync import BaseNetboxClient, collect
from annetbox.base.models import PagingResponse
from .models import Device, Interface, IpAddress


class NetboxV37(BaseNetboxClient):
    def _init_response_body_factory(self) -> FactoryProtocol:
        return Retort(recipe=[loader(datetime, dateutil.parser.parse)])

    @get("dcim/interfaces")
    def interfaces(
        self,
        device_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Interface]:
        pass

    all_interfaces = collect(interfaces, field="device_id")

    @get("ipam/ip-addresses")
    def ip_addresses(
        self,
        interface_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[IpAddress]:
        pass

    all_ip_addresses = collect(ip_addresses, field="interface_id")

    @get("dcim/devices")
    def devices(
        self,
        name: list[str] | None = None,
        name__ic: list[str] | None = None,
        tag: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Device]:
        pass

    all_devices = collect(devices)

    @get("dcim/devices/{device_id}")
    def get_device(
        self,
        device_id: int,
    ) -> Device:
        pass
