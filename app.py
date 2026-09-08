from __future__ import annotations

from html import escape
from typing import Any

import httpx
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import ValidationError

from spoolbud.config import settings
from spoolbud.clients.spoolman import SpoolmanClient
from spoolbud.parsing.spool_ids import extract_spool_id
from spoolbud.rendering.assets import (
    BINS_PAGE_SCRIPT,
    HOME_SCAN_PAGE_SCRIPT,
    SCAN_PAGE_SCRIPT,
    SPOOLS_PAGE_SCRIPT,
    TAG_SCAN_PAGE_SCRIPT,
)
from spoolbud.rendering.components import (
    render_page as build_page,
    render_spool_cards as build_spool_cards,
    spool_color_hex,
    spool_summary,
)
from spoolbud.services.spool_selection import clear_selected_spool, get_selected_spool, set_selected_spool
from spoolbud.services.qr import render_qr_svg
from spoolbud.services.bins import (
    configured_bins as build_configured_bins,
    default_bins,
    get_bin_contents,
    get_spoolman_locations,
    move_selected_spool_to_bin,
    normalize_location,
    spool_location_values,
    spools_in_location,
)
from spoolman_tags import TagScanError, TagScanRequest, resolve_tag

# Compatibility aliases remain while responsibilities move into the package.
SPOOLMAN_BASE = settings.spoolman_base
API_TOKEN = settings.spoolman_api_token
COOKIE_NAME = settings.cookie_name
COOKIE_MAX_AGE = settings.cookie_max_age
DESTINATIONS = settings.destinations

app = FastAPI(title="SpoolBud Helper")

def wants_scan_stay(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def spool_url(spool_id: int) -> str:
    return f"{SPOOLMAN_BASE}/spool/show/{spool_id}"


def configured_bins() -> list[str]:
    return build_configured_bins(DESTINATIONS)


def auth_headers() -> dict[str, str]:
    return SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).auth_headers()


def selected_spool_id(request: Request | None) -> int | None:
    return get_selected_spool(request, cookie_name=COOKIE_NAME, parser=extract_spool_id)


def render_page(
    title: str,
    body: str,
    *,
    request: Request | None = None,
    active_nav: str = "home",
    status_code: int = 200,
) -> HTMLResponse:
    return build_page(
        title,
        body,
        current_spool_id=selected_spool_id(request),
        spoolman_base=SPOOLMAN_BASE,
        active_nav=active_nav,
        status_code=status_code,
    )


def render_spool_cards(spools: list[dict[str, Any]], *, compact: bool = False) -> str:
    return build_spool_cards(spools, spoolman_base=SPOOLMAN_BASE, compact=compact)


async def fetch_spoolman_spools() -> list[dict[str, Any]]:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).get_spools()


async def fetch_spoolman_spool(spool_id: int) -> dict[str, Any]:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).get_spool(spool_id)


async def fetch_spoolman_locations() -> list[str]:
    return await get_spoolman_locations(fetch_spoolman_spools)


async def fetch_spools_in_location(location: str) -> list[dict[str, Any]]:
    return await get_bin_contents(location, fetch_spoolman_spools)


async def patch_spool_location(spool_id: int, location: str) -> httpx.Response:
    return await SpoolmanClient(SPOOLMAN_BASE, API_TOKEN).update_spool_location(spool_id, location)


def require_selection(request: Request, expected_spool_id: int) -> None:
    if selected_spool_id(request) != expected_spool_id:
        raise HTTPException(409, "Spool selection changed or was cleared. Scan your spool again before continuing.")


async def move_selected_spool(request: Request, spool_id: int, location: str) -> str:
    return await move_selected_spool_to_bin(
        request,
        spool_id,
        location,
        get_selection=selected_spool_id,
        update_location=patch_spool_location,
    )


def clear_selection(response: Response) -> Response:
    return clear_selected_spool(response, cookie_name=COOKIE_NAME)


def set_selection(response: Response, spool_id: int) -> Response:
    return set_selected_spool(response, spool_id, cookie_name=COOKIE_NAME, max_age=COOKIE_MAX_AGE)


@app.post("/api/tag/scan")
async def scan_tag(request: Request):
    # Validate here so even malformed scans clear an older pending selection.
    try:
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise ValueError("Expected JSON")
        scan = TagScanRequest.model_validate(await request.json())
    except (ValueError, ValidationError):
        return clear_selection(JSONResponse({"detail": "Send a JSON scan with a hardware UID and valid reader details. No spool was selected."}, status_code=400))
    try:
        spool_id = await resolve_tag(scan, base_url=SPOOLMAN_BASE, headers=auth_headers())
    except TagScanError as exc:
        return clear_selection(JSONResponse({"detail": str(exc)}, status_code=exc.status_code))
    if spool_id is None:
        return clear_selection(JSONResponse({"matched_spool_id": None, "detail": "This tag is not linked to a spool. Link it in Spoolman, then scan again."}))
    return set_selection(JSONResponse({"matched_spool_id": spool_id}), spool_id)


@app.post("/api/move")
async def move_spool(request: Request, spool_id: int = Body(gt=0), location: str = Body()):
    location = await move_selected_spool(request, spool_id, location)
    return clear_selection(JSONResponse({"spool_id": spool_id, "location": location}))


@app.post("/api/selection/clear")
def cancel_selection(request: Request, spool_id: int = Body(embed=True, gt=0)):
    require_selection(request, spool_id)
    return clear_selection(JSONResponse({"ok": True}))


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    current_spool_id = selected_spool_id(request)
    current_spool_markup = (
        f'<span id="currentSelection" class="chip">Selected spool: <strong>{current_spool_id}</strong></span>' if current_spool_id else ""
    )
    body = f"""
    <main class="stack">
      <section class="panel hero">
        <div class="summary">
          <span class="chip">Tap or scan</span>
          {current_spool_markup}
        </div>
        <div>
          <h1>Select a spool, then choose its destination</h1>
          <p class="muted">Scan a tag through Spoolman or use a spool QR. Then move or store the selected spool using a destination button or bin QR.</p>
          {f'<p id="continueSelection"><a class="button" href="/selected">Continue with spool {current_spool_id}</a></p>' if current_spool_id else ""}
        </div>
      </section>

      <section class="panel stack">
        <h2>Scan an NFC / RFID tag</h2>
        <p class="muted">Use a reader that enters the hardware UID, or paste a UID from a reader app. Spoolman decides which spool it identifies.</p>
        <form id="tagScanForm" class="stack">
          <label>Tag UID
            <input id="tagUid" class="input" required maxlength="128" autocomplete="off" spellcheck="false" placeholder="04:A2:B3:C4:D5:E6:F7" />
          </label>
          <label>Reader ID (optional)
            <input id="tagReaderId" class="input" maxlength="64" autocomplete="off" placeholder="desk-reader" />
          </label>
          <button id="submitTagScan" class="button" type="submit">Find spool in Spoolman</button>
        </form>
        <div class="toolbar">
          <button id="readNfc" class="button" type="button" hidden>Read tag with this phone</button>
          <button id="stopNfc" class="button" type="button" hidden>Stop reading</button>
        </div>
        <p id="tagScanStatus" role="status" aria-live="polite"></p>
        <p class="muted">Keyboard readers: focus Tag UID and send the hex UID followed by Enter. iPhone Safari needs a reader or companion app to supply the UID; it cannot read a blank tag directly.</p>
        <p><a href="{escape(SPOOLMAN_BASE, quote=True)}" target="_blank" rel="noreferrer">Link or reassign tags in Spoolman</a></p>
      </section>

      <section class="panel scanner-wrap">
        <h2>Scan a Spoolman QR</h2>
        <p class="muted">Scan a Spoolman QR such as <code>web+spoolman:s-42</code> or a SpoolBud spool link to choose a destination.</p>
        <div class="toolbar">
          <button id="startSpoolScanner" class="button" type="button">Open scanner</button>
        </div>
        <p id="spoolScannerStatus" class="muted">Tap <strong>Open scanner</strong> to scan a spool QR in a popup.</p>
        <label>
          <div class="muted">Supported spool QR payload example</div>
          <input id="spoolScanReference" class="input" value="" readonly />
        </label>
      </section>
      <section id="spoolScannerModal" class="scanner-modal" aria-hidden="true">
        <div class="scanner-modal-card">
          <div class="toolbar">
            <button id="runSpoolScanner" class="button" type="button">Start camera</button>
            <button id="stopSpoolScanner" class="button" type="button" disabled>Stop scanner</button>
            <button id="closeSpoolScanner" class="button" type="button">Close</button>
          </div>
          <video id="spoolScannerVideo" class="scanner-video" playsinline muted></video>
          <canvas id="spoolScannerCanvas" hidden></canvas>
        </div>
      </section>

      <section class="panel">
        <h2>Quick Links</h2>
        <ul class="clean">
          <li><a href="/bins">Open the bin label generator</a></li>
          <li><a href="/spools">Open the Spoolman-compatible spool label generator</a></li>
          <li><a href="/healthz">Check health output</a></li>
          <li><a href="/status">Inspect JSON session status</a></li>
          <li><a href="{escape(SPOOLMAN_BASE, quote=True)}" target="_blank" rel="noreferrer">Open Spoolman</a></li>
        </ul>
      </section>
    </main>
    <script>{HOME_SCAN_PAGE_SCRIPT}{TAG_SCAN_PAGE_SCRIPT}</script>
    """
    return render_page("Home", body, request=request, active_nav="home")


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {"ok": True, "spoolman_base": SPOOLMAN_BASE}


async def render_selected_spool(spool_id: int) -> HTMLResponse:
    spool_details_markup = ""
    spool_details_notice = ""
    try:
        spool = await fetch_spoolman_spool(spool_id)
    except httpx.HTTPError:
        spool = {}
        spool_details_notice = (
            '<p class="muted">SpoolBud selected this spool, but could not load its details from Spoolman right now.</p>'
        )

    if spool:
        spool_details_markup = render_spool_cards([spool], compact=True)

    body = f"""
    <main class="stack">
      <section class="panel">
        <h1 id="selectedHeading">Spool {spool_id} selected</h1>
        <div id="spoolDetails">{spool_details_markup}{spool_details_notice}</div>
        <p><a href="{escape(spool_url(spool_id), quote=True)}" target="_blank" rel="noreferrer">Open this spool in Spoolman</a></p>
        <p id="moveComplete" hidden><a class="button" href="/">Move another spool</a></p>
      </section>

      <div id="selectionActions" class="stack" data-spool-id="{spool_id}">
      <section class="panel stack">
        <h2>Choose a destination</h2>
        <p class="muted">Move or store this spool by choosing a location below or scanning its bin QR. A location change does not load a printer.</p>
        <p id="destinationStatus" class="muted" role="status">Loading destinations...</p>
        <p id="moveStatus" role="status" aria-live="polite"></p>
        <form id="destinationForm" class="stack">
          <label>Find or enter a destination
            <input id="destinationSearch" class="input" type="search" required maxlength="200" placeholder="F-001 or PRINTER-1" />
          </label>
          <button class="button" type="submit">Move to entered destination</button>
        </form>
        <div id="destinations" class="grid destination-grid"></div>
        <button id="cancelSelection" class="button" type="button">Cancel selection</button>
      </section>
      <section class="panel scanner-wrap">
        <div class="toolbar">
          <button id="startBinScanner" class="button" type="button">Open bin scanner</button>
        </div>
        <p id="scannerStatus" class="muted">Tap <strong>Open bin scanner</strong> to scan a bin QR in a popup.</p>
        <label>
          <div class="muted">Bin URL prefix (reference)</div>
          <input id="spoolBudBase" class="input" value="" readonly />
        </label>
      </section>
      <section id="binScannerModal" class="scanner-modal" aria-hidden="true">
        <div class="scanner-modal-card">
          <div class="toolbar">
            <button id="runBinScanner" class="button" type="button">Start camera</button>
            <button id="stopBinScanner" class="button" type="button" disabled>Stop scanner</button>
            <button id="closeBinScanner" class="button" type="button">Close</button>
          </div>
          <video id="scannerVideo" class="scanner-video" playsinline muted></video>
          <canvas id="scannerCanvas" hidden></canvas>
        </div>
      </section>
      </div>
    </main>
    <script>{SCAN_PAGE_SCRIPT}</script>
    """
    response = render_page("Spool Selected", body)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/selected")
async def selected_spool_page(request: Request):
    spool_id = selected_spool_id(request)
    if spool_id is None:
        return render_page("Select a spool", '<main class="panel"><h1>No spool selected</h1><p><a href="/">Scan a tag or spool QR to begin.</a></p></main>', status_code=409)
    return await render_selected_spool(spool_id)


@app.get("/scan")
async def scan(request: Request, value: str, stay: str | None = Query(default=None)):
    spool_id = extract_spool_id(value)
    if not spool_id:
        raise HTTPException(status_code=400, detail="Could not identify a spool from this QR value.")
    response = (await render_selected_spool(spool_id) if wants_scan_stay(stay)
                else RedirectResponse(url=spool_url(spool_id), status_code=302))
    return set_selection(response, spool_id)


@app.get("/select/{spool_id}")
def select_spool(spool_id: int):
    response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    return set_selection(response, spool_id)


@app.get("/bin/{location:path}")
async def set_location(location: str, request: Request, stay: str | None = None, spool_id: int | None = Query(default=None, gt=0)):
    normalized_location = normalize_location(location)
    if spool_id is not None:
        try:
            require_selection(request, spool_id)
        except HTTPException as exc:
            return render_move_error(request, exc)
    spool_id = selected_spool_id(request)

    if spool_id is None:
        try:
            matching_spools = await fetch_spools_in_location(normalized_location)
        except httpx.HTTPError as exc:
            body = f"""
            <main class="panel">
              <h1>Bin lookup failed</h1>
              <p class="muted">No spool is currently selected, and SpoolBud could not load the contents of <strong>{escape(normalized_location)}</strong> from Spoolman.</p>
              <pre class="card">{escape(str(exc))}</pre>
            </main>
            """
            return render_page("Bin Lookup Failed", body, request=request, status_code=502)

        if matching_spools:
            body = f"""
            <main class="stack">
              <section class="panel">
                <h1>Contents of {escape(normalized_location)}</h1>
                <p class="muted">No spool was selected in this browser, so this scan is showing what Spoolman currently lists in the bin instead.</p>
              </section>
              <section class="spool-list grid">
                {render_spool_cards(matching_spools)}
              </section>
            </main>
            """
            return render_page(f"Bin {normalized_location}", body, request=request)

        body = f"""
        <main class="panel">
          <h1>{escape(normalized_location)} is empty</h1>
          <p class="muted">No spool is selected in this browser, and Spoolman does not currently list any spools in this bin.</p>
          <p>Resolve a spool tag through Spoolman or scan a spool QR first to update its location.</p>
        </main>
        """
        return render_page(f"Bin {normalized_location}", body, request=request)

    try:
        normalized_location = await move_selected_spool(request, spool_id, normalized_location)
    except HTTPException as exc:
        return render_move_error(request, exc)

    if wants_scan_stay(stay):
        body = f"""<main class="panel">
          <h1>Spool {spool_id} moved to {escape(normalized_location)}</h1>
          <p><a class="button" href="/">Move another spool</a></p>
          <p><a href="{escape(spool_url(spool_id), quote=True)}">Open in Spoolman</a></p>
        </main>"""
        response = render_page("Spool moved", body)
    else:
        response = RedirectResponse(url=spool_url(spool_id), status_code=302)
    return clear_selection(response)


def render_move_error(request: Request, exc: HTTPException) -> HTMLResponse:
    body = f"""<main class="panel">
      <h1>Move not confirmed</h1><p>{escape(str(exc.detail))}</p>
      <p><a href="/">Return to SpoolBud</a></p>
    </main>"""
    return render_page("Move not confirmed", body, request=request, status_code=exc.status_code)


@app.get("/status", response_class=JSONResponse)
def status(request: Request) -> dict[str, object]:
    spool_id = selected_spool_id(request)
    return {
        "selected_spool_id": spool_id,
        "selected_spool_url": spool_url(spool_id) if spool_id else None,
    }


@app.get("/api/bins", response_class=JSONResponse)
async def api_bins(source: str = Query(default="default", pattern="^(default|spoolman|all)$")):
    if source == "all":
        bins = set(configured_bins())
        warning = None
        try:
            bins.update(await fetch_spoolman_locations())
        except httpx.HTTPError:
            warning = "Could not load locations from Spoolman. Showing configured/default destinations."
        return {"source": "all", "bins": sorted(bins), "warning": warning}
    if source == "spoolman":
        try:
            bins = await fetch_spoolman_locations()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to load bins from Spoolman: {exc}") from exc
        if bins:
            return {"source": "spoolman", "bins": bins}

    return {"source": "default", "bins": default_bins()}




@app.get("/api/spools", response_class=JSONResponse)
async def api_spools():
    try:
        spools = await fetch_spoolman_spools()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load spools from Spoolman: {exc}") from exc

    by_id = {spool["id"]: spool for spool in spools if isinstance(spool.get("id"), int) and spool["id"] > 0}
    summaries = [
        {"id": spool_id, "description": spool_summary(by_id[spool_id]),
         "color_hex": spool_color_hex(by_id[spool_id]), "locations": sorted(spool_location_values(by_id[spool_id]))}
        for spool_id in sorted(by_id)
    ]
    return {"source": "spoolman", "spool_ids": sorted(by_id), "spools": summaries}

@app.get("/qr.svg")
def qr_svg(value: str = Query(min_length=1, max_length=2048)) -> Response:
    return Response(render_qr_svg(value), media_type="image/svg+xml")


@app.get("/bins", response_class=HTMLResponse)
def bins_page(request: Request) -> HTMLResponse:
    body = f"""
    <main class="stack">
      <section class="panel">
        <h1>Bin QR Generator</h1>
        <p class="muted">Prepare QR labels for storage locations. Load configured shortcuts and used Spoolman locations, or enter names below.</p>
        <p class="muted">Spoolman owns the stored location. Local shortcuts only help choose a destination. Opening a bin QR with a selected spool moves it there.</p>
      </section>

      <section class="panel stack">
        <div class="toolbar">
          <label style="flex: 1 1 24rem;">
            <div class="muted">Public SpoolBud base URL</div>
            <input id="publicBase" class="input" value="" />
          </label>
          <button id="loadDefault" class="button" type="button">Load defaults</button>
          <button id="loadSpoolman" class="button" type="button">Load destinations</button>
          <button id="render" class="button" type="button">Render labels</button>
        </div>

        <label>
          <div class="muted">Bin codes, one per line</div>
          <textarea id="bins" class="input"></textarea>
        </label>

        <div id="status" class="muted"></div>
        <div id="grid" class="grid"></div>
      </section>
    </main>
    <script>{BINS_PAGE_SCRIPT}</script>
    """
    return render_page("Bin Labels", body, request=request, active_nav="bins")


@app.get("/spools", response_class=HTMLResponse)
def spools_page(request: Request) -> HTMLResponse:
    body = f"""
    <main class="stack">
      <section class="panel">
        <h1>Spoolman-Compatible Spool QR Labels</h1>
        <p>Create each physical spool in <a href="{escape(SPOOLMAN_BASE, quote=True)}" target="_blank" rel="noreferrer">Spoolman</a>, then load the list below to prepare compatibility QR labels.</p>
        <p class="muted">For NFC/RFID, use the spool’s Tags section in Spoolman to link its hardware UID. No data needs to be written to the tag. SpoolBud resolves tag associations through Spoolman.</p>
      </section>

      <section class="panel stack">
        <div class="toolbar">
          <button id="loadSpoolSample" class="button" type="button">Load sample IDs</button>
          <button id="loadSpoolmanSpools" class="button" type="button">Load from Spoolman</button>
          <button id="renderSpools" class="button" type="button">Render spool labels</button>
        </div>

        <label style="max-width: 24rem;">
          <div class="muted">QR format</div>
          <select id="spoolQrFormat" class="input">
            <option value="full-url">Full SpoolBud /scan URL</option>
            <option value="spoolman">Spoolman scanner payload (web+spoolman)</option>
          </select>
        </label>

        <label>
          <div class="muted">Public SpoolBud base URL (for full URL QR labels)</div>
          <input id="spoolPublicBase" class="input" value="" />
        </label>

        <label>
          <input id="includeStayFlag" type="checkbox" checked /> Include <code>&amp;stay=1</code> in full URL QR labels
        </label>

        <label>
          <div class="muted">Spool IDs or Spoolman spool URLs, one per line</div>
          <textarea id="spools" class="input" placeholder="42&#10;108&#10;256"></textarea>
        </label>

        <div id="spoolStatus" class="muted"></div>
        <label>Find a spool by ID, material, color, or location
          <input id="spoolSearch" class="input" type="search" placeholder="Search loaded labels" />
        </label>
        <div id="spoolGrid" class="grid"></div>
      </section>
    </main>
    <script>{{script}}</script>
    """.replace("{script}", SPOOLS_PAGE_SCRIPT)
    return render_page("Spool Labels", body, request=request, active_nav="spools")
