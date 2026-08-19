"""Monitor behavior tests."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

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
    monitor._unsubscribers = []
    monitor.state.armed_at_monotonic = 100.0
    return monitor, bus_events


def test_monitor_suppresses_initial_true_during_startup_window() -> None:
    """An initial occupied=true right after startup should be ignored."""

    monitor, bus_events = _make_monitor()
    listener_calls: list[dict] = []
    monitor.async_add_ring_listener(listener_calls.append)

    initial_true = SimpleNamespace(
        node_id=3,
        endpoint_id=2,
        cluster_id=0x0406,
        data={"occupancy": {"occupied": True}},
        event_id=1,
        event_number=2,
        priority=3,
        timestamp=4,
        timestamp_type="system",
    )

    with patch(
        "custom_components.g410_doorbell_event.monitor.time.monotonic",
        return_value=105.0,
    ):
        monitor._handle_node_event("node_event", initial_true)

    assert listener_calls == []
    assert bus_events == []


def test_monitor_allows_first_true_after_startup_window() -> None:
    """A first occupied=true later on should still create a ring event."""

    monitor, bus_events = _make_monitor()
    listener_calls: list[dict] = []
    monitor.async_add_ring_listener(listener_calls.append)

    true_data = SimpleNamespace(
        node_id=3,
        endpoint_id=2,
        cluster_id=0x0406,
        data={"occupancy": {"occupied": True}},
        event_id=3,
        event_number=4,
        priority=3,
        timestamp=6,
        timestamp_type="system",
    )

    with patch(
        "custom_components.g410_doorbell_event.monitor.time.monotonic",
        return_value=111.0,
    ):
        monitor._handle_node_event("node_event", true_data)

    assert len(listener_calls) == 1
    assert [event[0] for event in bus_events] == ["g410_doorbell_event", "aqara_g410_ring"]
    assert bus_events[0][1]["raw_data"] == {"occupancy": {"occupied": True}}


def test_monitor_allows_false_to_true_transition() -> None:
    """A later false->true transition should emit a ring event once."""

    monitor, bus_events = _make_monitor()
    listener_calls: list[dict] = []
    monitor.async_add_ring_listener(listener_calls.append)

    false_data = SimpleNamespace(
        node_id=3,
        endpoint_id=2,
        cluster_id=0x0406,
        data={"occupancy": {"occupied": False}},
        event_id=2,
        event_number=3,
        priority=3,
        timestamp=5,
        timestamp_type="system",
    )
    true_data = SimpleNamespace(
        node_id=3,
        endpoint_id=2,
        cluster_id=0x0406,
        data={"occupancy": {"occupied": True}},
        event_id=3,
        event_number=4,
        priority=3,
        timestamp=6,
        timestamp_type="system",
    )

    with patch(
        "custom_components.g410_doorbell_event.monitor.time.monotonic",
        return_value=111.0,
    ):
        monitor._handle_node_event("node_event", false_data)
        monitor._handle_node_event("node_event", true_data)

    assert len(listener_calls) == 1
    assert listener_calls[0]["event_type"] == "ring"
    assert [event[0] for event in bus_events] == ["g410_doorbell_event", "aqara_g410_ring"]
    assert bus_events[0][1]["raw_data"] == {"occupancy": {"occupied": True}}


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


def test_monitor_ignores_repeated_true_without_new_false_transition() -> None:
    """Repeated occupied=true events should not create duplicate rings."""

    monitor, bus_events = _make_monitor()
    listener_calls: list[dict] = []
    monitor.async_add_ring_listener(listener_calls.append)

    false_data = SimpleNamespace(
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
    true_data = SimpleNamespace(
        node_id=3,
        endpoint_id=2,
        cluster_id=0x0406,
        data={"occupancy": {"occupied": True}},
        event_id=2,
        event_number=3,
        priority=3,
        timestamp=5,
        timestamp_type="system",
    )

    with patch(
        "custom_components.g410_doorbell_event.monitor.time.monotonic",
        return_value=111.0,
    ):
        monitor._handle_node_event("node_event", false_data)
        monitor._handle_node_event("node_event", true_data)
        monitor._handle_node_event("node_event", true_data)

    assert len(listener_calls) == 1
    assert len(bus_events) == 2
