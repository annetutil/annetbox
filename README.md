# Annetbox - Netbox client used by annet and related projects

This project implements subset of Netbox API methods

## Usage

1. Install `sync` or `async` version

```shell
pip install 'annetbox[sync]'
```

2. Create client instance according to your netbox version (only some are supported)

```python
from annetbox.v37.client_sync import NetboxV37

netbox = NetboxV37(url="https://demo.netbox.dev", token="YOUR NETBOX TOKEN")
```

3. Call methods

```python
res = netbox.dcim_devices(limit=1)
```

## Configuration

### Verbose logging

For sync client

```python
import http.client
import logging

logging.basicConfig()
http.client.HTTPConnection.debuglevel = 1
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```

### Custom SSL context

1. Create context

```python
import ssl

context = ssl.create_default_context(cafile="path/to/cacert.pem")
```

2. Pass it to client

```python
netbox = NetboxV37(url=url, token=token, ssl_context=context)
```

## Development

### Adding new methods

1. Read openapi spec
2. Edit `models.py`
3. Edit `client_async.py`, do not forget adding `limit`/`offset`
4. Convert async code to sync

```shell
python transform_to_sync.py src/annetbox/v37/client_async.py > src/annetbox/v37/client_sync.py
```
