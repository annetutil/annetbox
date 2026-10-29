"""The loader of NetBox 4.2."""
from ssl import SSLContext

from annetbox.base.client_sync import SessionFactoryT
from annetbox.common.loader import NetboxLoader
from annetbox.v41.views import FHRPGroupAssignmentV41, FHRPGroupV41
from .client_sync import NetboxV42
from .views import (
    InterfaceV42,
    IpAddressV42,
    NetboxDeviceV42,
    PrefixV42,
    convert_device,
    convert_fhrp_group_assignments,
    convert_fhrp_groups,
    convert_interfaces,
    convert_ip_addresses,
    convert_prefixes,
)


class NetboxLoaderV42(
    NetboxLoader[
        NetboxDeviceV42,
        InterfaceV42,
        IpAddressV42,
        PrefixV42,
        FHRPGroupV41,
        FHRPGroupAssignmentV41,
    ],
):
    client: NetboxV42

    def __init__(
        self,
        url: str,
        token: str = "",
        ssl_context: SSLContext | None = None,
        threads: int = 1,
        session_factory: SessionFactoryT | None = None,
    ) -> None:
        super().__init__(
            NetboxV42(
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
