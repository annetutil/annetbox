from collections.abc import Iterable

from annetbox.base.client_sync import BaseNetboxClient, collect
from .client_base import BaseNetboxV42
from .models import (
    ItemToDelete,
)


class NetboxV42(BaseNetboxClient, BaseNetboxV42):
    dcim_all_interfaces = collect(
        BaseNetboxV42.dcim_interfaces, field="device_id", batch_size=10,  # heavy request
    )
    dcim_all_interfaces_by_id = collect(BaseNetboxV42.dcim_interfaces, field="id")

    dcim_all_console_ports = collect(BaseNetboxV42.dcim_console_ports, field="device_id")
    dcim_all_console_ports_by_id = collect(BaseNetboxV42.dcim_console_ports, field="id")

    dcim_all_cables = collect(BaseNetboxV42.dcim_cables, field="interface_id")

    def dcim_cable_bulk_delete(self, body: Iterable[int]) -> None:
        return self._dcim_cable_bulk_delete(
            [ItemToDelete(id=x) for x in body],
        )

    dcim_all_devices = collect(BaseNetboxV42.dcim_devices)
    dcim_all_devices_by_id = collect(BaseNetboxV42.dcim_devices, field="id")

    dcim_all_devices_brief = collect(BaseNetboxV42.dcim_devices_brief)
    dcim_all_devices_brief_by_id = collect(BaseNetboxV42.dcim_devices_brief, field="id")

    ipam_all_ip_addresses = collect(BaseNetboxV42.ipam_ip_addresses, field="interface_id")

    ipam_all_prefixes = collect(BaseNetboxV42.prefixes, field="prefix")

    ipam_all_vlans = collect(BaseNetboxV42.ipam_vlans, field="vid")
    ipam_all_vlans_by_id = collect(BaseNetboxV42.ipam_vlans, field="id")

    ipam_all_vrfs = collect(BaseNetboxV42.ipam_vrfs, field="vid")
    ipam_all_vrfs_by_id = collect(BaseNetboxV42.ipam_vrfs, field="id")

    ipam_all_fhrp_groups = collect(BaseNetboxV42.ipam_fhrp_groups)
    ipam_all_fhrp_groups_by_id = collect(BaseNetboxV42.ipam_fhrp_groups, field="id")


    ipam_all_fhrp_group_assignments = collect(
        BaseNetboxV42.ipam_fhrp_group_assignments_brief,
    )
    ipam_all_fhrp_group_assignments_by_interface = collect(
        BaseNetboxV42.ipam_fhrp_group_assignments_brief, field="interface_id",
    )
