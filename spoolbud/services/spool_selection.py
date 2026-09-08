"""Cookie-backed selected-spool workflow state."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response

from spoolbud.config import settings
from spoolbud.parsing.spool_ids import extract_spool_id


def get_selected_spool(
    request: Request | None,
    *,
    cookie_name: str = settings.cookie_name,
    parser: Callable[[str | None], int | None] = extract_spool_id,
) -> int | None:
    if request is None:
        return None
    return parser(request.cookies.get(cookie_name, ""))


def set_selected_spool(
    response: Response,
    spool_id: int,
    *,
    cookie_name: str = settings.cookie_name,
    max_age: int = settings.cookie_max_age,
) -> Response:
    response.set_cookie(cookie_name, str(spool_id), max_age=max_age, samesite="Lax")
    return response


def clear_selected_spool(
    response: Response,
    *,
    cookie_name: str = settings.cookie_name,
) -> Response:
    response.delete_cookie(cookie_name, samesite="Lax")
    return response
