from annetbox.base.models import PagingResponse


class Data:
    def __init__(self, max: int) -> None:
        self.max = max

    def items(
            self,
            ids: list[int] | None = None,
            offset: int = 0,
            limit: int = 10,
    ) -> PagingResponse[int]:
        if ids is None:
            all_data = range(self.max)
        else:
            all_data = [x for x in ids if x in range(self.max)]
        data = all_data[offset:offset + limit]
        count = len(data)
        next_page = (offset + limit) < len(all_data)
        return PagingResponse(
            results=data,
            next="+++" if next_page else None,
            previous=None,
            count=count,
        )
