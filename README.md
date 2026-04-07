# spoolbud helper service

A small FastAPI companion service for Spoolman that supports a two-scan workflow:

1. Open SpoolBud and scan a spool QR code to select a spool.
   - The homepage can scan native Spoolman spool QR payloads such as `web+spoolman:s-42` and opens the bin scanner automatically.
   - Direct links to `GET /scan?value=...` still work for URL-based or numeric spool QR formats.
   - Optional: use `/scan?value=...&stay=1` to keep the phone in SpoolBud and launch an in-page bin QR scanner button (no extra browser tabs/windows).
   - The in-page scanner prefers the browser's native `BarcodeDetector` and automatically falls back to a compatibility QR decoder for WebKit-based browsers such as Chrome on iPhone.
2. Scan a bin QR code (`/bin/F-001`) to move the selected spool to that location, clear the active spool selection cookie, and redirect back to that spool in Spoolman.
3. If a bin is scanned without an active spool selection, SpoolBud shows the current contents of that bin from Spoolman instead of failing.

This fits the workflow where bins are encoded as stable labels and spool selection is remembered in a browser cookie.

## Why this exists

When spool QR codes point directly to `https://<spoolman>/spool/show/<id>`, the helper cannot see which spool was chosen.
This service solves that by routing spool scans through `/scan`, storing the selected spool ID, and then handling subsequent bin scans.

## Endpoints

- `GET /healthz` — health probe
- `GET /status` — current selected spool for this browser session
- `GET /scan?value=<spool_url_or_id_or_spoolman_payload>[&stay=1]` — parse spool ID, set cookie, then either redirect to Spoolman (default) or stay in SpoolBud with an in-page bin scanner
  - When `stay=1` is used, the selected-spool page also shows the spool name/details returned by Spoolman when available.
- `GET /select/{spool_id}` — manual fallback spool selection (for old direct Spoolman QR labels)
- `GET /bin/{location}` — update selected spool location in Spoolman and redirect to the spool page, or show current bin contents if no spool is selected
- `GET /bins` — interactive QR label page for bin labels
- `GET /spools` — interactive QR label page for Spoolman-compatible payloads or full SpoolBud `/scan` URLs
- `GET /api/bins?source=default|spoolman` — fetch bin list from defaults or by scraping locations from Spoolman
- `GET /api/spools` — fetch spool IDs from Spoolman for the spool label generator
- `GET /qr.svg?value=<url_or_text>` — render QR code SVG for labels

## Environment variables

- `SPOOLMAN_BASE` (default `https://filament.igetno.net`)
- `SPOOLMAN_API_TOKEN` (optional bearer token)
- `COOKIE_NAME` (default `last_spool_id`)

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Docker compose

```bash
docker compose up --build
```

Service is available at <http://localhost:8010>.

## Bin QR label generator

Open <http://localhost:8010/bins> to:

- load default bins (`F-001..F-020` and `B-001..B-004`)
- scrape currently used location names from the configured Spoolman instance
- render printable QR labels that point to `https://<your-spoolbud-host>/bin/<location>`
- use the built-in top navigation and light/dark theme toggle while working on a phone or desktop browser

## Spoolman-compatible spool labels

Open <http://localhost:8010/spools> to generate spool QR labels in Spoolman's scanner format:

- accepts raw spool IDs plus Spoolman spool URLs pasted one per line
- can pull spool IDs directly from Spoolman with one tap
- renders either QR payloads like `web+spoolman:s-42` **or** full SpoolBud links like `/scan?...&stay=1`
- gives you a matching SpoolBud `/select/<spool_id>` link under each label for manual fallback

## QR formats

### Recommended spool QR format

```text
web+spoolman:s-42
```

Open SpoolBud, tap `Scan spool QR`, and scan that payload to stay in the helper flow.

Direct SpoolBud links are still supported when you want a QR code to jump straight into the helper:

```text
https://spoolbud.example.net/scan?value=https://filament.example.net/spool/show/42&stay=1
```

(On iPhone browsers, `stay=1` now uses a compatibility scanner automatically when native barcode detection is unavailable.)

(Also supports numeric-only IDs such as `?value=42`.)

### Bin QR format

```text
https://spoolbud.example.net/bin/F-001
https://spoolbud.example.net/bin/B-004
```

## CI/CD

- CI workflow (`.github/workflows/ci.yml`) runs unit tests, validates Docker Compose, builds the image, and smoke-tests `/healthz`.
- Publish workflow (`.github/workflows/publish.yml`) runs on pushes to `main` and pushes a **multi-arch** image to GHCR (`linux/amd64` + `linux/arm64`):
  - `ghcr.io/<owner>/spoolbud:latest`
  - `ghcr.io/<owner>/spoolbud:sha-<shortsha>`

If you need to force a platform when pulling/testing locally:

```bash
docker pull --platform linux/arm64 ghcr.io/<owner>/spoolbud:latest
```

## Agent guidance

Repository-level AI agent guidance lives in `AGENTS.md` (principles, architecture constraints, and extension expectations).
