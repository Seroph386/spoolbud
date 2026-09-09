"""Validation and canonicalization for NFC/RFID hardware UIDs."""

from __future__ import annotations

import re


_UID_PATTERN = re.compile(r"(?:[0-9A-Fa-f]{2})(?:[ :\-]?[0-9A-Fa-f]{2})*")
_UID_SEPARATORS = str.maketrans("", "", " :-")


def normalize_uid(value: str) -> str:
    """Return uppercase hex without separators, rejecting non-UID input."""
    if not isinstance(value, str):
        raise ValueError("NFC UID must be text.")
    uid = value.strip()
    if not uid or len(uid) > 128 or not _UID_PATTERN.fullmatch(uid):
        raise ValueError("NFC UID must contain hexadecimal byte pairs, with optional spaces, colons, or hyphens.")
    return uid.translate(_UID_SEPARATORS).upper()
