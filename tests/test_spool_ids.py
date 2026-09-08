import pytest

from spoolbud.parsing.spool_ids import extract_spool_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("web+spoolman:s-42", 42),
        ("https://spoolman.example/spool/show/42", 42),
        ("https://spoolman.example/spool/42", 42),
        ("/spool/show/42", 42),
        ("/spool/42", 42),
        ("https://spoolman.example/thing?spool_id=42", 42),
        ("42", 42),
        (" 42 ", 42),
        ("", None),
        (None, None),
        ("not-a-spool", None),
    ],
)
def test_extract_spool_id(value, expected):
    assert extract_spool_id(value) == expected
