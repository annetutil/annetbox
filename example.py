import asyncio
import os

from annetbox.base.status_client_sync import NetboxStatusClient
from annetbox.v37.client_async import NetboxV37 as AsyncNetboxV37
from annetbox.v37.client_sync import NetboxV37

url = os.getenv("NETBOX_URI")


def main_sync():
    # check the status of netbox installation
    # ClientError with `.status_code == 404` for 2.x versions
    status_client = NetboxStatusClient(url=url)
    status = status_client.status()
    print(status)

    # basic netbox methods
    netbox = NetboxV37(url=url)
    res = netbox.devices(limit=1)
    print(res)
    print()

    res = netbox.interfaces(limit=1)
    print(res)
    print()

    res = netbox.ip_addresses(limit=1)
    print(res)
    print()


async def main_async():
    # basic netbox methods
    netbox = AsyncNetboxV37(url=url)
    res = await netbox.devices(limit=1)
    print(res)
    print()

    res = await netbox.interfaces(limit=1)
    print(res)
    print()

    res = await netbox.ip_addresses(limit=1)
    print(res)
    print()

    await netbox.close()


if __name__ == '__main__':
    main_sync()
    print("==== async ===")
    asyncio.run(main_async())
