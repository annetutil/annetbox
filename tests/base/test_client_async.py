from unittest.mock import Mock

import pytest

from annetbox.base.client_async import collect
from annetbox.base.models import PagingResponse


class FakeClient:
    def __init__(self):
        self.items_mock = Mock()

    async def page(
        self,
        offset: int = 0,
        limit: int = 10,
    ) -> PagingResponse[int]:
        if offset >= 100:
            return PagingResponse(
                results=[],
                next=None,
                previous=None,
                count=0,
            )
        return PagingResponse(
            results=list(range(offset, offset + limit)),
            next="offset + limit",
            previous=None,
            count=limit,
        )

    all = collect(page)

    async def items(
        self,
        ids: list[int] | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> PagingResponse[int]:
        if ids is None:
            self.items_mock(ids)
            return PagingResponse(
                results=[1, 2],
                next=None,
                previous=None,
                count=limit,
            )
        if offset > len(ids):
            return PagingResponse(
                results=[],
                next=None,
                previous=None,
                count=0,
            )
        self.items_mock(ids)
        return PagingResponse(
            results=ids,
            next="offset + limit",
            previous=None,
            count=limit,
        )

    all_items = collect(items, field="ids", batch_size=2)


@pytest.mark.asyncio
async def test_collect_all():
    client = FakeClient()
    res = await client.all(limit=10)
    assert res.count == 100
    assert res.next is None
    assert res.results == list(range(100))


@pytest.mark.asyncio
async def test_collect_by_missing_filter():
    client = FakeClient()
    res = await client.all_items()
    assert res.next is None
    assert res.results == [1, 2]
    assert client.items_mock.call_count == 1


@pytest.mark.asyncio
async def test_collect_by_empty_field():
    client = FakeClient()
    res = await client.all_items(ids=[])
    assert res.next is None
    assert res.results == []
    assert client.items_mock.call_count == 0
