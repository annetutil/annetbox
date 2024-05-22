from dataclasses import dataclass
from typing import Generic, TypeVar

Model = TypeVar("Model")


@dataclass
class Status:
    netbox_version: str
    plugins: dict[str, str]


@dataclass
class PagingResponse(Generic[Model]):
    next: str | None
    previous: str | None
    count: int
    results: list[Model]
