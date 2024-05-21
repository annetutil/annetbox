## Annetbox - Netbox client used by annet and related projects

This project implements subset of Netbox API methods

### Adding new methods:

1. Read openapi spec
2. Edit `models.py`
3. Edit `client_async.py`, do not forget adding `limit`/`offset`
4. Convert async code to sync

```shell
python transform_to_sync.py src/annetbox/v37/client_async.py > src/annetbox/v37/client_sync.py
```

### Verbose logging

for Requests

```python
import http.client
import logging

logging.basicConfig()
http.client.HTTPConnection.debuglevel = 1
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```
