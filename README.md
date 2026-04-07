# spoolbud helper service

A small FastAPI companion service for Spoolman that supports a two-scan workflow:

1. Scan a spool QR code (`/scan?value=...`) to select a spool and redirect to Spoolman.
2. Scan a bin QR code (`/bin/F-001`) to move the selected spool to that location.

This fits the workflow where bins are encoded as stable labels and spool selection is remembered in a browser cookie.

## Why this exists

When spool QR codes point directly to `https://<spoolman>/spool/<id>`, the helper cannot see which spool was chosen.
This service solves that by routing spool scans through `/scan`, storing the selected spool ID, and then handling subsequent bin scans.

## Endpoints

- `GET /healthz` — health probe
- `GET /status` — current selected spool for this browser session
- `GET /scan?value=<spool_url_or_id>` — parse spool ID, set cookie, redirect to Spoolman spool page
- `GET /select/{spool_id}` — manual fallback spool selection (for old direct Spoolman QR labels)
- `GET /bin/{location}` — update selected spool location in Spoolman
- `GET /bins` — interactive QR label page for bin labels
- `GET /api/bins?source=default|spoolman` — fetch bin list from defaults or by scraping locations from Spoolman
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

## QR formats

### Recommended spool QR format

```text
https://spoolbud.example.net/scan?value=https://filament.example.net/spool/42
```

(Also supports numeric-only IDs such as `?value=42`.)

### Bin QR format

```text
https://spoolbud.example.net/bin/F-001
https://spoolbud.example.net/bin/B-004
```

## CI/CD

- CI workflow (`.github/workflows/ci.yml`) runs unit tests, validates Docker Compose, builds the image, and smoke-tests `/healthz`.
- Publish workflow (`.github/workflows/publish.yml`) runs on pushes to `main` and pushes to GHCR:
  - `ghcr.io/<owner>/spoolbud:latest`
  - `ghcr.io/<owner>/spoolbud:sha-<shortsha>`

## Agent guidance

Repository-level AI agent guidance lives in `AGENTS.md` (principles, architecture constraints, and extension expectations).
