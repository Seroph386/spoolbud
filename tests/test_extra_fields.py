import pytest

from spoolbud.parsing.extra_fields import decode_text_extra, encode_text_extra


@pytest.mark.parametrize(
    "wire_value, expected",
    [
        ('"04D6317FD22A81"', "04D6317FD22A81"),
        ('""', None),
        ("null", None),
        ("04D6317FD22A81", "04D6317FD22A81"),
        ("", None),
        ('"unterminated', None),
        (42, None),
        (None, None),
    ],
)
def test_decode_text_extra(wire_value, expected):
    assert decode_text_extra(wire_value) == expected


def test_encode_text_extra_uses_spoolman_wire_format():
    assert encode_text_extra("04D6317FD22A81") == '"04D6317FD22A81"'
