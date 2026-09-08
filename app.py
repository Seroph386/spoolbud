"""Uvicorn entry point and backwards-compatible public helpers."""

from spoolbud.application import create_app
from spoolbud.config import settings
from spoolbud.dependencies import (
    fetch_spoolman_locations,
    fetch_spoolman_spool,
    fetch_spoolman_spools,
    fetch_spools_in_location,
    patch_spool_location,
)
from spoolbud.parsing.spool_ids import extract_spool_id
from spoolbud.services.bins import default_bins


SPOOLMAN_BASE = settings.spoolman_base
API_TOKEN = settings.spoolman_api_token
COOKIE_NAME = settings.cookie_name
COOKIE_MAX_AGE = settings.cookie_max_age
DESTINATIONS = settings.destinations

app = create_app()
