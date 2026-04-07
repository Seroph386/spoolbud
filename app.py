from __future__ import annotations

import io
import os
import re
from html import escape
from typing import Any

import httpx
import segno
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

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


def default_bins() -> list[str]:
    front = [f"F-{index:03d}" for index in range(1, 21)]
    back = [f"B-{index:03d}" for index in range(1, 5)]
    return front + back


def auth_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    return headers


async def fetch_spoolman_spools() -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(f"{SPOOLMAN_BASE}/api/v1/spool", headers=auth_headers())
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []


async def fetch_spoolman_locations() -> list[str]:
    spools = await fetch_spoolman_spools()
    seen: set[str] = set()

    for spool in spools:
        for key in ("location", "bin", "storage_location"):
            value = spool.get(key)
            if value:
                seen.add(normalize_location(str(value)))

        extra = spool.get("extra")
        if isinstance(extra, dict):
            for key in ("location", "bin"):
                value = extra.get(key)
                if value:
                    seen.add(normalize_location(str(value)))

    return sorted(seen)


async def patch_spool_location(spool_id: int, location: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        return await client.patch(
            f"{SPOOLMAN_BASE}/api/v1/spool/{spool_id}",
            headers=auth_headers(),
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
              <li><a href="/bins">/bins</a> — generate printable bin QR codes</li>
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


@app.get("/api/bins", response_class=JSONResponse)
async def api_bins(source: str = Query(default="default", pattern="^(default|spoolman)$")):
    if source == "spoolman":
        try:
            bins = await fetch_spoolman_locations()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to load bins from Spoolman: {exc}") from exc
        if bins:
            return {"source": "spoolman", "bins": bins}

    return {"source": "default", "bins": default_bins()}


@app.get("/qr.svg")
def qr_svg(value: str = Query(min_length=1, max_length=2048)) -> Response:
    qr = segno.make(value)
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=7, border=2)
    return Response(buffer.getvalue(), media_type="image/svg+xml")


@app.get("/bins", response_class=HTMLResponse)
def bins_page() -> HTMLResponse:
    return HTMLResponse(
        f"""
        <html>
          <head>
            <title>SpoolBud Bin QR Generator</title>
            <style>
              body {{ font-family: system-ui, sans-serif; margin: 1rem auto; max-width: 1100px; padding: 0 1rem; }}
              .toolbar {{ display: flex; gap: .5rem; flex-wrap: wrap; align-items: center; margin-bottom: 1rem; }}
              textarea {{ width: 100%; min-height: 7rem; }}
              #grid {{ display: grid; grid-template-columns: repeat(auto-fill,minmax(180px,1fr)); gap: 1rem; margin-top: 1rem; }}
              .card {{ border: 1px solid #ddd; border-radius: 10px; padding: .75rem; text-align: center; }}
              .card img {{ width: 100%; max-width: 160px; }}
              .muted {{ color: #555; font-size: .9rem; }}
            </style>
          </head>
          <body>
            <h1>SpoolBud Bin QR Generator</h1>
            <p class="muted">Generate QR labels for <code>/bin/&lt;location&gt;</code>. You can load default bins or scrape existing locations from Spoolman.</p>

            <div class="toolbar">
              <label>Public helper base URL: <input id="publicBase" size="45" value="" /></label>
              <button id="loadDefault">Load defaults (F/B)</button>
              <button id="loadSpoolman">Load from Spoolman</button>
              <button id="render">Render QR labels</button>
            </div>

            <label>Bin codes (one per line)</label>
            <textarea id="bins"></textarea>
            <div id="status" class="muted"></div>
            <div id="grid"></div>

            <script>
              const binsEl = document.getElementById('bins');
              const statusEl = document.getElementById('status');
              const gridEl = document.getElementById('grid');
              const publicBaseEl = document.getElementById('publicBase');
              if (!publicBaseEl.value) publicBaseEl.value = window.location.origin;

              async function loadBins(source) {{
                statusEl.textContent = `Loading bins from ${{source}}...`;
                try {{
                  const res = await fetch(`/api/bins?source=${{source}}`);
                  const data = await res.json();
                  if (!res.ok) throw new Error(data.detail || 'Request failed');
                  binsEl.value = data.bins.join('\n');
                  statusEl.textContent = `Loaded ${{data.bins.length}} bins from ${{data.source}}.`;
                }} catch (err) {{
                  statusEl.textContent = `Failed to load bins: ${{err.message}}`;
                }}
              }}

              function render() {{
                const lines = binsEl.value.split('\n').map(v => v.trim().toUpperCase()).filter(Boolean);
                const publicBase = publicBaseEl.value.trim().replace(/\/$/, '');
                if (!publicBase) {{
                  statusEl.textContent = 'Enter a public helper base URL first.';
                  return;
                }}

                gridEl.innerHTML = '';
                for (const location of [...new Set(lines)]) {{
                  const target = `${{publicBase}}/bin/${{encodeURIComponent(location)}}`;
                  const qrSrc = `/qr.svg?value=${{encodeURIComponent(target)}}`;
                  const card = document.createElement('div');
                  card.className = 'card';
                  card.innerHTML = `<h3>${{location}}</h3><img alt="QR for ${{location}}" src="${{qrSrc}}"/><div class="muted">${{target}}</div>`;
                  gridEl.appendChild(card);
                }}
                statusEl.textContent = `Rendered ${{gridEl.children.length}} QR labels.`;
              }}

              document.getElementById('loadDefault').addEventListener('click', () => loadBins('default'));
              document.getElementById('loadSpoolman').addEventListener('click', () => loadBins('spoolman'));
              document.getElementById('render').addEventListener('click', render);
              loadBins('default');
            </script>
          </body>
        </html>
        """
    )
