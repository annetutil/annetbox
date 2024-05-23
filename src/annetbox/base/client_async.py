import http
from collections.abc import Callable
from functools import wraps
from ssl import SSLContext
from typing import Any, TypeVar

from adaptix import NameStyle, Retort, name_mapping
from aiohttp import ClientResponse, ClientSession, TCPConnector
from dataclass_rest import get
from dataclass_rest.client_protocol import FactoryProtocol
from dataclass_rest.http.aiohttp import AiohttpClient, AiohttpMethod
from dataclass_rest.http_request import HttpRequest

from .models import PagingResponse, Status

Func = TypeVar("Func", bound=Callable)


def _collect_by_pages(func: Func) -> Func:
    """Collect all results using only pagination."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        kwargs.setdefault("offset", 0)
        limit = kwargs.setdefault("limit", 100)
        results = []
        method = func.__get__(self, self.__class__)
        has_next = True
        while has_next:
            page = await method(*args, **kwargs)
            kwargs["offset"] += limit
            results.extend(page.results)
            has_next = bool(page.next)
        return PagingResponse(
            previous=None,
            next=None,
            count=len(results),
            results=results,
        )

    return wrapper


# default batch size 100 is calculated to fit list of UUIDs in 4k URL length
def collect(func: Func, field: str = "", batch_size: int = 100) -> Func:
    """
    Collect data from method iterating over pages and filter batches.

    :param func: Method to call
    :param field: Field which defines a filter split into batches
    :param batch_size: Limit of values in `field` filter requested at a time
    """
    func = _collect_by_pages(func)
    if not field:
        return func

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        method = func.__get__(self, self.__class__)

        value = kwargs.get(field)
        if not value:
            return await method(*args, **kwargs)

        results = []
        for offset in range(0, len(value), batch_size):
            kwargs[field] = value[offset : offset + batch_size]
            page = await method(*args, **kwargs)
            results.extend(page.results)
        return PagingResponse(
            previous=None,
            next=None,
            count=len(results),
            results=results,
        )

    return wrapper


class NoneAwareAiohttpMethod(AiohttpMethod):
    async def _pre_process_request(self, request: HttpRequest) -> HttpRequest:
        request.query_params = {
            k: v for k, v in request.query_params.items() if v is not None
        }
        return request

    async def _response_body(self, response: ClientResponse) -> Any:
        if response.status == http.HTTPStatus.NO_CONTENT:
            return None
        return await super()._response_body(response)


class BaseNetboxClient(AiohttpClient):
    method_class = NoneAwareAiohttpMethod

    def __init__(
        self,
        url: str,
        token: str = "",
        ssl_context: SSLContext | None = None,
    ):
        url = url.rstrip("/") + "/api/"

        connector = TCPConnector(ssl=ssl_context)
        session = ClientSession(connector=connector)
        if token:
            session.headers["Authorization"] = f"Token {token}"
        super().__init__(url, session)

    async def close(self):
        await self.session.close()


class NetboxStatusClient(BaseNetboxClient):
    def _init_response_body_factory(self) -> FactoryProtocol:
        return Retort(recipe=[name_mapping(name_style=NameStyle.LOWER_KEBAB)])

    @get("status")
    async def status(self) -> Status: ...
