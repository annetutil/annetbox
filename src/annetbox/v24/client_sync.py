from datetime import datetime

import dateutil.parser
from adaptix import Retort, loader
from dataclass_rest import get

from annetbox.base.client_sync import BaseNetboxClient, collect
from annetbox.base.models import PagingResponse
from .models import Device, Interface, IpAddress


class NetboxV24(BaseNetboxClient):
    def _init_response_body_factory(self) -> Retort:
        return Retort(recipe=[loader(datetime, dateutil.parser.parse)])

    # dcim
    @get("dcim/interfaces/")
    def dcim_interfaces(
        self,
        device_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Interface]:
        pass

    dcim_all_interfaces = collect(dcim_interfaces, field="device_id")

    @get("dcim/devices/")
    def dcim_devices(
        self,
        name: list[str] | None = None,
        tag: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Device]:
        pass

    dcim_all_devices = collect(dcim_devices)

    @get("dcim/devices/{device_id}")
    def dcim_device(
        self,
        device_id: int,
    ) -> Device:
        pass

    # ipam
    @get("ipam/ip-addresses/")
    def ipam_ip_addresses(
        self,
        interface_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[IpAddress]:
        pass

    ipam_all_ip_addresses = collect(ipam_ip_addresses, field="interface_id")
