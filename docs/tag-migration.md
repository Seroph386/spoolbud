# Spoolman tag identity migration

This migration replaces the earlier uncommitted URL-tag prototype. The existing
branch also contains its destination picker, QR improvements, and tests; these
are retained where compatible. No tag database or tag writer is being added.

## Review phases

0. **Architecture first:** update `AGENTS.md` before implementation and record
   ownership, compatibility rules, and this phased plan. Establish the existing
   34-test baseline.
1. **Spoolman tag resolution:** add a narrowly scoped HTTP integration and a
   session-aware scan endpoint. Trust only `matched_spool_id`, clear selection
   for unknown/error results, and test the real wire contract with mock HTTP.
2. **Workflow UI migration:** add UID/reader input, reuse the selected-spool
   screen without routing NFC through QR parsing, and remove NFC-writing tools.
   Retain spool/bin QR labels and existing URL entry points. Document linking
   tags in Spoolman and browser/device session boundaries. Test tag-to-move and
   legacy behavior; check the browser with mock inventory.
3. **Future station boundary:** define a minimal vendor-neutral printer adapter
   contract for load/unload, separate from inventory/location operations. Test
   with a fake adapter; document what a future FilaBridge adapter must supply.
   No printer actions are advertised as implemented in this migration.

Each phase gets a separate local commit after its tests pass; the earlier
prototype is preserved as a distinct baseline commit so the migration diffs
can be reviewed independently. No remote push or deployment is included.

## Sources and compatibility

- [Spoolman tag scanners](https://github.com/Donkie/Spoolman/wiki/Tag-scanners)
- [Spoolman API reference](https://donkie.github.io/Spoolman/)

Tag scanning requires Spoolman 0.27+; earlier servers keep the QR/move path but
receive an upgrade message when the tag endpoint is unavailable. Physical tag
readers and iPhone companion-app integration require a separate hardware pilot.

## Phase 1 result

Implemented `spoolman_tags.py` and `/api/tag/scan` with per-request matching and
explicit failures. All 70 tests pass, including contract forwarding, upstream
reassignment, rejection of client-supplied matches, session isolation, malformed
input/responses, upstream errors, and the 34 compatibility tests. Docker now
copies the integration module. The source API was checked directly because the
published generated OpenAPI reference did not include the tag endpoints:
[upstream tag.py](https://github.com/Donkie/Spoolman/blob/master/spoolman/api/v1/tag.py).

## Phase 2 result

The home page accepts reader-entered/pasted UIDs and offers read-only Web NFC
when supported. NFC responses navigate to `/selected`, which reads workflow
context without parsing QR data or reselecting an ID. Legacy QR URLs reuse the
same action renderer. NFC-writing controls and instructions have been removed;
Spoolman linking and iPhone/session limitations are documented in README.

All 75 tests pass. Browser verification with a mock upstream covered keyboard
UID submission, selection, explicit storage, unknown tags clearing a previous
selection, and QR label generation. Embedded JavaScript syntax checks passed.
Physical Web NFC and external reader hardware still require a deployment pilot.

## Phase 3 result

Added the small `PrinterIntegration` protocol and explicit load/unload dispatcher
in `printer_workflows.py`, independently of tag resolution and storage updates.
It rejects invalid identities/targets, fails without an adapter, and propagates
uncertain results without retry. README specifies the responsibilities of a
future FilaBridge or other adapter and of future session-aware action routes.
All 87 tests pass, including fake-adapter dispatch and failure coverage. No real
printer action, printer endpoint, or new persistent state has been introduced.

## Final validation

The tag request model requires Pydantic 2, now declared explicitly in runtime
requirements instead of relying on FastAPI's broader transitive requirement.
Reader ID validation stays on the server so invalid submissions clear the old
selection through the same error path as other invalid scans.

The full 87-test suite and embedded JavaScript syntax checks pass. Compose
configuration validation passes. The container build could not run because the
local Docker daemon is stopped; it still needs verification in CI or with Docker
running. Browser checks used mock inventory, not a live Spoolman server or
physical NFC/RFID reader.
