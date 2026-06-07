"""Config flow for ai_web_scraper."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.loader import async_get_loaded_integration
from slugify import slugify

from .const import (
    CONF_API_KEY,
    CONF_BROWSERLESS_URL,
    CONF_ENTRY_TYPE,
    CONF_EXTRACTION_MODE,
    CONF_INTERVAL_SECONDS,
    CONF_PROMPT,
    CONF_PROVIDER_ID,
    CONF_PROVIDER_NAME,
    CONF_SCRAPER_NAME,
    CONF_URL,
    DOMAIN,
    ENTRY_TYPE_PROVIDER,
    ENTRY_TYPE_SCRAPER,
    EXTRACTION_MODES,
)
from .data import get_provider_entries


class AIWebScraperConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ai_web_scraper."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step of the config flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entry_type = user_input.get(CONF_ENTRY_TYPE)
            if entry_type == ENTRY_TYPE_PROVIDER:
                return await self.async_step_provider()
            if entry_type == ENTRY_TYPE_SCRAPER:
                return await self.async_step_scraper()

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (
            "Integration documentation URL is not set in manifest.json"
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENTRY_TYPE,
                    default=(user_input or {}).get(CONF_ENTRY_TYPE, vol.UNDEFINED),
                ): vol.In(
                    {
                        ENTRY_TYPE_PROVIDER: "Add AI Provider",
                        ENTRY_TYPE_SCRAPER: "Add Scraper Entry",
                    }
                )
            }
        )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation,
            },
            data_schema=schema,
            errors=errors,
        )

    def _provider_entries(self) -> list[config_entries.ConfigEntry]:
        return get_provider_entries(self.hass)

    def _provider_options(self) -> dict[str, str]:
        return {entry.entry_id: entry.title for entry in self._provider_entries()}

    def _provider_schema(
        self,
        user_input: dict | None = None,
    ) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_PROVIDER_NAME,
                    default=(user_input or {}).get(CONF_PROVIDER_NAME, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(
                    CONF_API_KEY,
                    default=(user_input or {}).get(CONF_API_KEY, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(
                    CONF_MODEL_NAME,
                    default=(user_input or {}).get(CONF_MODEL_NAME, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(
                    CONF_BROWSERLESS_URL,
                    default=(user_input or {}).get(CONF_BROWSERLESS_URL, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                ),
            }
        )

    def _scraper_schema(
        self,
        user_input: dict | None = None,
    ) -> vol.Schema:
        provider_options = self._provider_options()

        schema_dict: dict[vol.Required, object] = {
            vol.Required(
                CONF_SCRAPER_NAME,
                default=(user_input or {}).get(CONF_SCRAPER_NAME, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_URL,
                default=(user_input or {}).get(CONF_URL, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            vol.Required(
                CONF_PROMPT,
                default=(user_input or {}).get(CONF_PROMPT, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_EXTRACTION_MODE,
                default=(user_input or {}).get(CONF_EXTRACTION_MODE, vol.UNDEFINED),
            ): vol.In(EXTRACTION_MODES),
            vol.Required(
                CONF_INTERVAL_SECONDS,
                default=(user_input or {}).get(CONF_INTERVAL_SECONDS, 60),
            ): vol.All(vol.Coerce(int), vol.Range(min=0)),
        }

        if provider_options:
            schema_dict[vol.Required(
                CONF_PROVIDER_ID,
                default=(user_input or {}).get(CONF_PROVIDER_ID, vol.UNDEFINED),
            )] = vol.In(provider_options)

        return vol.Schema(schema_dict)

    async def async_step_provider(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle AI Provider profile creation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            missing = [
                field
                for field in [CONF_PROVIDER_NAME, CONF_API_KEY, CONF_MODEL_NAME]
                if not user_input.get(field)
            ]
            if missing:
                for field in missing:
                    errors[field] = "required"
            else:
                await self.async_set_unique_id(slugify(user_input[CONF_PROVIDER_NAME]))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_PROVIDER_NAME],
                    data={
                        CONF_ENTRY_TYPE: ENTRY_TYPE_PROVIDER,
                        CONF_PROVIDER_NAME: user_input[CONF_PROVIDER_NAME],
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_MODEL_NAME: user_input[CONF_MODEL_NAME],
                        CONF_BROWSERLESS_URL: user_input.get(CONF_BROWSERLESS_URL, ""),
                    },
                )

        return self.async_show_form(
            step_id="provider",
            data_schema=self._provider_schema(user_input),
            errors=errors,
        )

    async def async_step_scraper(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle Scraper entry creation."""
        errors: dict[str, str] = {}
        provider_options = self._provider_options()

        if not provider_options:
            errors["base"] = "no_providers"

        if user_input is not None:
            if not provider_options:
                errors["base"] = "no_providers"
            if provider_options and not user_input.get(CONF_PROVIDER_ID):
                errors[CONF_PROVIDER_ID] = "required"
            if not user_input.get(CONF_SCRAPER_NAME):
                errors[CONF_SCRAPER_NAME] = "required"
            if not user_input.get(CONF_URL):
                errors[CONF_URL] = "required"
            if not user_input.get(CONF_PROMPT):
                errors[CONF_PROMPT] = "required"
            if not errors:
                await self.async_set_unique_id(
                    slugify(
                        f"{user_input[CONF_SCRAPER_NAME]}-{user_input.get(CONF_PROVIDER_ID, '')}"
                    )
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_SCRAPER_NAME],
                    data={
                        CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
                        CONF_SCRAPER_NAME: user_input[CONF_SCRAPER_NAME],
                        CONF_PROVIDER_ID: user_input[CONF_PROVIDER_ID],
                        CONF_URL: user_input[CONF_URL],
                        CONF_PROMPT: user_input[CONF_PROMPT],
                        CONF_EXTRACTION_MODE: user_input[CONF_EXTRACTION_MODE],
                        CONF_INTERVAL_SECONDS: user_input[CONF_INTERVAL_SECONDS],
                    },
                )

        return self.async_show_form(
            step_id="scraper",
            data_schema=self._scraper_schema(user_input),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return AIWebScraperOptionsFlowHandler(config_entry)


class AIWebScraperOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for ai_web_scraper."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        entry_type = self.config_entry.data.get(CONF_ENTRY_TYPE)
        if entry_type == ENTRY_TYPE_PROVIDER:
            return await self.async_step_provider(user_input)
        return await self.async_step_scraper(user_input)

    async def async_step_provider(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            missing = [
                field
                for field in [CONF_PROVIDER_NAME, CONF_API_KEY, CONF_MODEL_NAME]
                if not user_input.get(field)
            ]
            if missing:
                for field in missing:
                    errors[field] = "required"
            else:
                self.config_entry.async_update_entry(
                    data={
                        **self.config_entry.data,
                        CONF_PROVIDER_NAME: user_input[CONF_PROVIDER_NAME],
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_MODEL_NAME: user_input[CONF_MODEL_NAME],
                        CONF_BROWSERLESS_URL: user_input.get(CONF_BROWSERLESS_URL, ""),
                    }
                )
                return self.async_create_entry(title="done", data={})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PROVIDER_NAME,
                    default=self.config_entry.data.get(CONF_PROVIDER_NAME, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(
                    CONF_API_KEY,
                    default=self.config_entry.data.get(CONF_API_KEY, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(
                    CONF_MODEL_NAME,
                    default=self.config_entry.data.get(CONF_MODEL_NAME, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional(
                    CONF_BROWSERLESS_URL,
                    default=self.config_entry.data.get(CONF_BROWSERLESS_URL, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                ),
            }
        )

        return self.async_show_form(
            step_id="provider",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_scraper(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        provider_options = {
            entry.entry_id: entry.title
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_PROVIDER
        }

        if not provider_options:
            errors["base"] = "no_providers"

        if user_input is not None:
            if not provider_options:
                errors["base"] = "no_providers"
            if provider_options and not user_input.get(CONF_PROVIDER_ID):
                errors[CONF_PROVIDER_ID] = "required"
            if not user_input.get(CONF_SCRAPER_NAME):
                errors[CONF_SCRAPER_NAME] = "required"
            if not user_input.get(CONF_URL):
                errors[CONF_URL] = "required"
            if not user_input.get(CONF_PROMPT):
                errors[CONF_PROMPT] = "required"
            if not errors:
                self.config_entry.async_update_entry(
                    data={
                        **self.config_entry.data,
                        CONF_SCRAPER_NAME: user_input[CONF_SCRAPER_NAME],
                        CONF_PROVIDER_ID: user_input[CONF_PROVIDER_ID],
                        CONF_URL: user_input[CONF_URL],
                        CONF_PROMPT: user_input[CONF_PROMPT],
                        CONF_EXTRACTION_MODE: user_input[CONF_EXTRACTION_MODE],
                        CONF_INTERVAL_SECONDS: user_input[CONF_INTERVAL_SECONDS],
                    }
                )
                return self.async_create_entry(title="done", data={})

        schema_dict: dict[vol.Required, object] = {
            vol.Required(
                CONF_SCRAPER_NAME,
                default=self.config_entry.data.get(CONF_SCRAPER_NAME, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_URL,
                default=self.config_entry.data.get(CONF_URL, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            vol.Required(
                CONF_PROMPT,
                default=self.config_entry.data.get(CONF_PROMPT, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_EXTRACTION_MODE,
                default=self.config_entry.data.get(CONF_EXTRACTION_MODE, vol.UNDEFINED),
            ): vol.In(EXTRACTION_MODES),
            vol.Required(
                CONF_INTERVAL_SECONDS,
                default=self.config_entry.data.get(CONF_INTERVAL_SECONDS, 60),
            ): vol.All(vol.Coerce(int), vol.Range(min=0)),
        }

        if provider_options:
            schema_dict[vol.Required(
                CONF_PROVIDER_ID,
                default=self.config_entry.data.get(CONF_PROVIDER_ID, vol.UNDEFINED),
            )] = vol.In(provider_options)

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="scraper",
            data_schema=schema,
            errors=errors,
        )
