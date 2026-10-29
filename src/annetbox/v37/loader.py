"""The loader of NetBox 3.7."""
from ssl import SSLContext

from annetbox.base.client_sync import SessionFactoryT
from annetbox.common.loader import NetboxLoader
from .client_sync import NetboxV37
from .views import (
    FHRPGroupAssignmentV37,
    FHRPGroupV37,
    InterfaceV37,
    IpAddressV37,
    NetboxDeviceV37,
    PrefixV37,
    convert_device,
    convert_fhrp_group_assignments,
    convert_fhrp_groups,
    convert_interfaces,
    convert_ip_addresses,
    convert_prefixes,
)


class NetboxLoaderV37(
    NetboxLoader[
        NetboxDeviceV37,
        InterfaceV37,
        IpAddressV37,
        PrefixV37,
        FHRPGroupV37,
        FHRPGroupAssignmentV37,
    ],
):
    client: NetboxV37

    def __init__(
        self,
        url: str,
        token: str = "",
        ssl_context: SSLContext | None = None,
        threads: int = 1,
        session_factory: SessionFactoryT | None = None,
    ) -> None:
        super().__init__(
            NetboxV37(
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
