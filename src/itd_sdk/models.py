from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class Page(Generic[T]):
    items: list[T]
    next_cursor: str | None = None


class SDKObject(Mapping[str, Any]):
    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, Any] | None = None, /, **kwargs: Any) -> None:
        payload: dict[str, Any] = {}
        if data:
            payload.update(data)
        if kwargs:
            payload.update(kwargs)
        object.__setattr__(self, "_data", {key: to_model(value) for key, value in payload.items()})

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __repr__(self) -> str:
        return f"SDKObject({self._data!r})"

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return from_model(self._data)


def to_model(value: Any) -> Any:
    if isinstance(value, SDKObject):
        return value
    if isinstance(value, Mapping):
        return SDKObject(value)
    if isinstance(value, list):
        return [to_model(item) for item in value]
    if isinstance(value, tuple):
        return tuple(to_model(item) for item in value)
    return value


def from_model(value: Any) -> Any:
    if isinstance(value, SDKObject):
        return {key: from_model(item) for key, item in value.items()}
    if isinstance(value, list):
        return [from_model(item) for item in value]
    if isinstance(value, tuple):
        return [from_model(item) for item in value]
    if isinstance(value, dict):
        return {key: from_model(item) for key, item in value.items()}
    return value
