# AGENTS.md — SpoolBud Architecture and Agent Guidance

Scope: the entire repository. Read this before implementing changes.

## Product intent and ownership

SpoolBud is a lightweight physical filament workflow UI for Spoolman 0.27+.
Spoolman is authoritative for spool inventory, filament metadata, locations, and
NFC/RFID tag associations. SpoolBud selects a spool and coordinates explicit
physical actions such as moving/storing it. Printer stations and load/unload
workflows are future extensions of this boundary.

## Identity and state rules

- Resolve every new NFC/RFID scan by forwarding its hardware UID to Spoolman's
  `POST /api/v1/tag/scan`. Only the returned `matched_spool_id` selects a spool.
- Never infer a spool ID from a UID, tag payload, reader ID, or a client-supplied
  match. Never maintain a local UID-to-spool map, cache, or tag database.
- Do not encode Spoolman IDs into NFC tags or offer NFC tag-writing workflows.
  Create spools and link/unlink/reassign their tags in Spoolman.
- An unknown tag or failed resolution must not leave an older spool selected
  for an accidental move. Show an actionable result; never silently fall back
  from NFC to QR parsing or create inventory/tag associations automatically.
- Browser selection is transient workflow context. Retain the existing cookie
  for compatibility, storing only the selected canonical spool ID. It is not
  an inventory or tag-association store and is not authentication.
- No new persistent database, global selected-spool state, or background queue.
  A device request does not select an unrelated browser: session handoff must
  be explicit. Reader identity is metadata, not browser identity or a secret.

## Boundaries

- Keep FastAPI routes and mobile UI thin. Reuse selection, metadata, and action
  helpers for NFC and compatibility QR entry points.
- Isolate the Spoolman tag HTTP contract and its response validation. Pass
  canonical spool IDs to downstream workflows, never hardware UIDs/payloads.
- Moves/storage update Spoolman's location through its API. Local destination
  configuration and legacy defaults are shortcuts, not authoritative state;
  successful location changes must be confirmed by Spoolman.
- Printer load/unload is distinct from storage/location updates. Keep a small
  vendor-neutral interface for station/slot identifiers and canonical spool
  IDs. FilaBridge/Moonraker/vendor APIs belong in future adapters, not in scan
  parsing, tag resolution, or generic move routes. Do not pretend that setting
  a location loads a printer, or expose working load/unload controls before an
  adapter and its failure/reconciliation behavior exist.

## Compatibility and operations

- Preserve `/scan?value=...`, `/select/{spool_id}`, `/bin/{location}`, `/status`,
  `/healthz`, spool QR scanning, and printable bin QR labels.
- QR parsing continues to support `/spool/show/<id>`, `/spool/<id>`,
  `?spool_id=<id>`, numeric IDs, and `web+spoolman:s-<id>`.
- Previously written ID-based URL tags may still open the legacy scan route;
  document them as compatibility links, not the new NFC identity model.
- Scanning selects only. New moves require an explicit user action. Keep legacy
  bin-link move behavior during migration, including its redirect semantics.
- Retain selection after failed moves; clear it on successful moves or cancel.
  Reject stale action requests when the selected spool has changed.
- Credentials come only from environment variables. Do not log tokens or raw
  tag payloads; never expose upstream credentials/errors to the UI.
- Escape user-controlled HTML and render browser labels with safe DOM APIs.
- Keep the container small and boot fast. Prefer simple functions and standard
  library types; add dependencies or abstractions only for concrete needs.

## Phased changes and verification

Implement small reviewable phases with tests and docs updated in each phase.
Update this file before changing these ownership or integration boundaries.
For endpoint changes update `tests/`, `README.md`, and workflow/QR examples.
For environment changes also update `docker-compose.yml` and CI assumptions.

Cover matched/unknown tags, malformed Spoolman responses, upstream errors,
no local matching, session isolation, stale selections, and unchanged QR/bin
contracts. Exercise the actual HTTP request/response boundary with mocked
transport. Test printer boundaries with fake adapters, never real printers.
Use mock inventory for browser tests; report actual hardware testing separately.

Run when feasible:

- `pytest -q`
- `docker compose config -q`
- `docker build -t spoolbud:test .`

No full authentication system, persistent inventory mirror, frontend SPA,
or printer-vendor implementation is part of this migration.
