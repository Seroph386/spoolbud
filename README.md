# SpoolBud physical filament workflows

SpoolBud is a lightweight UI for selecting and moving/storing filament spools.
Spoolman 0.27+ owns inventory, metadata, locations, and NFC/RFID tag associations.
SpoolBud has no tag database, inventory mirror, or NFC writer.

1. Open SpoolBud. Use a reader to enter a tag UID, or scan a compatibility spool QR.
2. Tag scans are resolved by Spoolman's `POST /api/v1/tag/scan`. Only its
   `matched_spool_id` becomes the selected spool.
3. Check the selected spool's details, then choose a storage location or scan a
   bin QR. Scanning a spool alone never moves it or loads a printer.
4. A successful location update clears selection; failed moves keep it for retry.
   Use **Cancel selection** to abandon an unfinished workflow.

## New spools and tag associations

Create each physical spool in Spoolman. In that spool's **Tags** section, use
**Add tag** to associate the hardware UID supplied by your reader. Link, unlink,
or move that association in Spoolman when reusing a tag. No spool ID needs to be
written to the tag. SpoolBud queries Spoolman again on every scan, so reassignment
is picked up without updating labels or a local mapping.

See [Spoolman's tag-scanner guide](https://github.com/Donkie/Spoolman/wiki/Tag-scanners)
for linking and reader setup. Tag contents are not automatically converted into
filament metadata; create inventory in Spoolman before linking it.

## How a reader supplies a scan

- **Keyboard reader:** focus **Tag UID** on SpoolBud's home page. Configure the
  reader to enter the hardware UID as hex followed by Enter. The browser submits
  the scan using its own session. Reader ID is optional descriptive metadata.
- **Paste/type:** enter the UID reported by your reader app and press **Find spool
  in Spoolman**. This uses the same API as a keyboard reader.
- **Supported Android browser:** **Read tag with this phone** appears when Web NFC
  is available in a secure context. It submits only the hardware serial number;
  it does not decode NDEF records or write tags. Web NFC has tag/hardware limits;
  a compatible external reader may be needed for vendor tags.
- **iPhone Safari:** direct UID reading is unavailable. Use a reader or companion
  app to supply the UID; a blank tag does not automatically open SpoolBud. This
  migration does not include a native iPhone app or a background reader listener.

Spoolman's upstream reader pairing controls its own UI; it does not pair a
SpoolBud browser. A standalone device POST selects only that HTTP client's
session, not a tablet elsewhere. For the current UI, use a keyboard reader or
submit through the browser. Future network-reader handoff must explicitly bind
reader events to a browser/station rather than sharing a global selected spool.
A `reader_id` is metadata, not authentication or a session token. Supplying a
stable ID also avoids Spoolman deriving it from the shared SpoolBud server IP.

## Scan API contract

Example request to **SpoolBud**, with JSON content type:

```http
POST /api/tag/scan
Content-Type: application/json

{"uid":"04:A2:B3:C4:D5:E6:F7","reader_id":"desk-reader","name":"Desk"}
```

Optional `format` and `payload_b64` fields are forwarded unchanged. UID
normalization and matching belong entirely to Spoolman. Payloads are never
parsed for IDs. Client-supplied `matched_spool_id` or `spool_id` fields are rejected.

A successful reply is `{"matched_spool_id":42}` plus the selected-spool cookie.
The same client can open `/selected` or perform an explicit move. Browser clients
must retain the cookie. A `null` match returns 200 with guidance to link the tag
in Spoolman and clears any older selection. Invalid input/rejected scans return
400; upstream failures or invalid match responses return 502. All these failure
paths clear selection rather than leaving an earlier spool ready to move.
There is no automatic retry, local tag match, spool creation, or tag registration.

Tag scanning requires the upstream endpoint to be available in Spoolman 0.27+.
A missing endpoint produces an upgrade/configuration message; older servers
continue to support the compatibility QR and location-update workflows.

## Endpoints

- `POST /api/tag/scan` — resolve a hardware UID through Spoolman; see the contract below
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
verify a Spoolman tag association. Do not prepare new NFC tags with these links;
associate their UIDs in Spoolman instead. Bin URL tags that already exist also
continue to open the corresponding bin route.

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
