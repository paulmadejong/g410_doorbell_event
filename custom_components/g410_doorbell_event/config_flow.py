"""Config flow for the G410 Doorbell Event integration."""

from __future__ import annotations

import logging

from homeassistant import config_entries
from homeassistant.components.matter.helpers import get_matter
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, NAME
from .discovery import iter_candidates

_LOGGER = logging.getLogger(__name__)


class G410DoorbellEventConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """A zero-input config flow that validates the selected Matter endpoint."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Create the entry after validating the Matter inventory."""

        del user_input

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        try:
            matter = get_matter(self.hass)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Matter integration is not ready yet: %s", err)
            return self.async_abort(reason="matter_not_ready")

        candidates = iter_candidates(matter.matter_client)
        if not candidates:
            return self.async_abort(reason="no_candidates")

        candidates.sort(key=lambda item: (item.score, item.node_id, item.endpoint_id), reverse=True)
        best_score = candidates[0].score
        best_candidates = [item for item in candidates if item.score == best_score]
        if len(best_candidates) != 1:
            _LOGGER.error(
                "Ambiguous Matter candidates during config flow: %s",
                "; ".join(
                    f"node={item.node_id} endpoint={item.endpoint_id} score={item.score}"
                    for item in candidates
                ),
            )
            return self.async_abort(reason="ambiguous_candidates")

        candidate = best_candidates[0]
        _LOGGER.info(
            "Creating G410 Doorbell Event entry for node=%s endpoint=%s",
            candidate.node_id,
            candidate.endpoint_id,
        )
        return self.async_create_entry(title=NAME, data={})
