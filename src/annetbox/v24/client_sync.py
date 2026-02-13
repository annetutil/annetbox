from annetbox.base.client_sync import BaseNetboxClient, collect
from annetbox.base.models import PagingResponse
from .client_base import rest
from .models import Device, Interface, IpAddress


class NetboxV24(BaseNetboxClient):
    # dcim
    @rest.get("dcim/interfaces/")
    def dcim_interfaces(
        self,
        device_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Interface]:
        pass

    dcim_all_interfaces = collect(dcim_interfaces, field="device_id")

    @rest.get("dcim/devices/")
    def dcim_devices(
        self,
        name: list[str] | None = None,
        tag: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[Device]:
        pass

    dcim_all_devices = collect(dcim_devices)

    @rest.get("dcim/devices/{device_id}")
    def dcim_device(
        self,
        device_id: int,
    ) -> Device:
        pass

    # ipam
    @rest.get("ipam/ip-addresses/")
    def ipam_ip_addresses(
        self,
        interface_id: list[int] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PagingResponse[IpAddress]:
        pass

    ipam_all_ip_addresses = collect(ipam_ip_addresses, field="interface_id")
