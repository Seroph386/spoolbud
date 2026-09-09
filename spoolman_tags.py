"""Compatibility imports for the Spoolman tag lookup contract."""
from __future__ import annotations

import httpx
from spoolbud.clients.spoolman import (
    DuplicateTagUIDError,
    SpoolmanClient,
    TagLookupError,
    TagScanError,
    TagScanRequest,
)


async def resolve_tag(scan: TagScanRequest, *, base_url: str, headers: dict[str, str]) -> int | None:
    """Delegate legacy callers to the version-compatible tag resolver."""
    return await SpoolmanClient(base_url, client_factory=httpx.AsyncClient).scan_tag(scan, headers=headers)
