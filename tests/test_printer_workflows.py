import asyncio

import pytest

from printer_workflows import run_printer_action


class FakePrinter:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def load_spool(self, **target):
        self.calls.append(("load", target))
        if self.error:
            raise self.error

    async def unload_spool(self, **target):
        self.calls.append(("unload", target))
        if self.error:
            raise self.error


@pytest.mark.parametrize("action", ["load", "unload"])
def test_printer_actions_forward_only_canonical_identity_and_explicit_target(action):
    printer = FakePrinter()
    asyncio.run(run_printer_action(action, spool_id=42, station_id="station-A", slot_id="left", integration=printer))
    assert printer.calls == [(action, {"spool_id": 42, "station_id": "station-A", "slot_id": "left"})]


@pytest.mark.parametrize("target", [{"spool_id": "04AABB"}, {"spool_id": "42"}, {"spool_id": True},
                                     {"spool_id": 0}, {"station_id": ""}, {"slot_id": ""}, {"action": "store"}])
def test_invalid_action_or_target_never_calls_printer(target):
    printer = FakePrinter()
    args = {"action": "load", "spool_id": 42, "station_id": "station-A", "integration": printer}
    args.update(target)
    with pytest.raises(ValueError):
        asyncio.run(run_printer_action(**args))
    assert printer.calls == []


def test_printer_workflow_is_explicitly_unavailable_without_adapter():
    with pytest.raises(NotImplementedError, match="No printer integration"):
        asyncio.run(run_printer_action("load", spool_id=42, station_id="station-A"))


@pytest.mark.parametrize("action", ["load", "unload"])
def test_uncertain_printer_result_propagates_without_retry(action):
    printer = FakePrinter(TimeoutError("Unconfirmed printer operation"))
    with pytest.raises(TimeoutError):
        asyncio.run(run_printer_action(action, spool_id=42, station_id="station-A", integration=printer))
    assert len(printer.calls) == 1
