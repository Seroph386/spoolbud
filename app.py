from __future__ import annotations

import os
import re
from html import escape

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

SPOOLMAN_BASE = os.getenv("SPOOLMAN_BASE", "https://filament.igetno.net").rstrip("/")
API_TOKEN = os.getenv("SPOOLMAN_API_TOKEN", "")
COOKIE_NAME = os.getenv("COOKIE_NAME", "last_spool_id")
COOKIE_MAX_AGE = 60 * 60 * 24 * 30

app = FastAPI(title="SpoolBud Helper")

SPOOL_ID_PATTERNS = [
    r"/spool/(\d+)",
    r"[?&]spool_id=(\d+)",
    r"^(\d+)$",
]


def extract_spool_id(value: str | None) -> int | None:
    if not value:
        return None

    raw_value = value.strip()
    for pattern in SPOOL_ID_PATTERNS:
        match = re.search(pattern, raw_value)
        if match:
            return int(match.group(1))
    return None


def spool_url(spool_id: int) -> str:
    return f"{SPOOLMAN_BASE}/spool/{spool_id}"


def normalize_location(location: str) -> str:
    return location.strip().upper()


async def patch_spool_location(spool_id: int, location: str) -> httpx.Response:
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        return await client.patch(
            f"{SPOOLMAN_BASE}/api/v1/spool/{spool_id}",
            headers=headers,
            json={"location": location},
        )


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(
        """
        <html>
          <body style="font-family:sans-serif;max-width:45rem;margin:2rem auto;line-height:1.4;">
            <h1>SpoolBud Helper</h1>
            <p>Scan spool QR first via <code>/scan?value=...</code>, then scan a bin QR via <code>/bin/F-001</code>.</p>
            <ul>
              <li><a href="/status">/status</a> — current selected spool in this browser session</li>
              <li><a href="/healthz">/healthz</a> — health endpoint</li>
            </ul>
          </body>
        </html>
        """
    )


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {"ok": True, "spoolman_base": SPOOLMAN_BASE}


@app.get("/scan")
def scan(value: str):
    spool_id = extract_spool_id(value)
    if spool_id is None:
        raise HTTPException(status_code=400, detail="Could not parse spool ID from QR value")

    response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    response.set_cookie(COOKIE_NAME, str(spool_id), max_age=COOKIE_MAX_AGE, samesite="Lax")
    return response


@app.get("/select/{spool_id}")
def select_spool(spool_id: int):
    response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    response.set_cookie(COOKIE_NAME, str(spool_id), max_age=COOKIE_MAX_AGE, samesite="Lax")
    return response


@app.get("/bin/{location}")
async def set_location(location: str, request: Request):
    normalized_location = normalize_location(location)
    spool_id = extract_spool_id(request.cookies.get(COOKIE_NAME, ""))

    if spool_id is None:
        return HTMLResponse(
            f"""
            <html>
              <body style="font-family:sans-serif;max-width:40rem;margin:2rem auto;">
                <h2>No active spool selected</h2>
                <p>Scan the spool QR first, then scan bin <strong>{escape(normalized_location)}</strong>.</p>
                <p>Temporary fallback: open <code>/select/&lt;spool_id&gt;</code> manually.</p>
              </body>
            </html>
            """,
            status_code=400,
        )

    resp = await patch_spool_location(spool_id, normalized_location)
    if resp.status_code >= 400:
        return HTMLResponse(
            f"""
            <html>
              <body style="font-family:sans-serif;max-width:45rem;margin:2rem auto;">
                <h2>Update failed</h2>
                <p>Tried to set spool <strong>{spool_id}</strong> to <strong>{escape(normalized_location)}</strong>.</p>
                <pre style="white-space:pre-wrap;background:#f6f6f6;padding:1rem;border-radius:8px;">{escape(resp.text)}</pre>
              </body>
            </html>
            """,
            status_code=502,
        )

    return HTMLResponse(
        f"""
        <html>
          <body style="font-family:sans-serif;max-width:40rem;margin:2rem auto;">
            <h2>Location updated</h2>
            <p>Spool <strong>{spool_id}</strong> is now in <strong>{escape(normalized_location)}</strong>.</p>
            <p><a href="{spool_url(spool_id)}">Open spool in Spoolman</a></p>
          </body>
        </html>
        """
    )


@app.get("/status", response_class=JSONResponse)
def status(request: Request) -> dict[str, object]:
    spool_id = extract_spool_id(request.cookies.get(COOKIE_NAME, ""))
    return {
        "selected_spool_id": spool_id,
        "selected_spool_url": spool_url(spool_id) if spool_id else None,
    }
