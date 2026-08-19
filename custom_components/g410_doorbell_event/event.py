"""Doorbell event entity for the G410 integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.event import (
    DoorbellEventType,
    EventDeviceClass,
    EventEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NAME

try:
    from homeassistant.components.matter.helpers import get_node_device_identifier
except ImportError:  # pragma: no cover - depends on HA version
    get_node_device_identifier = None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the event entity for a config entry."""

    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([G410DoorbellRingEventEntity(runtime.monitor)])


class G410DoorbellRingEventEntity(EventEntity):
    """Event entity that exposes the standard ring event."""

    _attr_name = NAME
    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.DOORBELL
    _attr_event_types = [DoorbellEventType.RING]
    _attr_translation_key = "ring"
    _attr_unique_id = f"{DOMAIN}_ring"

    def __init__(self, monitor: Any) -> None:
        self._monitor = monitor
        self._remove_listener: Callable[[], None] | None = None
        self._attr_device_info = self._build_device_info()

    def _build_device_info(self) -> DeviceInfo:
        """Link this entity to the resolved Matter device when possible."""

        candidate = self._monitor.state.candidate
        server_info = getattr(self._monitor.matter_client, "server_info", None)

        if (
            candidate is not None
            and server_info is not None
            and get_node_device_identifier is not None
        ):
            return DeviceInfo(
                identifiers={get_node_device_identifier(server_info, candidate.node_id)}
            )

        return DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            manufacturer="Aqara",
            model="G410",
            name="Aqara G410 ring",
        )

    async def async_added_to_hass(self) -> None:
        """Register ring callbacks."""

        self._remove_listener = self._monitor.async_add_ring_listener(self._handle_ring_event)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister ring callbacks."""

        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    @callback
    def _handle_ring_event(self, event_data: dict[str, Any]) -> None:
        """Handle a ring event from the monitor."""

        self._trigger_event(DoorbellEventType.RING, event_data)
        self.async_write_ha_state()
