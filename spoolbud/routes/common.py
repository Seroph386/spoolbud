"""Small helpers shared by route groups."""


def wants_scan_stay(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}
