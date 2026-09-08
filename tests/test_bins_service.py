from spoolbud.services.bins import configured_bins, spool_location_values, spools_in_location


def test_configured_bins_normalize_and_deduplicate():
    assert configured_bins(" f-001, printer / left\nF-001 ") == ["F-001", "PRINTER / LEFT"]


def test_spool_location_values_support_legacy_fields():
    spool = {"location": "f-001", "bin": "b-001", "extra": {"location": "overflow"}}
    assert spool_location_values(spool) == {"F-001", "B-001", "OVERFLOW"}


def test_spools_in_location_matches_normalized_locations():
    spools = [{"id": 1, "location": "f-001"}, {"id": 2, "location": "F-002"}]
    assert spools_in_location(spools, " F-001 ") == [spools[0]]
