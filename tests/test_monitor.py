"""Monitor behavior tests."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from custom_components.g410_doorbell_event.models import DoorbellCandidate, MonitorState
from custom_components.g410_doorbell_event.monitor import DoorbellMonitor


@dataclass
class FakeBus:
    """Capture fired Home Assistant bus events."""

    events: list[tuple[str, dict]]

    def async_fire(self, event_type: str, event_data: dict) -> None:
        self.events.append((event_type, event_data))


def _make_monitor() -> tuple[DoorbellMonitor, list[tuple[str, dict]]]:
    """Create a monitor instance without constructing full Matter runtime."""

    bus_events: list[tuple[str, dict]] = []
    monitor = DoorbellMonitor.__new__(DoorbellMonitor)
    monitor.hass = SimpleNamespace(bus=FakeBus(bus_events), async_create_task=lambda coro: coro)
    monitor.matter_client = SimpleNamespace(server_info=None)
    monitor.state = MonitorState(
        candidate=DoorbellCandidate(
            node_id=3,
            endpoint_id=2,
            node_name="G410",
            endpoint_name="Doorbell",
            score=100,
            reasons=("occupancy sensing cluster present",),
        ),
        status="ready",
        detail="test",
    )
    monitor._listeners = []
    return monitor, bus_events


def test_monitor_handles_nested_occupancy_payload_and_fires_legacy_event() -> None:
    """Nested occupancyChanged payloads should still emit the ring event."""

    monitor, bus_events = _make_monitor()
    listener_calls: list[dict] = []
    monitor.async_add_ring_listener(listener_calls.append)

    payload = {"occupancy": {"occupied": True}}
    data = SimpleNamespace(
        node_id=3,
        endpoint_id=2,
        cluster_id=0x0406,
        data=payload,
        event_id=1,
        event_number=2,
        priority=3,
        timestamp=4,
        timestamp_type="system",
    )

    monitor._handle_node_event("node_event", data)

    assert len(listener_calls) == 1
    assert listener_calls[0]["event_type"] == "ring"
    assert bus_events[0][0] == "g410_doorbell_event"
    assert bus_events[0][1]["raw_data"] == payload


def test_monitor_ignores_non_occupied_event() -> None:
    """occupied=false must not emit a ring event."""

    monitor, bus_events = _make_monitor()
    listener_calls: list[dict] = []
    monitor.async_add_ring_listener(listener_calls.append)

    data = SimpleNamespace(
        node_id=3,
        endpoint_id=2,
        cluster_id=0x0406,
        data={"occupancy": {"occupied": False}},
        event_id=1,
        event_number=2,
        priority=3,
        timestamp=4,
        timestamp_type="system",
    )

    monitor._handle_node_event("node_event", data)

    assert listener_calls == []
    assert bus_events == []
