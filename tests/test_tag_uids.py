import pytest

from spoolbud.parsing.tag_uids import normalize_uid


@pytest.mark.parametrize(
    "value",
    [
        "04A2B3C4",
        "04:A2:B3:C4",
        "04-A2-B3-C4",
        "04 a2 b3 c4",
        "04a2b3c4",
    ],
)
def test_normalize_uid_accepts_common_representations(value):
    assert normalize_uid(value) == "04A2B3C4"


@pytest.mark.parametrize(
    "value",
    ["", "   ", "04A2?B3", "04/A2/B3", "0x04A2", "ABC", "04::A2", "AA" * 65],
)
def test_normalize_uid_rejects_empty_unexpected_or_incomplete_values(value):
    with pytest.raises(ValueError):
        normalize_uid(value)


def test_normalize_uid_rejects_non_text():
    with pytest.raises(ValueError):
        normalize_uid(42)  # type: ignore[arg-type]
