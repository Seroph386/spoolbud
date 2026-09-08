"""Parse spool identities from Spoolman and legacy SpoolBud references."""

from __future__ import annotations

import re


SPOOL_ID_PATTERNS = (
    r"(?i)web\+spoolman:s-(\d+)",
    r"/spool/show/(\d+)",
    r"/spool/(\d+)",
    r"[?&]spool_id=(\d+)",
    r"^(\d+)$",
)


def extract_spool_id(value: str | None) -> int | None:
    if not value:
        return None

    candidate = value.strip()
    for pattern in SPOOL_ID_PATTERNS:
        match = re.search(pattern, candidate)
        if match:
            return int(match.group(1))
    return None
