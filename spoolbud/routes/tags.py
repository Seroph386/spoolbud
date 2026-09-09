"""NFC UID URL entry point."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from spoolbud import dependencies as deps
from spoolbud.clients.spoolman import DuplicateTagUIDError, TagAssignmentRequest, TagLookupError
from spoolbud.parsing.tag_uids import normalize_uid
from spoolbud.rendering.pages import (
    render_duplicate_tag,
    render_invalid_tag_uid,
    render_selected_spool,
    render_tag_lookup_failed,
    render_unassigned_tag,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def clear_tag_selection(response: HTMLResponse) -> HTMLResponse:
    response.headers["Cache-Control"] = "no-store"
    return deps.clear_selection(response)


@router.get("/tag/{uid}", response_class=HTMLResponse)
async def select_spool_by_tag(uid: str) -> HTMLResponse:
    try:
        canonical_uid = normalize_uid(uid)
    except ValueError:
        return clear_tag_selection(render_invalid_tag_uid(uid, deps.SPOOLMAN_BASE))

    try:
        spool = await deps.fetch_spool_by_tag_uid(canonical_uid)
    except DuplicateTagUIDError as exc:
        logger.warning("Duplicate nfc_id configuration matched spool IDs %s", exc.spool_ids)
        return clear_tag_selection(render_duplicate_tag(canonical_uid, deps.SPOOLMAN_BASE))
    except TagLookupError as exc:
        return clear_tag_selection(render_tag_lookup_failed(canonical_uid, str(exc), deps.SPOOLMAN_BASE))

    if spool is None:
        load_error = None
        try:
            spools = await deps.fetch_spoolman_spools()
        except httpx.HTTPError:
            spools = []
            load_error = "Could not load the spool list from Spoolman. Check the connection, then try again."
        return clear_tag_selection(
            render_unassigned_tag(canonical_uid, spools, deps.SPOOLMAN_BASE, load_error=load_error)
        )

    spool_id = spool["id"]
    response = render_selected_spool(
        spool_id,
        spool,
        lookup_failed=False,
        spoolman_base=deps.SPOOLMAN_BASE,
    )
    return deps.set_selection(response, spool_id)


@router.post("/tag/{uid}/assign", response_class=JSONResponse)
async def assign_spool_to_tag(uid: str, request: Request) -> JSONResponse:
    try:
        canonical_uid = normalize_uid(uid)
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise ValueError("Expected JSON")
        assignment = TagAssignmentRequest.model_validate(await request.json())
    except (ValueError, ValidationError):
        response = JSONResponse(
            {"detail": "Choose a valid Spoolman spool for this NFC tag."},
            status_code=400,
        )
        response.headers["Cache-Control"] = "no-store"
        return deps.clear_selection(response)

    try:
        spool = await deps.associate_spool_with_tag_uid(
            assignment.spool_id,
            canonical_uid,
            replace_existing=assignment.replace_existing,
        )
    except DuplicateTagUIDError as exc:
        logger.warning("Duplicate nfc_id configuration matched spool IDs %s", exc.spool_ids)
        response = JSONResponse({"detail": str(exc)}, status_code=exc.status_code)
        response.headers["Cache-Control"] = "no-store"
        return deps.clear_selection(response)
    except TagLookupError as exc:
        response = JSONResponse({"detail": str(exc)}, status_code=exc.status_code)
        response.headers["Cache-Control"] = "no-store"
        return deps.clear_selection(response)

    response = JSONResponse(
        {"assigned_spool_id": spool["id"], "uid": canonical_uid},
        headers={"Cache-Control": "no-store"},
    )
    return deps.set_selection(response, spool["id"])
