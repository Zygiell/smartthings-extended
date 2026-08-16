"""Config flow for SmartThings Extended."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from . import DOMAIN


class SmartThingsExtendedConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the single SmartThings Extended config entry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="SmartThings Extended", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Import the existing configuration.yaml setup."""
        data = dict(user_input or {})
        existing = self._async_current_entries()
        if existing:
            self.hass.config_entries.async_update_entry(existing[0], data=data)
            return self.async_abort(reason="already_configured")

        return self.async_create_entry(title="SmartThings Extended", data=data)
