from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from spoolbud import dependencies as deps
from spoolbud.rendering.pages import render_home


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return render_home(deps.selected_spool_id(request), deps.SPOOLMAN_BASE)
