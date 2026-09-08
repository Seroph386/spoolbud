from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from spoolbud import dependencies as deps
from spoolbud.rendering.pages import render_spools


router = APIRouter()


@router.get("/spools", response_class=HTMLResponse)
def spools_page(request: Request) -> HTMLResponse:
    return render_spools(deps.selected_spool_id(request), deps.SPOOLMAN_BASE)
