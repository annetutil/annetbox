import re
from dataclasses import dataclass
from typing import Generic, TypeVar

Model = TypeVar("Model")


@dataclass
class Status:
    netbox_version: str
    plugins: dict[str, str]

    @property
    def minor_version(self) -> str:
        """Major and minor part of the version, for example `4.2`."""
        if match := re.match(r"\d+\.\d+", self.netbox_version):
            return match.group(0)
        return ""


@dataclass
class PagingResponse(Generic[Model]):
    next: str | None
    previous: str | None
    count: int
    results: list[Model]
