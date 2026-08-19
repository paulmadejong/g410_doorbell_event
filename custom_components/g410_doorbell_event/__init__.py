"""G410 Doorbell Event integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .monitor import DoorbellMonitor

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["event"]


@dataclass(slots=True)
class RuntimeData:
    """Runtime state for the config entry."""

    monitor: DoorbellMonitor


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""

    del config
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""

    try:
        monitor = DoorbellMonitor(hass)
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady("Matter integration is not ready") from err

    try:
        await monitor.async_start()
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady("Failed to initialize doorbell monitor") from err

    hass.data[DOMAIN][entry.entry_id] = RuntimeData(monitor=monitor)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("Loaded G410 Doorbell Event integration for entry %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runtime is not None:
        await runtime.monitor.async_stop()
    return unload_ok
