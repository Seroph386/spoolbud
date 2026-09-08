from __future__ import annotations

import httpx
from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

from spoolbud import dependencies as deps
from spoolbud.clients.spoolman import TagScanError, TagScanRequest
from spoolbud.rendering.components import spool_color_hex, spool_summary
from spoolbud.services.bins import default_bins, spool_location_values
from spoolbud.services.qr import render_qr_svg


router = APIRouter()


@router.post("/api/tag/scan")
async def scan_tag(request: Request):
    try:
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise ValueError("Expected JSON")
        scan = TagScanRequest.model_validate(await request.json())
    except (ValueError, ValidationError):
        return deps.clear_selection(
            JSONResponse(
                {"detail": "Send a JSON scan with a hardware UID and valid reader details. No spool was selected."},
                status_code=400,
            )
        )
    try:
        spool_id = await deps.resolve_tag_scan(scan)
    except TagScanError as exc:
        return deps.clear_selection(JSONResponse({"detail": str(exc)}, status_code=exc.status_code))
    if spool_id is None:
        return deps.clear_selection(
            JSONResponse(
                {
                    "matched_spool_id": None,
                    "detail": "This tag is not linked to a spool. Link it in Spoolman, then scan again.",
                }
            )
        )
    return deps.set_selection(JSONResponse({"matched_spool_id": spool_id}), spool_id)


@router.post("/api/move")
async def move_spool(request: Request, spool_id: int = Body(gt=0), location: str = Body()):
    location = await deps.move_selected_spool(request, spool_id, location)
    return deps.clear_selection(JSONResponse({"spool_id": spool_id, "location": location}))


@router.get("/api/bins", response_class=JSONResponse)
async def api_bins(source: str = Query(default="default", pattern="^(default|spoolman|all)$")):
    if source == "all":
        bins = set(deps.configured_bins())
        warning = None
        try:
            bins.update(await deps.fetch_spoolman_locations())
        except httpx.HTTPError:
            warning = "Could not load locations from Spoolman. Showing configured/default destinations."
        return {"source": "all", "bins": sorted(bins), "warning": warning}
    if source == "spoolman":
        try:
            bins = await deps.fetch_spoolman_locations()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to load bins from Spoolman: {exc}") from exc
        if bins:
            return {"source": "spoolman", "bins": bins}
    return {"source": "default", "bins": default_bins()}


@router.get("/api/spools", response_class=JSONResponse)
async def api_spools():
    try:
        spools = await deps.fetch_spoolman_spools()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load spools from Spoolman: {exc}") from exc

    by_id = {
        spool["id"]: spool
        for spool in spools
        if isinstance(spool.get("id"), int) and spool["id"] > 0
    }
    summaries = [
        {
            "id": spool_id,
            "description": spool_summary(by_id[spool_id]),
            "color_hex": spool_color_hex(by_id[spool_id]),
            "locations": sorted(spool_location_values(by_id[spool_id])),
        }
        for spool_id in sorted(by_id)
    ]
    return {"source": "spoolman", "spool_ids": sorted(by_id), "spools": summaries}


@router.get("/qr.svg")
def qr_svg(value: str = Query(min_length=1, max_length=2048)) -> Response:
    return Response(render_qr_svg(value), media_type="image/svg+xml")
