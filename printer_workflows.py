"""Future printer actions: no tag identity, inventory state, or vendor HTTP here."""
from __future__ import annotations

from typing import Literal, Protocol


class PrinterIntegration(Protocol):
    """Adapters return only after confirmation; failures/uncertain results raise.

    The adapter must check the expected spool when unloading a slot. Station and
    slot IDs belong to the integration, not to Spoolman's location field.
    """

    async def load_spool(self, *, spool_id: int, station_id: str, slot_id: str | None) -> None: ...

    async def unload_spool(self, *, spool_id: int, station_id: str, slot_id: str | None) -> None: ...


async def run_printer_action(
    action: Literal["load", "unload"],
    *,
    spool_id: int,
    station_id: str,
    slot_id: str | None = None,
    integration: PrinterIntegration | None = None,
) -> None:
    """Dispatch an explicit action using a resolved canonical spool ID.

    Future routes must first verify their current session selection. This helper
    never changes inventory, clears selection, retries, or guesses an adapter.
    """
    if action not in {"load", "unload"}:
        raise ValueError("Unsupported printer action")
    if type(spool_id) is not int or spool_id <= 0:
        raise ValueError("A canonical Spoolman spool ID is required")
    if not isinstance(station_id, str) or not station_id.strip():
        raise ValueError("An explicit printer station is required")
    if slot_id is not None and (not isinstance(slot_id, str) or not slot_id.strip()):
        raise ValueError("Slot ID must be nonempty when provided")
    if integration is None:
        raise NotImplementedError("No printer integration is configured")
    operation = integration.load_spool if action == "load" else integration.unload_spool
    await operation(spool_id=spool_id, station_id=station_id, slot_id=slot_id)
