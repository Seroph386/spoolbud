# SpoolBud physical filament workflows

SpoolBud is a lightweight UI for selecting and moving/storing filament spools.
Spoolman owns inventory, metadata, locations, and NFC/RFID identity. Current
Spoolman 0.26.x + SpoolSense installations store that identity in the spool's
`extra.nfc_id` field. SpoolBud has no tag database or inventory mirror.

## Internal architecture

`app.py` is only the Uvicorn entry point. Application assembly lives in
`spoolbud/application.py`, which registers feature routers from
`spoolbud/routes/`. Route modules validate requests and coordinate work; they do
not contain page markup or direct HTTP calls.

- `spoolbud/clients/spoolman.py` owns Spoolman URLs, authentication headers,
  timeouts, version-compatible tag lookup, and response validation.
- `spoolbud/parsing/` owns NFC UID normalization and compatibility spool-reference parsing.
- `spoolbud/services/` owns cookie selection, bin workflows, and QR generation.
- `spoolbud/rendering/` owns HTML components, complete page rendering, CSS, and
  browser scripts.
- `spoolbud/dependencies.py` provides the small runtime boundary used by routes,
  keeping client and workflow substitutions straightforward in tests.

The package introduces no new runtime service or persistence. Uvicorn still
loads `app:app`, and all existing URLs and environment variables remain valid.

1. Tap a spool's NFC tag with an iPhone, or scan a compatibility spool QR.
2. The NFC tag opens `/tag/<uid>`. SpoolBud resolves that UID against Spoolman
   and selects only a validated matching spool.
3. Check the selected spool's details, then choose a storage location or scan a
   bin QR. Scanning a spool alone never moves it or loads a printer.
4. A successful location update clears selection; failed moves keep it for retry.
   Use **Cancel selection** to abandon an unfinished workflow.

## iPhone NFC workflow

1. Read the tag's hardware UID and write this NDEF URL to the tag:

   ```text
   https://<spoolbud>/tag/<uid>
   ```

2. The iPhone reads the NDEF URL and opens SpoolBud in the browser.
3. SpoolBud normalizes `<uid>` to uppercase hex and looks it up in Spoolman.
   If it is unassigned, search for and select the existing Spoolman spool;
   SpoolBud writes the normalized UID into that spool's `nfc_id` extra field.
4. Once associated, SpoolBud verifies the returned spool's `extra.nfc_id` and
   selects it.
5. Choose an F-series bin, B-series bin, another known location, or scan an
   existing bin QR code. SpoolBud updates that spool's Spoolman location.

The tag URL contains the hardware UID, not a Spoolman spool ID. The unassigned
page lists existing, non-archived Spoolman spools and filters them in the browser
by ID, material, vendor, location, or current NFC ID. Assigning never creates a
spool. Spoolman's wire format JSON-encodes every extra-field value, including
text fields. SpoolBud decodes those values for comparison/display and patches
only the encoded `nfc_id` key, so Spoolman's per-key merge preserves other extra
fields. Replacing a different current NFC ID requires confirmation.
The physical tag URL stays the same. iPhone is only responsible for opening the
NDEF URL; SpoolBud does not use Web NFC or any browser-side NFC API.

The home page also accepts a pasted or keyboard-reader UID and opens the same
`/tag/<uid>` workflow.

## Spoolman tag lookup compatibility

Spoolman 0.26.x supports filtering spools with:

```http
GET /api/v1/spool?extra.nfc_id=04A2B3C4D5E6F7
```

Extra-field filtering can be partial and a missing field can yield unrelated
rows, so SpoolBud never trusts the first result. It normalizes and compares each
decoded `extra.nfc_id`; zero validated matches is unknown, and multiple matches
are reported as a configuration error with links to the affected spool records.

The client checks Spoolman's own `/api/v1/info` response for capability. When a
future 0.27+ server advertises native tags, SpoolBud prefers
`GET /api/v1/spool?tag=<uid>` and falls back to `extra.nfc_id` when that lookup is
unsupported or unmatched. Current functionality does not depend on unreleased APIs.

## Scan API contract

Example request to **SpoolBud**, with JSON content type:

```http
POST /api/tag/scan
Content-Type: application/json

{"uid":"04:A2:B3:C4:D5:E6:F7","reader_id":"desk-reader","name":"Desk"}
```

Optional legacy reader metadata is accepted for compatibility but is not used
to identify a spool. UIDs are normalized server-side. Client-supplied
`matched_spool_id` or `spool_id` fields are rejected.

A successful reply is `{"matched_spool_id":42}` plus the selected-spool cookie.
The same client can open `/selected` or perform an explicit move. Browser clients
must retain the cookie. A `null` match returns 200 with guidance to open the
interactive tag URL and clears any older selection. Invalid input/rejected scans return
400; upstream failures or invalid match responses return 502. All these failure
paths clear selection rather than leaving an earlier spool ready to move.
There is no local UID map, spool creation, or automatic tag assignment. The
interactive `/tag/{uid}` page is the only assignment workflow and requires an
explicit spool choice.

## Endpoints

- `GET /tag/{uid}` — normalize an NDEF URL's hardware UID; resolve and select a known spool, or show the searchable assignment workflow for an unassigned UID
- `POST /tag/{uid}/assign` — JSON `{ "spool_id": 42, "replace_existing": false }`; re-check the UID, merge it into the selected spool's `extra.nfc_id`, verify the response, and select that spool
- `POST /api/tag/scan` — compatibility JSON entry point using the same UID resolver
- `GET /selected` — show actions for the session’s selected spool without parsing QR data or changing selection; returns 409 without a selection
- `GET /healthz` — health probe
- `GET /status` — current selected spool for this browser session
- `GET /scan?value=<spool_url_or_id_or_spoolman_payload>[&stay=1]` — parse spool ID, set cookie, then either redirect to Spoolman (default) or stay in SpoolBud with a destination picker and optional QR scanner
  - When `stay=1` is used, the selected-spool page also shows the spool name/details returned by Spoolman when available.
- `GET /select/{spool_id}` — manual fallback spool selection (for old direct Spoolman QR labels)
- `GET /bin/{location}[?stay=1]` — move the selected spool, or show bin contents without a selection. `stay=1` shows confirmation in SpoolBud; omission preserves the Spoolman redirect. Optional `spool_id` checks the expected selection for in-page QR scans. Location names may include spaces and slashes; URL-encode the entire name.
- `POST /api/move` — JSON `{ "spool_id": 42, "location": "F-001" }`; checks the selected cookie, updates Spoolman, and clears selection on success. Returns JSON with the spool ID and normalized location; mismatched selection returns 409.
- `POST /api/selection/clear` — JSON `{ "spool_id": 42 }`; cancels only the matching selection
- `GET /bins` — destination QR labels
- `GET /spools` — searchable compatibility spool QR labels
- `GET /api/bins?source=default|spoolman|all` — fetch defaults, used Spoolman locations, or configured/default destinations combined with used locations. `all` returns a warning and the configured/default list if Spoolman is unavailable.
- `GET /api/spools` — returns existing `spool_ids` plus `spools` summaries with description, color, and locations for QR labels
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

## Compatibility QR labels and existing URL tags

Open `/spools` to load spool details from Spoolman and print QR labels. It offers
both `web+spoolman:s-42` and full SpoolBud scan URLs. Open `/bins` to prepare stable
location QR labels. Example payloads:

```text
web+spoolman:s-42
https://spoolbud.example.net/scan?value=42&stay=1
https://spoolbud.example.net/bin/F-001?stay=1
https://spoolbud.example.net/bin/PRINTER%20%2F%20LEFT?stay=1
```

Previously written ID-based URL tags still reach the legacy scan route, just as
an existing QR or manually opened link does. This compatibility path does **not**
verify `extra.nfc_id`. Prepare new NFC tags with `/tag/<uid>` URLs; the first tap
can associate the UID with an existing spool from SpoolBud. Bin URL tags that
already exist also continue to open the corresponding bin route.

`/scan` without `stay=1` and `/select/{spool_id}` keep their Spoolman redirects.
`/bin/{location}` without `stay=1` still moves a selected spool and redirects to
Spoolman; `stay=1` shows confirmation in SpoolBud. Without a selected spool, a
bin scan shows its contents. QR parsing still accepts `/spool/show/<id>`,
`/spool/<id>`, `?spool_id=<id>`, numeric IDs, and native Spoolman QR payloads.

Selection is a transient browser cookie, not an inventory record. Keep scans and
moves in the same hostname/browser profile. Destination actions reject stale
spool selections. Local `DESTINATIONS` and default bins are operator shortcuts;
Spoolman remains authoritative for the location actually stored on each spool.
Setting a printer-like location name only stores a location; it does not load
filament into a printer or configure printer usage tracking.

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


Review the implementation phases in [docs/tag-migration.md](docs/tag-migration.md).

## Future printer stations and load/unload

`printer_workflows.py` defines `PrinterIntegration.load_spool` and
`unload_spool`, plus an explicit dispatcher. Calls carry a canonical Spoolman
spool ID, station ID, and optional slot ID. No UID, tag payload, or location name
is used to infer a printer target. No concrete adapter, printer endpoint, or
load/unload UI is enabled yet; a missing adapter fails explicitly.

A future FilaBridge or other adapter owns its transport, environment credentials,
station/slot mapping, and confirmation/error handling. It must verify the
expected loaded spool before unloading, return only after confirmed success,
and report uncertain results for reconciliation. Future action routes must
check the browser's current selection before dispatch. They must retain it on
failure and reconcile partial operations before claiming a combined load/store
success. The dispatcher neither retries nor changes Spoolman inventory.

Moves/storage remain independent Spoolman location updates. New printer
adapters should be separately reviewed and tested against fake hardware first.
