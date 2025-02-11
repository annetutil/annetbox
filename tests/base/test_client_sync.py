from unittest.mock import Mock

from annetbox.base.client_sync import FakePool, collect
from annetbox.base.models import PagingResponse
from .data import Data


class FakeClient:
    def __init__(self):
        self.data = Data(100)
        self.items_mock = Mock()
        self.pool = FakePool()

    def page(self, offset: int = 0, limit: int = 10) -> PagingResponse[int]:
        return self.data.items(None, offset=offset, limit=limit)

    all = collect(page)

    def items(
        self,
        ids: list[int] | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> PagingResponse[int]:
        self.items_mock()
        return self.data.items(ids, offset=offset, limit=limit)

    all_items = collect(items, field="ids", batch_size=2)


def test_collect_all():
    client = FakeClient()
    res = client.all(limit=10)
    assert res.count == 10
    assert res.next is None
    assert res.results == list(range(10))


def test_collect_by_field():
    client = FakeClient()
    ids = [1, 2, 3, 4, 5]
    res = client.all_items(ids=ids)
    assert res.next is None
    assert res.results == ids
    assert client.items_mock.call_count == 3


def test_collect_by_missing_filter():
    client = FakeClient()
    res = client.all_items()
    assert res.next is None
    assert res.results == list(range(100))
    assert client.items_mock.call_count == 1


def test_collect_by_empty_field():
    client = FakeClient()
    res = client.all_items(ids=[])
    assert res.next is None
    assert res.results == []
    assert client.items_mock.call_count == 0
