"""HTTP boundary for Spoolman."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


class TagScanRequest(BaseModel):
    """The tag scan contract accepted by Spoolman 0.27+."""

    model_config = ConfigDict(extra="forbid")
    uid: str = Field(min_length=1, max_length=128)
    reader_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._:-]{1,64}$")
    name: str | None = Field(default=None, max_length=64)
    format: str | None = Field(default=None, max_length=32)
    payload_b64: str | None = Field(default=None, max_length=8192)


class TagScanError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class SpoolmanClient:
    """Small async client that owns Spoolman URLs, credentials, and timeouts."""

    def __init__(
        self,
        base_url: str,
        api_token: str = "",
        *,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.client_factory = client_factory

    def auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def get_spools(self) -> list[dict[str, Any]]:
        async with self.client_factory(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(f"{self.base_url}/api/v1/spool", headers=self.auth_headers())
            response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    async def get_spool(self, spool_id: int) -> dict[str, Any]:
        async with self.client_factory(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(f"{self.base_url}/api/v1/spool/{spool_id}", headers=self.auth_headers())
            response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    async def update_spool_location(self, spool_id: int, location: str) -> httpx.Response:
        async with self.client_factory(timeout=15.0, follow_redirects=True) as client:
            return await client.patch(
                f"{self.base_url}/api/v1/spool/{spool_id}",
                headers=self.auth_headers(),
                json={"location": location},
            )

    async def scan_tag(
        self,
        scan: TagScanRequest,
        *,
        headers: dict[str, str] | None = None,
    ) -> int | None:
        try:
            async with self.client_factory(timeout=10.0, follow_redirects=False) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/tag/scan",
                    headers=headers or self.auth_headers(),
                    json=scan.model_dump(exclude_none=True),
                )
        except httpx.RequestError:
            raise TagScanError(502, "Could not reach Spoolman. Check its connection, then scan again.") from None

        if response.status_code in {404, 405, 501}:
            raise TagScanError(502, "Tag scanning requires Spoolman 0.27+ with /api/v1/tag/scan available. Check the version and server address; QR scanning remains available.")
        if response.status_code in {401, 403}:
            raise TagScanError(502, "Spoolman denied tag scanning. Check the configured API credentials and proxy permissions.")
        if response.status_code in {400, 422}:
            raise TagScanError(400, "Spoolman rejected the scan. Check the hardware UID and reader details, then scan again.")
        if response.status_code != 200:
            raise TagScanError(502, "Spoolman could not resolve this tag. Try scanning again when the service is available.")

        try:
            result = response.json()
        except ValueError:
            raise TagScanError(502, "Spoolman returned an invalid tag-scan response. No spool was selected.") from None
        if not isinstance(result, dict) or "matched_spool_id" not in result:
            raise TagScanError(502, "Spoolman returned no tag match result. No spool was selected.")
        spool_id = result["matched_spool_id"]
        if spool_id is not None and (type(spool_id) is not int or spool_id <= 0):
            raise TagScanError(502, "Spoolman returned an invalid spool identity. No spool was selected.")
        return spool_id
