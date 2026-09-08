from __future__ import annotations

import httpx
from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from spoolbud import dependencies as deps
from spoolbud.parsing.spool_ids import extract_spool_id
from spoolbud.rendering.pages import render_no_selection, render_selected_spool as render_selected_page
from spoolbud.routes.common import wants_scan_stay


router = APIRouter()


async def render_selected_spool(spool_id: int) -> HTMLResponse:
    lookup_failed = False
    try:
        spool = await deps.fetch_spoolman_spool(spool_id)
    except httpx.HTTPError:
        spool = {}
        lookup_failed = True
    return render_selected_page(spool_id, spool, lookup_failed=lookup_failed, spoolman_base=deps.SPOOLMAN_BASE)


@router.get("/selected")
async def selected_spool_page(request: Request):
    spool_id = deps.selected_spool_id(request)
    if spool_id is None:
        return render_no_selection(deps.SPOOLMAN_BASE)
    return await render_selected_spool(spool_id)


@router.get("/scan")
async def scan(request: Request, value: str, stay: str | None = Query(default=None)):
    spool_id = extract_spool_id(value)
    if not spool_id:
        raise HTTPException(status_code=400, detail="Could not identify a spool from this QR value.")
    response = (
        await render_selected_spool(spool_id)
        if wants_scan_stay(stay)
        else RedirectResponse(url=deps.spool_url(spool_id), status_code=302)
    )
    return deps.set_selection(response, spool_id)


@router.get("/select/{spool_id}")
def select_spool(spool_id: int):
    return deps.set_selection(RedirectResponse(url=deps.spool_url(spool_id), status_code=302), spool_id)


@router.get("/status", response_class=JSONResponse)
def status(request: Request) -> dict[str, object]:
    spool_id = deps.selected_spool_id(request)
    return {
        "selected_spool_id": spool_id,
        "selected_spool_url": deps.spool_url(spool_id) if spool_id else None,
    }


@router.post("/api/selection/clear")
def cancel_selection(request: Request, spool_id: int = Body(embed=True, gt=0)):
    deps.require_selection(request, spool_id)
    return deps.clear_selection(JSONResponse({"ok": True}))
