import http
from collections.abc import Callable
from functools import wraps
from ssl import SSLContext
from typing import Any, Concatenate, ParamSpec, TypeVar

from adaptix import NameStyle, Retort, name_mapping
from dataclass_rest import get
from dataclass_rest.client_protocol import FactoryProtocol
from dataclass_rest.http.requests import RequestsClient, RequestsMethod
from requests import Response, Session
from requests.adapters import HTTPAdapter

from .exceptions import ClientWithBodyError, ServerWithBodyError
from .models import Model, PagingResponse, Status

Class = TypeVar("Class")
ArgsSpec = ParamSpec("ArgsSpec")


def _collect_by_pages(
    func: Callable[Concatenate[Class, ArgsSpec], PagingResponse[Model]],
) -> Callable[Concatenate[Class, ArgsSpec], PagingResponse[Model]]:
    """Collect all results using only pagination."""

    @wraps(func)
    def wrapper(
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
            page = method(*args, **kwargs)
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
    func: Callable[Concatenate[Class, ArgsSpec], PagingResponse[Model]],
    field: str = "",
    batch_size: int = 100,
) -> Callable[Concatenate[Class, ArgsSpec], PagingResponse[Model]]:
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
    def wrapper(
        self: Class,
        *args: ArgsSpec.args,
        **kwargs: ArgsSpec.kwargs,
    ) -> PagingResponse[Model]:
        method = func.__get__(self, self.__class__)

        value = kwargs.get(field)
        if value is None:
            return method(*args, **kwargs)
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
            page = method(*args, **kwargs)
            results.extend(page.results)
        return PagingResponse(
            previous=None,
            next=None,
            count=len(results),
            results=results,
        )

    return wrapper


class NoneAwareRequestsMethod(RequestsMethod):
    def _on_error_default(self, response: Response) -> Any:
        body = self._response_body(response)
        if http.HTTPStatus.BAD_REQUEST <= response.status_code \
                                       < http.HTTPStatus.INTERNAL_SERVER_ERROR:
            raise ClientWithBodyError(response.status_code, body=body)
        raise ServerWithBodyError(response.status_code, body=body)

    def _response_body(self, response: Response) -> Any:
        if response.status_code == http.HTTPStatus.NO_CONTENT:
            return None
        return super()._response_body(response)


class CustomHTTPAdapter(HTTPAdapter):
    def __init__(
        self,
        ssl_context: SSLContext | None = None,
        timeout: int = 30,
    ) -> None:
        self.ssl_context = ssl_context
        self.timeout = timeout
        super().__init__()

    def send(self, request, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return super().send(request, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        if self.ssl_context is not None:
            kwargs.setdefault("ssl_context", self.ssl_context)
        super().init_poolmanager(*args, **kwargs)


class BaseNetboxClient(RequestsClient):
    method_class = NoneAwareRequestsMethod

    def __init__(
        self,
        url: str,
        token: str = "",
        ssl_context: SSLContext | None = None,
    ):
        url = url.rstrip("/") + "/api/"

        adapter = CustomHTTPAdapter(
            ssl_context=ssl_context,
            timeout=300,
        )
        session = Session()
        if ssl_context and not ssl_context.check_hostname:
            session.verify = False
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        if token:
            session.headers["Authorization"] = f"Token {token}"
        super().__init__(url, session)


class NetboxStatusClient(BaseNetboxClient):
    def _init_response_body_factory(self) -> FactoryProtocol:
        return Retort(recipe=[name_mapping(name_style=NameStyle.LOWER_KEBAB)])

    @get("status")
    def status(self) -> Status: ...
