"""Spoolman extra-field wire-format helpers."""

from __future__ import annotations

import json


def decode_text_extra(value: object) -> str | None:
    """Decode a Spoolman text extra, accepting legacy raw strings defensively."""
    if not isinstance(value, str):
        return None
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(decoded, str):
            return None
        value = decoded
    elif value == "null":
        return None
    return value if value.strip() else None


def encode_text_extra(value: str) -> str:
    """Encode a text value for Spoolman's uniform extra-field wire format."""
    return json.dumps(value)
