import http
from collections.abc import Awaitable, Callable
from functools import wraps
from ssl import SSLContext
from typing import Any, Concatenate, ParamSpec, TypeVar

from adaptix import NameStyle, Retort, name_mapping
from aiohttp import ClientResponse, ClientSession, TCPConnector
from dataclass_rest import get
from dataclass_rest.client_protocol import FactoryProtocol
from dataclass_rest.http.aiohttp import AiohttpClient, AiohttpMethod
from dataclass_rest.http_request import HttpRequest

from .exceptions import ClientWithBodyError, ServerWithBodyError
from .models import Model, PagingResponse, Status

Class = TypeVar("Class")
ArgsSpec = ParamSpec("ArgsSpec")


def _collect_by_pages(
    func: Callable[
        Concatenate[Class, ArgsSpec],
        Awaitable[PagingResponse[Model]],
    ],
) -> Callable[Concatenate[Class, ArgsSpec], Awaitable[PagingResponse[Model]]]:
    """Collect all results using only pagination."""

    @wraps(func)
    async def wrapper(
        self: Class,
        *args: ArgsSpec.args,
        **kwargs: ArgsSpec.kwargs,
    ) -> PagingResponse[Model]:
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
def collect(
    func: Callable[
        Concatenate[Class, ArgsSpec],
        Awaitable[PagingResponse[Model]],
    ],
    field: str = "",
    batch_size: int = 100,
) -> Callable[Concatenate[Class, ArgsSpec], Awaitable[PagingResponse[Model]]]:
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
    async def wrapper(
        self: Class,
        *args: ArgsSpec.args,
        **kwargs: ArgsSpec.kwargs,
    ) -> PagingResponse[Model]:
        method = func.__get__(self, self.__class__)

        value = kwargs.get(field)
        if value is None:
            return await method(*args, **kwargs)
        elif not value:
            return PagingResponse(
                previous=None,
                next=None,
                count=0,
                results=[],
            )

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
    async def _on_error_default(self, response: ClientResponse) -> Any:
        body = await self._response_body(response)
        if http.HTTPStatus.BAD_REQUEST <= response.status \
                                       < http.HTTPStatus.INTERNAL_SERVER_ERROR:
            raise ClientWithBodyError(response.status, body=body)
        raise ServerWithBodyError(response.status, body=body)

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
