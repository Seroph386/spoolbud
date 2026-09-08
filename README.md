# spoolbud helper service

A small FastAPI companion service for Spoolman with an NFC and QR location workflow:

1. Tap a spool NFC tag and open its notification, or open SpoolBud and scan a spool QR.
2. On the selected-spool page, choose a destination button, enter a location, tap a destination NFC tag, or scan its QR.
3. SpoolBud updates Spoolman, confirms the move, and clears the browser's spool selection after success. Failed moves retain the selection so you can check and retry.

Existing `/scan?value=...` links without `stay=1` and `/bin/<location>` links without `stay=1` still redirect to Spoolman. Opening a bin with no selected spool shows its contents.

Spool selection is stored in a browser cookie. Use the same SpoolBud hostname and browser profile for both taps/scans; private browsing and different browsers have separate selections. Use **Cancel selection** to discard an unfinished move. Destination buttons and the in-page QR scanner check the spool ID shown on the page to reject stale selections.

## Why this exists

When spool QR codes point directly to `https://<spoolman>/spool/show/<id>`, the helper cannot see which spool was chosen.
This service solves that by routing spool scans through `/scan`, storing the selected spool ID, and then handling subsequent bin scans.

## Endpoints

- `GET /healthz` — health probe
- `GET /status` — current selected spool for this browser session
- `GET /scan?value=<spool_url_or_id_or_spoolman_payload>[&stay=1]` — parse spool ID, set cookie, then either redirect to Spoolman (default) or stay in SpoolBud with a destination picker and optional QR scanner
  - When `stay=1` is used, the selected-spool page also shows the spool name/details returned by Spoolman when available.
- `GET /select/{spool_id}` — manual fallback spool selection (for old direct Spoolman QR labels)
- `GET /bin/{location}[?stay=1]` — move the selected spool, or show bin contents without a selection. `stay=1` shows confirmation in SpoolBud; omission preserves the Spoolman redirect. Optional `spool_id` checks the expected selection for in-page QR scans. Location names may include spaces and slashes; URL-encode the entire name.
- `POST /api/move` — JSON `{ "spool_id": 42, "location": "F-001" }`; checks the selected cookie, updates Spoolman, and clears selection on success. Returns JSON with the spool ID and normalized location; mismatched selection returns 409.
- `POST /api/selection/clear` — JSON `{ "spool_id": 42 }`; cancels only the matching selection
- `GET /bins` — destination QR labels and NFC links
- `GET /spools` — searchable spool tag preparation with NFC links and either Spoolman-compatible QR payloads or full SpoolBud URLs
- `GET /api/bins?source=default|spoolman|all` — fetch defaults, used Spoolman locations, or configured/default destinations combined with used locations. `all` returns a warning and the configured/default list if Spoolman is unavailable.
- `GET /api/spools` — returns existing `spool_ids` plus `spools` summaries with description, color, and locations for tag preparation
- `GET /qr.svg?value=<url_or_text>` — render QR code SVG for labels

## Environment variables

- `SPOOLMAN_BASE` (default `https://filament.igetno.net`)
- `SPOOLMAN_API_TOKEN` (optional bearer token)
- `COOKIE_NAME` (default `last_spool_id`)
- `DESTINATIONS` (optional comma- or newline-separated names, e.g. `F-001,F-002,PRINTER-1`). These remain selectable even when empty. If unset, the picker uses built-in defaults plus used Spoolman locations. Names are trimmed and uppercased, matching existing bin behavior. Restart the service after changing configuration; editing the label-page text does not persist destinations.

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

## Prepare a new spool and write its NFC tag

1. Create each physical spool in Spoolman, choosing its filament and entering its details. Two identical rolls need separate spool records.
2. Open `/spools` in SpoolBud and choose **Load from Spoolman**. Search the loaded labels by ID, manufacturer, material, color, or location. Refresh this list after creating another spool.
3. Check the spool details and public SpoolBud base URL, then choose **Copy NFC link**. If clipboard access is unavailable, manually copy the visible selected link.
4. In NFC Tools on the iPhone: **Write → Add a record → URL/URI**, paste the link, then **Write** and hold the phone near the sticker. Use one website record; replace any old record when reusing a writable sticker.
5. Leave the writing screen, tap the tag, and open the notification. Verify the expected spool in SpoolBud before attaching the sticker, then choose its destination.

SpoolBud prepares links; the writing app performs the physical NFC write. Copying a link is not proof that a tag was written, so always perform the tap-back check. No tag UID registration, native app, or additional database is required for this URL flow. External readers that send tag UIDs and filament-data tag formats are not supported by this change.

The tag identifies the spool; filament details and current location remain in Spoolman. Moving the spool does not require rewriting its tag. A replacement tag uses the same link. Reusing a writable sticker for a new roll requires a new spool record and overwriting the link with that new ID.

Example NFC link (also the default full-URL QR format):

```text
https://spoolbud.example.net/scan?value=42&stay=1
```

Use your stable, phone-accessible HTTPS SpoolBud hostname. Both SpoolBud and the phone need access to their configured services. The selected-spool screen does not automatically start the camera; **Open bin scanner** is optional. QR scanning uses native barcode detection when available and a compatibility decoder otherwise.

## Prepare destination tags and QR labels

Open `/bins` to load configured/default destinations plus used Spoolman locations, or enter names one per line. **Render labels** produces matching printable QR codes and **Copy NFC link** buttons. Buckets and printer positions use the same location field in Spoolman.

```text
https://spoolbud.example.net/bin/F-001?stay=1
https://spoolbud.example.net/bin/PRINTER%20%2F%20LEFT?stay=1
```

Write each link as a URL/URI record using the same steps as spool tags. Cancel any active spool selection before testing a destination tag if you only want to inspect the bin: opening a destination link with a selected spool performs a move.

## Existing QR labels

Existing bin links keep working without changes:

```text
https://spoolbud.example.net/bin/F-001
```

The spool preparation page still offers Spoolman's scanner payload format:

```text
web+spoolman:s-42
```

Scan that payload using SpoolBud's homepage camera scanner. NFC links always use full SpoolBud URLs, regardless of the QR format selected. Spool URLs such as `/spool/show/42`, `/spool/42`, query values such as `?spool_id=42`, and numeric IDs remain supported. The `/select/42` fallback remains available.

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

## Migration phase 1: Spoolman-owned tag resolution

New NFC/RFID identity is resolved by Spoolman 0.27+. Send a hardware UID to
SpoolBud's `POST /api/tag/scan` as JSON, optionally including `reader_id`, `name`,
`format`, and opaque `payload_b64`. SpoolBud forwards these fields unchanged to
Spoolman's `POST /api/v1/tag/scan` and uses only `matched_spool_id` from its reply.
It does not decode tag contents, derive IDs, or cache associations.

A positive match selects that spool in the requesting session. A null match
clears selection and asks you to link the tag in Spoolman. Invalid scans,
malformed responses, and unavailable services also clear old selection. The
response returns a match or an actionable error without upstream details.
QR selection remains available on older Spoolman servers.

A device's HTTP request cannot select a different browser. Use the browser's
own scan form (phase 2), or a client that retains the session cookie and follows
up in that same session. `reader_id` is upstream metadata, not session pairing.
The preceding NFC-writing instructions describe the superseded prototype and
are removed in the next UI migration phase; do not prepare new ID-based tags.
