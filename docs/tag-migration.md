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
