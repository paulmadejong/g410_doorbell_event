"""Test stubs for importing the custom integration without Home Assistant."""

from __future__ import annotations

import sys
from types import ModuleType


def _ensure_module(name: str) -> ModuleType:
    """Create a module placeholder if it does not exist yet."""

    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        sys.modules[name] = module
    return module


homeassistant = _ensure_module("homeassistant")
config_entries = _ensure_module("homeassistant.config_entries")
components = _ensure_module("homeassistant.components")
event = _ensure_module("homeassistant.components.event")
matter = _ensure_module("homeassistant.components.matter")
matter_helpers = _ensure_module("homeassistant.components.matter.helpers")
core = _ensure_module("homeassistant.core")
data_entry_flow = _ensure_module("homeassistant.data_entry_flow")
exceptions = _ensure_module("homeassistant.exceptions")
helpers = _ensure_module("homeassistant.helpers")
helpers_config_validation = _ensure_module("homeassistant.helpers.config_validation")
helpers_entity = _ensure_module("homeassistant.helpers.entity")
helpers_entity_platform = _ensure_module("homeassistant.helpers.entity_platform")
ha_const = _ensure_module("homeassistant.const")
chip = _ensure_module("chip")
chip_clusters = _ensure_module("chip.clusters")
matter_server = _ensure_module("matter_server")
matter_server_common = _ensure_module("matter_server.common")
matter_server_models = _ensure_module("matter_server.common.models")

homeassistant.config_entries = config_entries
homeassistant.components = components
homeassistant.core = core
homeassistant.data_entry_flow = data_entry_flow
homeassistant.exceptions = exceptions
components.matter = matter
components.event = event
matter.helpers = matter_helpers
homeassistant.helpers = helpers
helpers.config_validation = helpers_config_validation
helpers.entity = helpers_entity
helpers.entity_platform = helpers_entity_platform
homeassistant.const = ha_const
chip.clusters = chip_clusters
matter_server.common = matter_server_common
matter_server_common.models = matter_server_models


class ConfigEntry:  # noqa: D101
    pass


class ConfigFlow:  # noqa: D101
    def __init_subclass__(cls, **kwargs):
        return super().__init_subclass__()


class OptionsFlow:  # noqa: D101
    @property
    def config_entry(self):
        return None


class HomeAssistant:  # noqa: D101
    pass


class ConfigEntryNotReady(Exception):  # noqa: D101
    pass


class EventEntity:  # noqa: D101
    def _trigger_event(self, *_args, **_kwargs) -> None:
        pass

    def async_write_ha_state(self) -> None:
        pass


class DeviceInfo(dict):  # noqa: D101
    pass


class AddEntitiesCallback:  # noqa: D101
    pass


class DoorbellEventType:  # noqa: D101
    RING = "ring"


class EventDeviceClass:  # noqa: D101
    DOORBELL = "doorbell"


config_entries.ConfigEntry = ConfigEntry
config_entries.ConfigFlow = ConfigFlow
config_entries.OptionsFlow = OptionsFlow
core.HomeAssistant = HomeAssistant
core.callback = lambda func: func
data_entry_flow.FlowResult = dict
exceptions.ConfigEntryNotReady = ConfigEntryNotReady
event.EventEntity = EventEntity
event.DoorbellEventType = DoorbellEventType
event.EventDeviceClass = EventDeviceClass
helpers_entity.DeviceInfo = DeviceInfo
helpers_entity_platform.AddEntitiesCallback = AddEntitiesCallback
helpers_config_validation.config_entry_only_config_schema = lambda _domain: object()


def get_matter(_: HomeAssistant):  # noqa: D401
    """Return a stub Matter runtime."""

    class StubMatterRuntime:
        matter_client = None

    return StubMatterRuntime()


def get_node_device_identifier(server_info, node_id: int):  # noqa: D401
    """Return a stub Matter device identifier."""

    return (
        "matter",
        f"deviceid_{server_info.compressed_fabric_id:016X}-{node_id:016X}-MatterNodeDevice",
    )


class EventType:  # noqa: D101
    NODE_EVENT = "node_event"
    NODE_ADDED = "node_added"
    NODE_UPDATED = "node_updated"
    NODE_REMOVED = "node_removed"
    ENDPOINT_ADDED = "endpoint_added"
    ENDPOINT_REMOVED = "endpoint_removed"


class MatterNodeEvent:  # noqa: D101
    pass


class _OccupancySensing:  # noqa: D101
    pass


class _ClusterObjects:  # noqa: D101
    OccupancySensing = _OccupancySensing


matter_helpers.get_matter = get_matter
matter_helpers.get_node_device_identifier = get_node_device_identifier
matter_server_models.EventType = EventType
matter_server_models.MatterNodeEvent = MatterNodeEvent
chip_clusters.Objects = _ClusterObjects
