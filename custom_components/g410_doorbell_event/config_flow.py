"""Config flow for the G410 Ring Event integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.matter.helpers import get_matter
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ENDPOINT_ID, CONF_NODE_ID, DOMAIN, NAME
from .discovery import iter_candidates, rank_candidates, resolve_candidate, summarize_candidate
from .models import DoorbellCandidate

_LOGGER = logging.getLogger(__name__)
CONF_CANDIDATE = "candidate"


class G410DoorbellEventConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """A zero-input config flow that validates the selected Matter endpoint."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler."""

        return G410DoorbellEventOptionsFlow(config_entry)

    def __init__(self) -> None:
        self._candidates: list[DoorbellCandidate] = []

    @staticmethod
    def _candidate_value(candidate: DoorbellCandidate) -> str:
        """Serialize a candidate for a select field."""

        return f"{candidate.node_id}:{candidate.endpoint_id}"

    @classmethod
    def _candidate_options(cls, candidates: list[DoorbellCandidate]) -> dict[str, str]:
        """Build human-readable select options for candidate choice."""

        return {
            cls._candidate_value(candidate): summarize_candidate(candidate)
            for candidate in candidates
        }

    @staticmethod
    def _has_ambiguity(candidates: list[DoorbellCandidate]) -> bool:
        """Return True when multiple top-ranked candidates remain."""

        if len(candidates) < 2:
            return False
        return candidates[0].score == candidates[1].score

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
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

        self._candidates = rank_candidates(candidates)
        status, candidate, ranked = resolve_candidate(candidates)
        if self._has_ambiguity(self._candidates):
            _LOGGER.warning(
                "Ambiguous Matter candidates during config flow: %s",
                "; ".join(summarize_candidate(item) for item in self._candidates),
            )
            return await self.async_step_manual()

        if status != "ready" or candidate is None:
            _LOGGER.error(
                "Could not resolve Matter candidate during config flow: %s",
                "; ".join(summarize_candidate(item) for item in ranked),
            )
            return await self.async_step_manual()

        _LOGGER.info(
            "Creating G410 Ring Event entry for node=%s endpoint=%s",
            candidate.node_id,
            candidate.endpoint_id,
        )
        return self.async_create_entry(
            title=NAME,
            data={
                CONF_NODE_ID: candidate.node_id,
                CONF_ENDPOINT_ID: candidate.endpoint_id,
            },
        )

    async def async_step_manual(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Allow candidate selection when auto-detection is ambiguous."""

        errors: dict[str, str] = {}

        if user_input is not None:
            selected_value = user_input[CONF_CANDIDATE]
            selected_candidate = next(
                (
                    candidate
                    for candidate in self._candidates
                    if self._candidate_value(candidate) == selected_value
                ),
                None,
            )
            if selected_candidate is None:
                errors["base"] = "invalid_candidate"
            else:
                status, candidate, _ = resolve_candidate(
                    self._candidates,
                    preferred_node_id=selected_candidate.node_id,
                    preferred_endpoint_id=selected_candidate.endpoint_id,
                )
                if status == "ready" and candidate is not None:
                    await self.async_set_unique_id(DOMAIN)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=NAME,
                        data={
                            CONF_NODE_ID: candidate.node_id,
                            CONF_ENDPOINT_ID: candidate.endpoint_id,
                        },
                    )
                errors["base"] = "invalid_candidate"

        suggested = self._candidates[0]
        options = self._candidate_options(self._candidates)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CANDIDATE,
                    default=self._candidate_value(suggested),
                ): vol.In(options),
            }
        )
        candidate_list = " | ".join(summarize_candidate(item) for item in self._candidates)
        return self.async_show_form(
            step_id="manual",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "candidates": candidate_list,
                "suggested_node_id": str(suggested.node_id),
                "suggested_endpoint_id": str(suggested.endpoint_id),
            },
        )


class G410DoorbellEventOptionsFlow(config_entries.OptionsFlow):
    """Allow changing the preferred Matter node/endpoint after setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._candidates: list[DoorbellCandidate] = []

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage integration options."""

        errors: dict[str, str] = {}

        try:
            matter = get_matter(self.hass)
            self._candidates = rank_candidates(iter_candidates(matter.matter_client))
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Matter integration is not ready during options flow: %s", err)
            self._candidates = []

        current_node_id = self._config_entry.options.get(
            CONF_NODE_ID,
            self._config_entry.data.get(CONF_NODE_ID),
        )
        current_endpoint_id = self._config_entry.options.get(
            CONF_ENDPOINT_ID,
            self._config_entry.data.get(CONF_ENDPOINT_ID),
        )

        if user_input is not None:
            if self._candidates:
                status, candidate, _ = resolve_candidate(
                    self._candidates,
                    preferred_node_id=user_input[CONF_NODE_ID],
                    preferred_endpoint_id=user_input[CONF_ENDPOINT_ID],
                )
                if status != "ready" or candidate is None:
                    errors["base"] = "invalid_override"
                else:
                    return self.async_create_entry(
                        title="",
                        data={
                            CONF_NODE_ID: candidate.node_id,
                            CONF_ENDPOINT_ID: candidate.endpoint_id,
                        },
                    )
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_NODE_ID: user_input[CONF_NODE_ID],
                        CONF_ENDPOINT_ID: user_input[CONF_ENDPOINT_ID],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NODE_ID, default=current_node_id): vol.Coerce(int),
                vol.Required(CONF_ENDPOINT_ID, default=current_endpoint_id): vol.Coerce(int),
            }
        )

        candidate_list = (
            " | ".join(summarize_candidate(item) for item in self._candidates)
            if self._candidates
            else "No current candidates detected."
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"candidates": candidate_list},
        )
