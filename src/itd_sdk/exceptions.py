from __future__ import annotations

from typing import Any


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        code: str,
        *,
        errors: dict[str, list[str]] | dict[str, Any] | None = None,
        payload: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code
        self.errors = errors
        self.payload = payload

    def __str__(self) -> str:
        return f"{self.status_code} {self.code}: {self.message}"
