# Spoolman NFC compatibility migration

This refinement replaces the earlier 0.27-only tag-scanner design after confirming
that Spoolman 0.27 is not yet released. SpoolBud remains additive: existing spool
QRs, bin QRs, selection cookies, and location updates keep their current contracts.

## Current source of truth

Spoolman 0.26.x and SpoolSense associate an NFC hardware UID with a spool through:

```text
spool.extra.nfc_id
```

SpoolBud does not create a UID database or cache. It queries Spoolman for every
tap, validates the returned extra field after normalization, and sends only the
matched spool ID into the common selection and destination workflow.

The tagged Spoolman 0.26 source confirms the supported filter is:

```text
GET /api/v1/spool?extra.nfc_id=<uid>
```

The filter is not treated as authoritative by itself: missing extra-field
configuration or partial matching can return unrelated rows. Zero locally
validated matches is an unassigned tag; multiple validated matches is an
operator configuration error.

## iPhone entry point

New NFC labels contain a stable NDEF URL:

```text
https://<spoolbud>/tag/<uid>
```

The iPhone opens that URL. There is no Safari Web NFC integration and no spool ID
on the tag. After lookup, `/tag/{uid}` renders the same selected-spool destination
page used by QR selection.

## First-tap association

When `/tag/{uid}` has no validated match, SpoolBud clears any older selection
and renders **Unassigned NFC Tag** with a searchable list of existing Spoolman
spools. The operator chooses a spool and explicitly submits the association.
SpoolBud then:

1. re-checks that the UID was not associated while the page was open;
2. reloads the selected spool and preserves all of its existing extra fields;
3. requires confirmation before replacing a different `nfc_id`;
4. patches the merged extra-field object with the canonical UID; and
5. verifies Spoolman's response before selecting the spool.

This creates no local mapping and no new spool. It is a server-side metadata
update to the authoritative Spoolman record. Errors clear the browser selection
and leave an actionable message on the assignment page.

## Future native lookup

The Spoolman client owns the version boundary. It consults the server's documented
`/api/v1/info` response, and only a server advertising 0.27+ is queried with:

```text
GET /api/v1/spool?tag=<uid>
```

An unsupported or unmatched native query falls back to `extra.nfc_id`. This keeps
0.26 functional without depending on unreleased behavior and gives native tag
support one isolated seam when 0.27 ships.

## Verification

Automated coverage includes UID normalization, valid/no/duplicate legacy matches,
first-tap assignment, preservation of unrelated extra fields, confirmed
replacement, stale-page conflicts, malformed extra fields, native capability and
fallback, transport failures, `/tag/{uid}` result pages, selection-to-location
movement, invalid destinations, and the unchanged QR/bin contracts. Hardware
validation still requires an iPhone and a physical NDEF URL tag in the deployed
environment.
