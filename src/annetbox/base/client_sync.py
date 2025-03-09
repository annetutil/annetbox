import http
import logging
import os
import urllib.parse
from abc import abstractmethod
from collections.abc import Callable, Iterable
from functools import wraps
from multiprocessing.pool import ThreadPool
from ssl import SSLContext
from typing import Any, Concatenate, ParamSpec, Protocol, TypeVar

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
default_page_size = int(os.getenv("NETBOX_PAGE_SIZE", 100))
# rfc9110:
# It is RECOMMENDED that all senders and recipients support, at a minimum,
# URIs with lengths of 8000 octets in protocol elements
max_url_size = int(os.getenv("NETBOX_MAX_URL_SIZE", 8000))
logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class _BasePool(Protocol):
    @abstractmethod
    def map(
            self, func: Callable[[T], R], iterable: Iterable[T],
    ) -> Iterable[R]:
        raise NotImplementedError


class FakePool(_BasePool):
    def map(
            self, func: Callable[[T], R], iterable: Iterable[T],
    ) -> Iterable[R]:
        for item in iterable:
            yield func(item)


def split_by_len(pref_len: int, max_batch_len: int, data: list[Any]) -> list[list[Any]]:
    res = []
    current_batch = []
    current_batch_len = 0
    if not len(data):
        return res
    for item in data:
        item_len = len(urllib.parse.quote_plus(str(item))) + pref_len
        if current_batch_len + item_len > max_batch_len:
            current_batch = []
            current_batch_len = item_len
            res.append(current_batch)
        else:
            current_batch_len += item_len
            current_batch.append(item)
    res.append(current_batch)
    return res


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
        page_size = kwargs.pop("page_size", default_page_size)
        limit = kwargs.pop("limit", None)
        results = []
        method = func.__get__(self, self.__class__)
        has_next = True
        while has_next:
            if limit is None:
                kwargs["limit"] = page_size
            else:
                kwargs["limit"] = min(limit - kwargs["offset"], page_size)
            page = method(*args, **kwargs)
            kwargs["offset"] += page_size
            results.extend(page.results)
            if limit is None:
                has_next = bool(page.next)
            else:
                has_next = kwargs["offset"] < limit
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

        max_len = max_url_size - 200  # minus base url, TODO: calc using real base URL
        batches = split_by_len(len(field)+2, max_len, value)  # +1 for equal sign, +1 for &

        def apply(batch: list[Any]):
            nonlocal kwargs
            kwargs = kwargs.copy()
            kwargs[field] = batch
            return method(*args, **kwargs)

        results = []
        for page in self.pool.map(apply, batches):
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
        pool_connections: int = 10,
        pool_maxsize: int = 10,
    ) -> None:
        self.ssl_context = ssl_context
        self.timeout = timeout
        super().__init__(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
        )

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
        threads: int = 1,
    ):
        url = url.rstrip("/") + "/api/"
        session = self._init_session(ssl_context, threads)
        self.pool = self._init_pool(threads)

        if token:
            session.headers["Authorization"] = f"Token {token}"
        super().__init__(url, session)

    def _init_session(
        self,
        ssl_context: SSLContext | None = None,
        pool_connections: int = 1,
    ) -> Session:
        adapter = CustomHTTPAdapter(
            ssl_context=ssl_context,
            timeout=300,
            pool_connections=pool_connections,
            pool_maxsize=pool_connections,
        )
        session = Session()
        if ssl_context and not ssl_context.check_hostname:
            session.verify = False
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _init_pool(self, threads: int) -> _BasePool:
        if threads > 1:
            return ThreadPool(processes=threads)
        return FakePool()


class NetboxStatusClient(BaseNetboxClient):
    def _init_response_body_factory(self) -> FactoryProtocol:
        return Retort(recipe=[name_mapping(name_style=NameStyle.LOWER_KEBAB)])

    @get("status")
    def status(self) -> Status: ...
