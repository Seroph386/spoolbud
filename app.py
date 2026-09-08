from __future__ import annotations

from typing import Any

import httpx
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import ValidationError

from spoolbud.config import settings
from spoolbud.clients.spoolman import SpoolmanClient
from spoolbud.parsing.spool_ids import extract_spool_id
from spoolbud.rendering.components import (
    render_page as build_page,
    render_spool_cards as build_spool_cards,
    spool_color_hex,
    spool_summary,
)
from spoolbud.rendering.pages import (
    render_bin_contents,
    render_bin_lookup_failed,
    render_bins,
    render_empty_bin,
    render_home,
    render_move_error as render_move_error_page,
    render_no_selection,
    render_selected_spool as render_selected_spool_page,
    render_spool_moved,
    render_spools,
)
from spoolbud.services.spool_selection import clear_selected_spool, get_selected_spool, set_selected_spool
from spoolbud.services.qr import render_qr_svg
from spoolbud.services.bins import (
    configured_bins as build_configured_bins,
    default_bins,
    get_bin_contents,
    get_spoolman_locations,
    move_selected_spool_to_bin,
    normalize_location,
    spool_location_values,
    spools_in_location,
)
from spoolman_tags import TagScanError, TagScanRequest, resolve_tag

# Compatibility aliases remain while responsibilities move into the package.
SPOOLMAN_BASE = settings.spoolman_base
API_TOKEN = settings.spoolman_api_token
COOKIE_NAME = settings.cookie_name
COOKIE_MAX_AGE = settings.cookie_max_age
DESTINATIONS = settings.destinations

app = FastAPI(title="SpoolBud Helper")

def wants_scan_stay(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def spool_url(spool_id: int) -> str:
    return f"{SPOOLMAN_BASE}/spool/show/{spool_id}"


def configured_bins() -> list[str]:
    return build_configured_bins(DESTINATIONS)


def auth_headers() -> dict[str, str]:
    return SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).auth_headers()


def selected_spool_id(request: Request | None) -> int | None:
    return get_selected_spool(request, cookie_name=COOKIE_NAME, parser=extract_spool_id)


def render_page(
    title: str,
    body: str,
    *,
    request: Request | None = None,
    active_nav: str = "home",
    status_code: int = 200,
) -> HTMLResponse:
    return build_page(
        title,
        body,
        current_spool_id=selected_spool_id(request),
        spoolman_base=SPOOLMAN_BASE,
        active_nav=active_nav,
        status_code=status_code,
    )


def render_spool_cards(spools: list[dict[str, Any]], *, compact: bool = False) -> str:
    return build_spool_cards(spools, spoolman_base=SPOOLMAN_BASE, compact=compact)


async def fetch_spoolman_spools() -> list[dict[str, Any]]:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).get_spools()


async def fetch_spoolman_spool(spool_id: int) -> dict[str, Any]:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).get_spool(spool_id)


async def fetch_spoolman_locations() -> list[str]:
    return await get_spoolman_locations(fetch_spoolman_spools)


async def fetch_spools_in_location(location: str) -> list[dict[str, Any]]:
    return await get_bin_contents(location, fetch_spoolman_spools)


async def patch_spool_location(spool_id: int, location: str) -> httpx.Response:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).update_spool_location(spool_id, location)


def require_selection(request: Request, expected_spool_id: int) -> None:
    if selected_spool_id(request) != expected_spool_id:
        raise HTTPException(409, "Spool selection changed or was cleared. Scan your spool again before continuing.")


async def move_selected_spool(request: Request, spool_id: int, location: str) -> str:
    return await move_selected_spool_to_bin(
        request,
        spool_id,
        location,
        get_selection=selected_spool_id,
        update_location=patch_spool_location,
    )


def clear_selection(response: Response) -> Response:
    return clear_selected_spool(response, cookie_name=COOKIE_NAME)


def set_selection(response: Response, spool_id: int) -> Response:
    return set_selected_spool(response, spool_id, cookie_name=COOKIE_NAME, max_age=COOKIE_MAX_AGE)


@app.post("/api/tag/scan")
async def scan_tag(request: Request):
    # Validate here so even malformed scans clear an older pending selection.
    try:
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise ValueError("Expected JSON")
        scan = TagScanRequest.model_validate(await request.json())
    except (ValueError, ValidationError):
        return clear_selection(JSONResponse({"detail": "Send a JSON scan with a hardware UID and valid reader details. No spool was selected."}, status_code=400))
    try:
        spool_id = await resolve_tag(scan, base_url=SPOOLMAN_BASE, headers=auth_headers())
    except TagScanError as exc:
        return clear_selection(JSONResponse({"detail": str(exc)}, status_code=exc.status_code))
    if spool_id is None:
        return clear_selection(JSONResponse({"matched_spool_id": None, "detail": "This tag is not linked to a spool. Link it in Spoolman, then scan again."}))
    return set_selection(JSONResponse({"matched_spool_id": spool_id}), spool_id)


@app.post("/api/move")
async def move_spool(request: Request, spool_id: int = Body(gt=0), location: str = Body()):
    location = await move_selected_spool(request, spool_id, location)
    return clear_selection(JSONResponse({"spool_id": spool_id, "location": location}))


@app.post("/api/selection/clear")
def cancel_selection(request: Request, spool_id: int = Body(embed=True, gt=0)):
    require_selection(request, spool_id)
    return clear_selection(JSONResponse({"ok": True}))


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return render_home(selected_spool_id(request), SPOOLMAN_BASE)


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {"ok": True, "spoolman_base": SPOOLMAN_BASE}


async def render_selected_spool(spool_id: int) -> HTMLResponse:
    lookup_failed = False
    try:
        spool = await fetch_spoolman_spool(spool_id)
    except httpx.HTTPError:
        spool = {}
        lookup_failed = True
    return render_selected_spool_page(
        spool_id, spool, lookup_failed=lookup_failed, spoolman_base=SPOOLMAN_BASE
    )


@app.get("/selected")
async def selected_spool_page(request: Request):
    spool_id = selected_spool_id(request)
    if spool_id is None:
        return render_no_selection(SPOOLMAN_BASE)
    return await render_selected_spool(spool_id)


@app.get("/scan")
async def scan(request: Request, value: str, stay: str | None = Query(default=None)):
    spool_id = extract_spool_id(value)
    if not spool_id:
        raise HTTPException(status_code=400, detail="Could not identify a spool from this QR value.")
    response = (await render_selected_spool(spool_id) if wants_scan_stay(stay)
                else RedirectResponse(url=spool_url(spool_id), status_code=302))
    return set_selection(response, spool_id)


@app.get("/select/{spool_id}")
def select_spool(spool_id: int):
    response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    return set_selection(response, spool_id)


@app.get("/bin/{location:path}")
async def set_location(location: str, request: Request, stay: str | None = None, spool_id: int | None = Query(default=None, gt=0)):
    normalized_location = normalize_location(location)
    if spool_id is not None:
        try:
            require_selection(request, spool_id)
        except HTTPException as exc:
            return render_move_error(request, exc)
    spool_id = selected_spool_id(request)

    if spool_id is None:
        try:
            matching_spools = await fetch_spools_in_location(normalized_location)
        except httpx.HTTPError as exc:
            return render_bin_lookup_failed(
                normalized_location, exc, selected_spool_id(request), SPOOLMAN_BASE
            )

        if matching_spools:
            return render_bin_contents(
                normalized_location, matching_spools, selected_spool_id(request), SPOOLMAN_BASE
            )
        return render_empty_bin(normalized_location, selected_spool_id(request), SPOOLMAN_BASE)

    try:
        normalized_location = await move_selected_spool(request, spool_id, normalized_location)
    except HTTPException as exc:
        return render_move_error(request, exc)

    if wants_scan_stay(stay):
        response = render_spool_moved(spool_id, normalized_location, SPOOLMAN_BASE)
    else:
        response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    return clear_selection(response)


def render_move_error(request: Request, exc: HTTPException) -> HTMLResponse:
    return render_move_error_page(
        exc.detail, selected_spool_id(request), SPOOLMAN_BASE, exc.status_code
    )


@app.get("/status", response_class=JSONResponse)
def status(request: Request) -> dict[str, object]:
    spool_id = selected_spool_id(request)
    return {
        "selected_spool_id": spool_id,
        "selected_spool_url": spool_url(spool_id) if spool_id else None,
    }


@app.get("/api/bins", response_class=JSONResponse)
async def api_bins(source: str = Query(default="default", pattern="^(default|spoolman|all)$")):
    if source == "all":
        bins = set(configured_bins())
        warning = None
        try:
            bins.update(await fetch_spoolman_locations())
        except httpx.HTTPError:
            warning = "Could not load locations from Spoolman. Showing configured/default destinations."
        return {"source": "all", "bins": sorted(bins), "warning": warning}
    if source == "spoolman":
        try:
            bins = await fetch_spoolman_locations()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to load bins from Spoolman: {exc}") from exc
        if bins:
            return {"source": "spoolman", "bins": bins}

    return {"source": "default", "bins": default_bins()}




@app.get("/api/spools", response_class=JSONResponse)
async def api_spools():
    try:
        spools = await fetch_spoolman_spools()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load spools from Spoolman: {exc}") from exc

    by_id = {spool["id"]: spool for spool in spools if isinstance(spool.get("id"), int) and spool["id"] > 0}
    summaries = [
        {"id": spool_id, "description": spool_summary(by_id[spool_id]),
         "color_hex": spool_color_hex(by_id[spool_id]), "locations": sorted(spool_location_values(by_id[spool_id]))}
        for spool_id in sorted(by_id)
    ]
    return {"source": "spoolman", "spool_ids": sorted(by_id), "spools": summaries}

@app.get("/qr.svg")
def qr_svg(value: str = Query(min_length=1, max_length=2048)) -> Response:
    return Response(render_qr_svg(value), media_type="image/svg+xml")


@app.get("/bins", response_class=HTMLResponse)
def bins_page(request: Request) -> HTMLResponse:
    return render_bins(selected_spool_id(request), SPOOLMAN_BASE)


@app.get("/spools", response_class=HTMLResponse)
def spools_page(request: Request) -> HTMLResponse:
    return render_spools(selected_spool_id(request), SPOOLMAN_BASE)
