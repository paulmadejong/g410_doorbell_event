"""Config flow regression tests."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.modules.setdefault("voluptuous", MagicMock())

from custom_components.g410_doorbell_event.config_flow import G410DoorbellEventOptionsFlow


def test_options_flow_accepts_config_entry_without_setting_base_property() -> None:
    """Options flow should not assign to the read-only base config_entry property."""

    entry = SimpleNamespace(options={"node_id": 3}, data={"endpoint_id": 2})

    flow = G410DoorbellEventOptionsFlow(entry)

    assert flow._config_entry is entry
