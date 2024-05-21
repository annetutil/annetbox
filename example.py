import os

from annetbox.base.client_sync import NetboxStatusClient
from annetbox.v37.client_sync import NetboxV37


def main():
    url = os.getenv("NETBOX_URL")
    token = os.getenv("NETBOX_TOKEN")
    # check the status of netbox installation
    # ClientError with `.status_code == 404` for 2.x versions
    status_client = NetboxStatusClient(url=url)
    status = status_client.status()
    print(status)

    # basic netbox methods
    netbox = NetboxV37(url=url, token=token)
    res = netbox.dcim_devices(limit=1)
    print(res)
    print()

    res = netbox.dcim_interfaces(limit=1)
    print(res)
    print()

    res = netbox.dcim_cables(limit=1)
    print(res)
    print()

    res = netbox.ipam_ip_addresses(limit=1)
    print(res)
    print()


if __name__ == '__main__':
    main()
