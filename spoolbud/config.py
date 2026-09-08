"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    spoolman_base: str
    spoolman_api_token: str
    cookie_name: str
    cookie_max_age: int
    destinations: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            spoolman_base=os.getenv("SPOOLMAN_BASE", "https://filament.igetno.net").rstrip("/"),
            spoolman_api_token=os.getenv("SPOOLMAN_API_TOKEN", ""),
            cookie_name=os.getenv("COOKIE_NAME", "last_spool_id"),
            cookie_max_age=60 * 60 * 24 * 30,
            destinations=os.getenv("DESTINATIONS", ""),
        )


settings = Settings.from_env()
