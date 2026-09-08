"""Small runtime dependency boundary shared by route modules."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, Request, Response

from spoolbud.clients.spoolman import SpoolmanClient, TagScanRequest
from spoolbud.config import settings
from spoolbud.parsing.spool_ids import extract_spool_id
from spoolbud.services.bins import (
    configured_bins as build_configured_bins,
    get_bin_contents,
    get_spoolman_locations,
    move_selected_spool_to_bin,
)
from spoolbud.services.spool_selection import clear_selected_spool, get_selected_spool, set_selected_spool
from spoolman_tags import resolve_tag


# Module aliases keep tests and transitional deployments easy to configure.
SPOOLMAN_BASE = settings.spoolman_base
API_TOKEN = settings.spoolman_api_token
COOKIE_NAME = settings.cookie_name
COOKIE_MAX_AGE = settings.cookie_max_age
DESTINATIONS = settings.destinations


def client() -> SpoolmanClient:
    return SpoolmanClient(SPOOLMAN_BASE, API_TOKEN)


def spool_url(spool_id: int) -> str:
    return f"{SPOOLMAN_BASE}/spool/show/{spool_id}"


def configured_bins() -> list[str]:
    return build_configured_bins(DESTINATIONS)


def selected_spool_id(request: Request | None) -> int | None:
    return get_selected_spool(request, cookie_name=COOKIE_NAME, parser=extract_spool_id)


def require_selection(request: Request, expected_spool_id: int) -> None:
    if selected_spool_id(request) != expected_spool_id:
        raise HTTPException(409, "Spool selection changed or was cleared. Scan your spool again before continuing.")


def clear_selection(response: Response) -> Response:
    return clear_selected_spool(response, cookie_name=COOKIE_NAME)


def set_selection(response: Response, spool_id: int) -> Response:
    return set_selected_spool(response, spool_id, cookie_name=COOKIE_NAME, max_age=COOKIE_MAX_AGE)


async def fetch_spoolman_spools() -> list[dict[str, Any]]:
    return await client().get_spools()


async def fetch_spoolman_spool(spool_id: int) -> dict[str, Any]:
    return await client().get_spool(spool_id)


async def fetch_spoolman_locations() -> list[str]:
    return await get_spoolman_locations(fetch_spoolman_spools)


async def fetch_spools_in_location(location: str) -> list[dict[str, Any]]:
    return await get_bin_contents(location, fetch_spoolman_spools)


async def patch_spool_location(spool_id: int, location: str) -> httpx.Response:
    return await client().update_spool_location(spool_id, location)


async def move_selected_spool(request: Request, spool_id: int, location: str) -> str:
    return await move_selected_spool_to_bin(
        request,
        spool_id,
        location,
        get_selection=selected_spool_id,
        update_location=patch_spool_location,
    )


async def resolve_tag_scan(scan: TagScanRequest) -> int | None:
    return await resolve_tag(scan, base_url=SPOOLMAN_BASE, headers=client().auth_headers())
