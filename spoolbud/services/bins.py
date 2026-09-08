"""Bin names, contents, and move workflow operations."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import HTTPException, Request


LOCATION_KEYS = ("location", "bin", "storage_location")
EXTRA_LOCATION_KEYS = ("location", "bin")


def normalize_location(location: str) -> str:
    return location.strip().upper()


def default_bins() -> list[str]:
    front = [f"F-{index:03d}" for index in range(1, 21)]
    back = [f"B-{index:03d}" for index in range(1, 5)]
    return front + back


def configured_bins(destinations: str) -> list[str]:
    configured = {normalize_location(value) for value in re.split(r"[,\n]", destinations) if value.strip()}
    return sorted(configured) or default_bins()


def spool_location_values(spool: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in LOCATION_KEYS:
        value = spool.get(key)
        if value:
            values.add(normalize_location(str(value)))

    extra = spool.get("extra")
    if isinstance(extra, dict):
        for key in EXTRA_LOCATION_KEYS:
            value = extra.get(key)
            if value:
                values.add(normalize_location(str(value)))
    return values


def spools_in_location(spools: list[dict[str, Any]], location: str) -> list[dict[str, Any]]:
    normalized = normalize_location(location)
    return [spool for spool in spools if normalized in spool_location_values(spool)]


async def get_spoolman_locations(
    fetch_spools: Callable[[], Awaitable[list[dict[str, Any]]]],
) -> list[str]:
    locations: set[str] = set()
    for spool in await fetch_spools():
        locations.update(spool_location_values(spool))
    return sorted(locations)


async def get_bin_contents(
    location: str,
    fetch_spools: Callable[[], Awaitable[list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    return spools_in_location(await fetch_spools(), location)


async def move_selected_spool_to_bin(
    request: Request,
    spool_id: int,
    location: str,
    *,
    get_selection: Callable[[Request], int | None],
    update_location: Callable[[int, str], Awaitable[httpx.Response]],
) -> str:
    if get_selection(request) != spool_id:
        raise HTTPException(409, "Spool selection changed or was cleared. Scan your spool again before continuing.")

    normalized = normalize_location(location)
    if not normalized or len(normalized) > 200:
        raise HTTPException(400, "Choose a destination between 1 and 200 characters long.")
    try:
        response = await update_location(spool_id, normalized)
        response.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(502, "Spoolman could not confirm the move. Check the spool's location and connection, then try again.") from None
    return normalized
