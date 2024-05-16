from dataclasses import dataclass
from typing import Generic, TypeVar

Model = TypeVar("Model")


@dataclass
class PagingResponse(Generic[Model]):
    next: str | None
    previous: str | None
    count: int
    results: list[Model]
