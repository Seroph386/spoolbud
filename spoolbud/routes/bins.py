from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from spoolbud import dependencies as deps
from spoolbud.rendering.pages import (
    render_bin_contents,
    render_bin_lookup_failed,
    render_bins,
    render_empty_bin,
    render_move_error,
    render_spool_moved,
)
from spoolbud.routes.common import wants_scan_stay
from spoolbud.services.bins import normalize_location


router = APIRouter()


def move_error(request: Request, exc: HTTPException) -> HTMLResponse:
    return render_move_error(
        exc.detail, deps.selected_spool_id(request), deps.SPOOLMAN_BASE, exc.status_code
    )


@router.get("/bin/{location:path}")
async def set_location(
    location: str,
    request: Request,
    stay: str | None = None,
    spool_id: int | None = Query(default=None, gt=0),
):
    normalized_location = normalize_location(location)
    if spool_id is not None:
        try:
            deps.require_selection(request, spool_id)
        except HTTPException as exc:
            return move_error(request, exc)
    spool_id = deps.selected_spool_id(request)

    if spool_id is None:
        try:
            matching_spools = await deps.fetch_spools_in_location(normalized_location)
        except httpx.HTTPError as exc:
            return render_bin_lookup_failed(
                normalized_location, exc, deps.selected_spool_id(request), deps.SPOOLMAN_BASE
            )
        if matching_spools:
            return render_bin_contents(
                normalized_location,
                matching_spools,
                deps.selected_spool_id(request),
                deps.SPOOLMAN_BASE,
            )
        return render_empty_bin(
            normalized_location, deps.selected_spool_id(request), deps.SPOOLMAN_BASE
        )

    try:
        normalized_location = await deps.move_selected_spool(request, spool_id, normalized_location)
    except HTTPException as exc:
        return move_error(request, exc)

    response = (
        render_spool_moved(spool_id, normalized_location, deps.SPOOLMAN_BASE)
        if wants_scan_stay(stay)
        else RedirectResponse(url=deps.spool_url(spool_id), status_code=302)
    )
    return deps.clear_selection(response)


@router.get("/bins", response_class=HTMLResponse)
def bins_page(request: Request) -> HTMLResponse:
    return render_bins(deps.selected_spool_id(request), deps.SPOOLMAN_BASE)
