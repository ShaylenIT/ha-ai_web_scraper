"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from .const import CONF_PROVIDER, CONF_API_KEY, CONF_BASE_URL, PROVIDERS
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.loader import async_get_loaded_integration
from slugify import slugify

from .api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
)
from .const import DOMAIN, LOGGER


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            provider = user_input.get(CONF_PROVIDER)
            provider_fields = PROVIDERS.get(provider, {}).get("fields", [])
            # Validate required fields
            missing = [f for f in provider_fields if not user_input.get(f)]
            if not provider:
                _errors[CONF_PROVIDER] = "required"
            elif missing:
                for f in missing:
                    _errors[f] = "required"
            else:
                # Here you would test credentials if needed
                await self.async_set_unique_id(slugify(provider + "-" + (user_input.get(CONF_API_KEY) or user_input.get(CONF_BASE_URL) or "")))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=PROVIDERS[provider]["name"],
                    data=user_input,
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (
            "Integration documentation URL is not set in manifest.json"
        )

        # Provider selection
        provider_options = [(k, v["name"]) for k, v in PROVIDERS.items()]
        schema_dict = {
            vol.Required(CONF_PROVIDER, default=(user_input or {}).get(CONF_PROVIDER, vol.UNDEFINED)):
                vol.In({k: v for k, v in provider_options}),
        }
        provider = (user_input or {}).get(CONF_PROVIDER)
        if provider:
            fields = PROVIDERS[provider]["fields"]
            if "api_key" in fields:
                schema_dict[vol.Required(CONF_API_KEY, default=(user_input or {}).get(CONF_API_KEY, vol.UNDEFINED))] = selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                )
            if "base_url" in fields:
                schema_dict[vol.Required(CONF_BASE_URL, default=(user_input or {}).get(CONF_BASE_URL, vol.UNDEFINED))] = selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation,
            },
            data_schema=vol.Schema(schema_dict),
            errors=_errors,
        )

    async def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        client = IntegrationBlueprintApiClient(
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
        )
        await client.async_get_data()
