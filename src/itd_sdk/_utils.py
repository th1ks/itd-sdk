from __future__ import annotations

from collections.abc import Mapping
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4


def new_device_id() -> str:
    return str(uuid4())


def drop_none(data: Mapping[str, Any] | None = None, /, **kwargs: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if data:
        payload.update(data)
    for key, value in kwargs.items():
        if value is not None:
            payload[key] = value
    return payload


def parse_cookies(cookies: str | Mapping[str, str] | None) -> dict[str, str]:
    if cookies is None:
        return {}
    if isinstance(cookies, Mapping):
        return {str(key): str(value) for key, value in cookies.items()}

    parsed = SimpleCookie()
    parsed.load(cookies)
    if parsed:
        return {key: morsel.value for key, morsel in parsed.items()}

    # Fallback: if the caller passed a raw token instead of a cookie header,
    # treat it as empty here and let them pass it via access_token.
    return {}


def to_query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_query(params: Mapping[str, Any] | None = None, /, **kwargs: Any) -> dict[str, str]:
    merged = drop_none(params, **kwargs)
    return {key: to_query_value(value) for key, value in merged.items()}


def unwrap_data(payload: Any) -> Any:
    if isinstance(payload, Mapping) and payload.get("data") is not None:
        return payload["data"]
    return payload


def build_upload_file(
    file: str | Path | bytes | BinaryIO,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> tuple[tuple[str, Any, str | None], BinaryIO | None]:
    if isinstance(file, (str, Path)):
        path = Path(file)
        opened = path.open("rb")
        effective_name = filename or path.name
        return (effective_name, opened, content_type), opened

    if isinstance(file, bytes):
        effective_name = filename or "upload.bin"
        return (effective_name, file, content_type), None

    effective_name = filename or Path(getattr(file, "name", "upload.bin")).name
    return (effective_name, file, content_type), None
