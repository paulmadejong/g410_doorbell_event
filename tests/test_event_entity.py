"""Event entity tests."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import custom_components.g410_doorbell_event.event as event_module
from custom_components.g410_doorbell_event.event import G410DoorbellRingEventEntity
from custom_components.g410_doorbell_event.models import DoorbellCandidate, MonitorState


@dataclass
class FakeServerInfo:
    """Minimal Matter server info."""

    compressed_fabric_id: int


class FakeMonitor:
    """Minimal monitor stub for event entity tests."""

    def __init__(self) -> None:
        self.matter_client = SimpleNamespace(
            server_info=FakeServerInfo(compressed_fabric_id=0x134B)
        )
        self.state = MonitorState(
            candidate=DoorbellCandidate(
                node_id=3,
                endpoint_id=2,
                node_name="G410",
                endpoint_name="Doorbell",
                score=100,
                reasons=("occupancy sensing cluster present",),
            ),
            status="ready",
            detail="ready",
        )
        self._listener = None

    def async_add_ring_listener(self, listener):
        self._listener = listener
        return lambda: None


def test_event_entity_links_to_matter_device_identifier() -> None:
    """Event entity should attach to the resolved Matter device."""

    entity = G410DoorbellRingEventEntity(FakeMonitor())

    assert entity._attr_device_info["identifiers"] == {
        ("matter", "deviceid_000000000000134B-0000000000000003-MatterNodeDevice")
    }


def test_event_entity_falls_back_without_helper() -> None:
    """Older HA versions without the Matter helper should still work."""

    original_helper = event_module.get_node_device_identifier
    event_module.get_node_device_identifier = None
    try:
        entity = G410DoorbellRingEventEntity(FakeMonitor())
    finally:
        event_module.get_node_device_identifier = original_helper

    assert entity._attr_device_info["identifiers"] == {
        ("g410_doorbell_event", "g410_doorbell_event")
    }


def test_event_entity_triggers_standard_ring_event() -> None:
    """Event entity should emit the standard ring event type."""

    entity = G410DoorbellRingEventEntity(FakeMonitor())
    captured: list[tuple[str, dict]] = []
    entity._trigger_event = lambda event_type, data: captured.append((event_type, data))
    entity.async_write_ha_state = lambda: None

    entity._handle_ring_event({"event_type": "ring", "node_id": 3})

    assert captured == [("ring", {"event_type": "ring", "node_id": 3})]
