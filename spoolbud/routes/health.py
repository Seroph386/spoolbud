from fastapi import APIRouter

from spoolbud import dependencies as deps


router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, object]:
    return {"ok": True, "spoolman_base": deps.SPOOLMAN_BASE}
