from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import aiohttp

from ._utils import new_device_id, parse_cookies
from .exceptions import ApiError


DEFAULT_TIMEOUT = 30.0
REQUEST_TIMEOUT_CODE = "TIMEOUT"
NETWORK_ERROR_CODE = "NETWORK_ERROR"
INVALID_RESPONSE_CODE = "INVALID_RESPONSE"


class _HTTPClient:
    def __init__(
        self,
        *,
        origin: str,
        access_token: str | None = None,
        cookies: str | Mapping[str, str] | None = None,
        device_id: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        headers: Mapping[str, str] | None = None,
        auto_refresh: bool = True,
    ) -> None:
        self.origin = origin.rstrip("/")
        self.api_base = f"{self.origin}/api"
        self.auth_base = f"{self.origin}/api/v1/auth"
        self.access_token = access_token
        self.device_id = device_id or new_device_id()
        self.timeout = timeout
        self.auto_refresh = auto_refresh
        self._base_headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        if headers:
            self._base_headers.update(headers)

        self._cookie_store = parse_cookies(cookies)
        self._client: aiohttp.ClientSession | None = None
        self._refresh_lock: asyncio.Lock | None = None

    async def open(self) -> None:
        await self._ensure_client()

    async def close(self) -> None:
        if self._client is not None and not self._client.closed:
            await self._client.close()
        self._client = None

    def set_access_token(self, access_token: str | None) -> None:
        self.access_token = access_token

    def set_cookies(self, cookies: str | Mapping[str, str]) -> None:
        parsed = parse_cookies(cookies)
        self._cookie_store.update(parsed)
        if self._client is not None:
            self._client.cookie_jar.update_cookies(parsed)

    async def request_api(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        files: Any | None = None,
        timeout: float | None = None,
        retry: bool = True,
    ) -> Any:
        return await self._request(
            base_url=self.api_base,
            method=method,
            path=path,
            json=json,
            params=params,
            headers=headers,
            files=files,
            timeout=timeout,
            retry=retry,
        )

    async def request_auth(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        return await self._request(
            base_url=self.auth_base,
            method=method,
            path=path,
            json=json,
            params=params,
            headers=headers,
            files=None,
            timeout=timeout,
            retry=False,
        )

    async def try_refresh_session(self) -> bool:
        if self._refresh_lock is None:
            self._refresh_lock = asyncio.Lock()

        async with self._refresh_lock:
            try:
                payload = await self.request_auth("POST", "/refresh")
            except ApiError:
                self.access_token = None
                return False

            if isinstance(payload, dict) and payload.get("accessToken"):
                self.access_token = str(payload["accessToken"])
                return True
            return False

    async def _ensure_client(self) -> aiohttp.ClientSession:
        if self._client is None or self._client.closed:
            self._client = aiohttp.ClientSession(
                headers={"User-Agent": "itd-sdk/0.1.0"},
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                raise_for_status=False,
            )
            if self._cookie_store:
                self._client.cookie_jar.update_cookies(self._cookie_store)
        return self._client

    async def _request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        json: dict[str, Any] | None,
        params: Mapping[str, Any] | None,
        headers: Mapping[str, str] | None,
        files: Any | None,
        timeout: float | None,
        retry: bool,
    ) -> Any:
        client = await self._ensure_client()
        url = self._build_url(base_url, path)
        request_headers = self._build_headers(headers, include_content_type=files is None)
        request_timeout = aiohttp.ClientTimeout(total=timeout or self.timeout)
        data = self._build_form_data(files) if files is not None else None

        try:
            async with client.request(
                method=method.upper(),
                url=url,
                json=json if files is None else None,
                params=params,
                headers=request_headers,
                data=data,
                timeout=request_timeout,
            ) as response:
                if (
                    response.status == 401
                    and retry
                    and self.auto_refresh
                    and base_url == self.api_base
                    and self.access_token
                    and await self.try_refresh_session()
                ):
                    return await self._request(
                        base_url=base_url,
                        method=method,
                        path=path,
                        json=json,
                        params=params,
                        headers=headers,
                        files=files,
                        timeout=timeout,
                        retry=False,
                    )

                return await self._handle_response(response)
        except asyncio.TimeoutError as exc:
            raise ApiError(0, "Request timeout", REQUEST_TIMEOUT_CODE) from exc
        except aiohttp.ClientError as exc:
            raise ApiError(0, str(exc) or "Network error", NETWORK_ERROR_CODE) from exc

    def _build_url(self, base_url: str, path: str) -> str:
        base = base_url.rstrip("/")
        suffix = path if path.startswith("/") else f"/{path}"
        return f"{base}{suffix}"

    def _build_headers(
        self,
        headers: Mapping[str, str] | None,
        *,
        include_content_type: bool,
    ) -> dict[str, str]:
        merged = dict(self._base_headers)
        if not include_content_type:
            merged.pop("Content-Type", None)
        if headers:
            merged.update(headers)
        merged["X-Device-Id"] = self.device_id
        if self.access_token:
            merged["Authorization"] = f"Bearer {self.access_token}"
        return merged

    def _build_form_data(self, files: Any) -> aiohttp.FormData:
        form = aiohttp.FormData()
        for field_name, value in files.items():
            if isinstance(value, tuple):
                filename = value[0] if len(value) > 0 else field_name
                file_value = value[1] if len(value) > 1 else None
                content_type = value[2] if len(value) > 2 else None
                kwargs: dict[str, Any] = {}
                if filename is not None:
                    kwargs["filename"] = filename
                if content_type is not None:
                    kwargs["content_type"] = content_type
                form.add_field(field_name, file_value, **kwargs)
            else:
                form.add_field(field_name, value)
        return form

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        if response.status == 204:
            return None

        try:
            payload = await response.json(content_type=None)
        except Exception:
            text = (await response.text()).strip()
            if response.status >= 400:
                raise ApiError(
                    response.status,
                    text or "Invalid response format",
                    INVALID_RESPONSE_CODE,
                    payload=text,
                )
            return text or None

        if response.status >= 400:
            error_payload = payload.get("error") if isinstance(payload, dict) else None
            body = error_payload if isinstance(error_payload, dict) else payload

            errors = None
            if isinstance(body, dict):
                errors = body.get("errors")
                violations = body.get("violations")
                if isinstance(violations, list):
                    errors = {}
                    for item in violations:
                        field = item.get("field", "non_field_errors")
                        errors.setdefault(field, []).append(item.get("message", "Invalid value"))

            message = "Request failed"
            code = self._map_status_code(response.status)
            if isinstance(body, dict):
                message = body.get("detail") or body.get("message") or body.get("title") or message
                code = body.get("code") or code

            raise ApiError(
                response.status,
                message,
                code,
                errors=errors,
                payload=payload,
            )

        return payload

    def _map_status_code(self, status_code: int) -> str:
        mapping = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "ACCESS_DENIED",
            404: "ENTITY_NOT_FOUND",
            409: "ENTITY_ALREADY_EXISTS",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
        }
        return mapping.get(status_code, "UNKNOWN_ERROR")
