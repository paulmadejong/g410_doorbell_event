"""Matter node monitoring and auto-discovery logic."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from homeassistant.components.matter.helpers import get_matter
from homeassistant.core import HomeAssistant
from matter_server.common.models import EventType, MatterNodeEvent

from .const import (
    DOMAIN,
    ENTITY_RING,
    EVENT_DOORBELL,
    OCCUPANCY_SENSING_CLUSTER_ID,
)
from .discovery import (
    extract_occupied_flag,
    iter_candidates,
    resolve_candidate,
    summarize_candidate,
)
from .models import DoorbellListener, MonitorState

_LOGGER = logging.getLogger(__name__)


class DoorbellMonitor:
    """Manage Matter subscriptions and a single resolved endpoint."""

    hass: HomeAssistant
    matter_client: Any
    state: MonitorState

    def __init__(
        self,
        hass: HomeAssistant,
        preferred_node_id: int | None = None,
        preferred_endpoint_id: int | None = None,
    ) -> None:
        self.hass = hass
        self.matter_client = get_matter(hass).matter_client
        self.preferred_node_id = preferred_node_id
        self.preferred_endpoint_id = preferred_endpoint_id
        self.state = MonitorState()
        self._listeners: list[DoorbellListener] = []
        self._unsubscribers: list[Callable[[], None]] = []
        self._rescan_lock = asyncio.Lock()

    async def async_start(self) -> None:
        """Set up subscriptions and resolve the active endpoint."""

        self._unsubscribers.append(
            self.matter_client.subscribe_events(self._handle_node_event, EventType.NODE_EVENT)
        )
        for event_type in (
            EventType.NODE_ADDED,
            EventType.NODE_UPDATED,
            EventType.NODE_REMOVED,
            EventType.ENDPOINT_ADDED,
            EventType.ENDPOINT_REMOVED,
        ):
            self._unsubscribers.append(
                self.matter_client.subscribe_events(self._handle_topology_event, event_type)
            )

        await self.async_rescan("startup")

    async def async_stop(self) -> None:
        """Tear down all subscriptions."""

        while self._unsubscribers:
            unsubscribe = self._unsubscribers.pop()
            try:
                unsubscribe()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Failed to unsubscribe Matter listener")
        self._listeners.clear()

    def async_add_ring_listener(self, listener: DoorbellListener) -> Callable[[], None]:
        """Register a callback for ring events."""

        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    async def async_rescan(self, reason: str) -> None:
        """Re-evaluate the node inventory and pick an active endpoint if possible."""

        async with self._rescan_lock:
            candidates = iter_candidates(self.matter_client)
            status, candidate, ranked = resolve_candidate(
                candidates,
                preferred_node_id=self.preferred_node_id,
                preferred_endpoint_id=self.preferred_endpoint_id,
            )

            if status == "missing":
                self.state.candidate = None
                self.state.status = "missing"
                self.state.detail = (
                    "No available Matter node with Occupancy Sensing support was found."
                )
                _LOGGER.warning("%s", self.state.detail)
                return

            if status == "invalid_override":
                self.state.candidate = None
                self.state.status = "invalid_override"
                self.state.detail = (
                    "Configured node/endpoint override does not match any available "
                    "Occupancy Sensing endpoint."
                )
                _LOGGER.error(
                    "%s Candidates: %s",
                    self.state.detail,
                    "; ".join(summarize_candidate(item) for item in ranked),
                )
                return

            if status == "ambiguous" or candidate is None:
                self.state.candidate = None
                self.state.status = "ambiguous"
                self.state.detail = (
                    "Multiple Occupancy Sensing endpoints matched; "
                    "manual endpoint selection is required."
                )
                _LOGGER.error(
                    "%s Candidates: %s",
                    self.state.detail,
                    "; ".join(summarize_candidate(item) for item in ranked),
                )
                return

            previous = self.state.candidate
            self.state.candidate = candidate
            self.state.status = "ready"
            self.state.detail = summarize_candidate(candidate)

            if previous != candidate:
                _LOGGER.info(
                    "Resolved Aqara G410 Matter endpoint after %s: %s",
                    reason,
                    self.state.detail,
                )
            else:
                _LOGGER.debug(
                    "Aqara G410 Matter endpoint unchanged after %s: %s",
                    reason,
                    self.state.detail,
                )

    def _handle_topology_event(self, event: EventType, data: Any) -> None:
        """Rescan when the Matter topology changes."""

        del event, data
        self.hass.async_create_task(self.async_rescan("topology update"))

    def _handle_node_event(self, event: EventType, data: MatterNodeEvent) -> None:
        """Fire a Home Assistant event when the selected endpoint reports occupied=true."""

        del event
        candidate = self.state.candidate
        if candidate is None or self.state.status != "ready":
            return

        if data.node_id != candidate.node_id or data.endpoint_id != candidate.endpoint_id:
            return

        if data.cluster_id != OCCUPANCY_SENSING_CLUSTER_ID:
            return

        payload = data.data or {}
        if not extract_occupied_flag(payload):
            _LOGGER.debug(
                "Ignoring occupancy event without occupied=true for node=%s endpoint=%s payload=%s",
                data.node_id,
                data.endpoint_id,
                payload,
            )
            return

        _LOGGER.info(
            "Doorbell event detected on node=%s endpoint=%s event_id=%s event_number=%s",
            data.node_id,
            data.endpoint_id,
            getattr(data, "event_id", None),
            getattr(data, "event_number", None),
        )
        event_payload = {
            "domain": DOMAIN,
            "node_id": data.node_id,
            "endpoint_id": data.endpoint_id,
            "cluster_id": data.cluster_id,
            "event_id": getattr(data, "event_id", None),
            "event_number": getattr(data, "event_number", None),
            "priority": getattr(data, "priority", None),
            "timestamp": getattr(data, "timestamp", None),
            "timestamp_type": getattr(data, "timestamp_type", None),
            "occupied": True,
            "event_type": ENTITY_RING,
            "raw_data": payload,
        }

        for listener in tuple(self._listeners):
            try:
                listener(event_payload)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Ring listener callback failed")

        self.hass.bus.async_fire(EVENT_DOORBELL, event_payload)
