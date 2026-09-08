"""Spoolman owns UID normalization and matching; this module only relays scans."""
from __future__ import annotations

import httpx
from pydantic import BaseModel, ConfigDict, Field


class TagScanRequest(BaseModel):
    # Bounds follow Spoolman's tag API. Do not accept a client-provided match.
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


async def resolve_tag(scan: TagScanRequest, *, base_url: str, headers: dict[str, str]) -> int | None:
    """Return only Spoolman's explicit match. Never decode or cache tag identity."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/v1/tag/scan",
                headers=headers,
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
