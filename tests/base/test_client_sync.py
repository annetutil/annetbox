from annetbox.base.client_sync import collect
from annetbox.base.models import PagingResponse


class FakeClient:
    def page(self, offset: int = 0, limit: int = 10) -> PagingResponse[int]:
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


def test_collect_all():
    client = FakeClient()
    res = client.all(limit=10)
    assert res.count == 100
    assert res.next is None
    assert res.results == list(range(100))
