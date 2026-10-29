"""The loader of NetBox 4.1."""
from ssl import SSLContext

from annetbox.base.client_sync import SessionFactoryT
from annetbox.common.loader import NetboxLoader
from .client_sync import NetboxV41
from .views import (
    FHRPGroupAssignmentV41,
    FHRPGroupV41,
    InterfaceV41,
    IpAddressV41,
    NetboxDeviceV41,
    PrefixV41,
    convert_device,
    convert_fhrp_group_assignments,
    convert_fhrp_groups,
    convert_interfaces,
    convert_ip_addresses,
    convert_prefixes,
)


class NetboxLoaderV41(
    NetboxLoader[
        NetboxDeviceV41,
        InterfaceV41,
        IpAddressV41,
        PrefixV41,
        FHRPGroupV41,
        FHRPGroupAssignmentV41,
    ],
):
    client: NetboxV41

    def __init__(
        self,
        url: str,
        token: str = "",
        ssl_context: SSLContext | None = None,
        threads: int = 1,
        session_factory: SessionFactoryT | None = None,
    ) -> None:
        super().__init__(
            NetboxV41(
                url=url,
                token=token,
                ssl_context=ssl_context,
                threads=threads,
                session_factory=session_factory,
            ),
            convert_device=convert_device,
            convert_interfaces=convert_interfaces,
            convert_ip_addresses=convert_ip_addresses,
            convert_prefixes=convert_prefixes,
            convert_fhrp_group_assignments=convert_fhrp_group_assignments,
            convert_fhrp_groups=convert_fhrp_groups,
        )
