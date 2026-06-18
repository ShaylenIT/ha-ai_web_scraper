"""Config flow for ai_web_scraper."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.loader import async_get_loaded_integration
from slugify import slugify

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_BROWSERLESS_URL,
    CONF_COOL_DOWN_SECONDS,
    CONF_ENTRY_TYPE,
    CONF_EXTRACTION_MODE,
    CONF_INTERVAL_SECONDS,
    CONF_MODEL_NAME,
    CONF_PROMPT,
    CONF_PROVIDER_ID,
    CONF_PROVIDER_NAME,
    CONF_PROVIDER_TYPE,
    CONF_REQUEST_TIMEOUT,
    CONF_SCRAPER_NAME,
    CONF_URL,
    DOMAIN,
    ENTRY_TYPE_PROVIDER,
    ENTRY_TYPE_SCRAPER,
    EXTRACTION_MODES,
    LOGGER,
    OPENAI_COMPATIBLE_TYPES,
    PROVIDER_BASE_URLS,
    PROVIDER_TYPE_GEMINI,
    PROVIDER_TYPE_OPENAI,
    PROVIDER_TYPES,
)
from .data import get_provider_entries


def _provider_details_schema(
    provider_type: str,
    user_input: dict | None = None,
) -> vol.Schema:
    """
    Build a conditional schema based on the selected provider brand.

    Standalone function so both the config flow and options flow can use it.
    """
    schema_dict: dict[vol.Required | vol.Optional, object] = {
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
            CONF_COOL_DOWN_SECONDS,
            default=(user_input or {}).get(CONF_COOL_DOWN_SECONDS, 30),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                min=0,
                max=3600,
                unit_of_measurement="seconds",
            )
        ),
        vol.Optional(
            CONF_REQUEST_TIMEOUT,
            default=(user_input or {}).get(CONF_REQUEST_TIMEOUT, 60),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                min=10,
                max=300,
                unit_of_measurement="seconds",
            )
        ),
    }

    # OpenAI-compatible providers: show base URL (pre-filled for known brands)
    if provider_type in OPENAI_COMPATIBLE_TYPES:
        default_url = PROVIDER_BASE_URLS.get(provider_type, "")
        schema_dict[
            vol.Optional(
                CONF_BASE_URL,
                default=(user_input or {}).get(
                    CONF_BASE_URL, default_url or vol.UNDEFINED
                ),
            )
        ] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        )
        # Browserless URL is available for all compatible providers
        schema_dict[
            vol.Optional(
                CONF_BROWSERLESS_URL,
                default=(user_input or {}).get(CONF_BROWSERLESS_URL, vol.UNDEFINED),
            )
        ] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        )

    # Gemini: show browserless URL but no base URL
    if provider_type == PROVIDER_TYPE_GEMINI:
        schema_dict[
            vol.Optional(
                CONF_BROWSERLESS_URL,
                default=(user_input or {}).get(CONF_BROWSERLESS_URL, vol.UNDEFINED),
            )
        ] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        )

    return vol.Schema(schema_dict)


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
        documentation_url = integration.documentation if integration is not None else ""

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
                "documentation_url": documentation_url,
            },
            data_schema=schema,
            errors=errors,
        )

    def _provider_entries(self) -> list[config_entries.ConfigEntry]:
        return get_provider_entries(self.hass)

    def _provider_options(self) -> dict[str, str]:
        return {entry.entry_id: entry.title for entry in self._provider_entries()}

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
        }

        if provider_options:
            schema_dict[
                vol.Required(
                    CONF_PROVIDER_ID,
                    default=(user_input or {}).get(CONF_PROVIDER_ID, vol.UNDEFINED),
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=entry_id, label=label
                        )
                        for entry_id, label in provider_options.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return vol.Schema(schema_dict)

    async def async_step_provider(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Select the AI provider brand."""
        errors: dict[str, str] = {}

        if user_input is not None:
            provider_type = user_input.get(CONF_PROVIDER_TYPE)
            if provider_type in PROVIDER_TYPES:
                # Store the selected provider type for the next step
                self._selected_provider_type = provider_type
                return await self.async_step_provider_details()

            errors[CONF_PROVIDER_TYPE] = "required"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PROVIDER_TYPE,
                    default=(user_input or {}).get(CONF_PROVIDER_TYPE, vol.UNDEFINED),
                ): vol.In(PROVIDER_TYPES),
            }
        )

        return self.async_show_form(
            step_id="provider",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "provider_types": ", ".join(PROVIDER_TYPES.values()),
            },
        )

    async def async_step_provider_details(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Configure provider-specific fields."""
        errors: dict[str, str] = {}
        provider_type = getattr(self, "_selected_provider_type", PROVIDER_TYPE_OPENAI)

        if user_input is not None:
            missing = [
                field
                for field in [
                    CONF_PROVIDER_NAME,
                    CONF_API_KEY,
                    CONF_MODEL_NAME,
                ]
                if not user_input.get(field)
            ]
            if missing:
                for field in missing:
                    errors[field] = "required"
            else:
                await self.async_set_unique_id(slugify(user_input[CONF_PROVIDER_NAME]))
                self._abort_if_unique_id_configured()
                data = {
                    CONF_ENTRY_TYPE: ENTRY_TYPE_PROVIDER,
                    CONF_PROVIDER_NAME: user_input[CONF_PROVIDER_NAME],
                    CONF_PROVIDER_TYPE: provider_type,
                    CONF_API_KEY: user_input[CONF_API_KEY],
                    CONF_MODEL_NAME: user_input[CONF_MODEL_NAME],
                    CONF_COOL_DOWN_SECONDS: user_input.get(CONF_COOL_DOWN_SECONDS, 30),
                    CONF_REQUEST_TIMEOUT: user_input.get(CONF_REQUEST_TIMEOUT, 60),
                }
                if provider_type in OPENAI_COMPATIBLE_TYPES:
                    data[CONF_BASE_URL] = user_input.get(CONF_BASE_URL, "")
                    data[CONF_BROWSERLESS_URL] = user_input.get(
                        CONF_BROWSERLESS_URL, ""
                    )
                if provider_type == PROVIDER_TYPE_GEMINI:
                    data[CONF_BROWSERLESS_URL] = user_input.get(
                        CONF_BROWSERLESS_URL, ""
                    )
                return self.async_create_entry(
                    title=user_input[CONF_PROVIDER_NAME],
                    data=data,
                )

        return self.async_show_form(
            step_id="provider_details",
            data_schema=_provider_details_schema(provider_type, user_input),
            errors=errors,
            description_placeholders={
                "provider_brand": PROVIDER_TYPES.get(provider_type, provider_type),
            },
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
                scraper_id = (
                    f"{user_input[CONF_SCRAPER_NAME]}-"
                    f"{user_input.get(CONF_PROVIDER_ID, '')}"
                )
                await self.async_set_unique_id(slugify(scraper_id))
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
                        CONF_INTERVAL_SECONDS: 0,
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
        """Return an options flow for the given config entry."""
        return AIWebScraperOptionsFlowHandler(config_entry)


class AIWebScraperOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for ai_web_scraper."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry
        self._selected_provider_type = config_entry.data.get(
            CONF_PROVIDER_TYPE, PROVIDER_TYPE_OPENAI
        )

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle the initial step of the options flow."""
        entry_type = self._config_entry.data.get(CONF_ENTRY_TYPE)
        if entry_type == ENTRY_TYPE_PROVIDER:
            return await self.async_step_provider(user_input)
        return await self.async_step_scraper(user_input)

    async def async_step_provider(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Step 1: Select the AI provider brand (reconfigure)."""
        errors: dict[str, str] = {}
        current_type = self._config_entry.data.get(
            CONF_PROVIDER_TYPE, PROVIDER_TYPE_OPENAI
        )

        if user_input is not None:
            provider_type = user_input.get(CONF_PROVIDER_TYPE, current_type)
            if provider_type in PROVIDER_TYPES:
                self._selected_provider_type = provider_type
                return await self.async_step_provider_details()

            errors[CONF_PROVIDER_TYPE] = "required"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PROVIDER_TYPE,
                    default=current_type,
                ): vol.In(PROVIDER_TYPES),
            }
        )

        return self.async_show_form(
            step_id="provider",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_provider_details(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Step 2: Configure provider-specific fields (reconfigure)."""
        errors: dict[str, str] = {}
        provider_type = self._selected_provider_type
        current_data = self._config_entry.data

        if user_input is not None:
            try:
                missing = [
                    field
                    for field in [
                        CONF_PROVIDER_NAME,
                        CONF_API_KEY,
                        CONF_MODEL_NAME,
                    ]
                    if not user_input.get(field)
                ]
                if missing:
                    for field in missing:
                        errors[field] = "required"
                else:
                    updated_data = {
                        **current_data,
                        CONF_PROVIDER_NAME: user_input[CONF_PROVIDER_NAME],
                        CONF_PROVIDER_TYPE: provider_type,
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_MODEL_NAME: user_input[CONF_MODEL_NAME],
                        CONF_COOL_DOWN_SECONDS: user_input.get(
                            CONF_COOL_DOWN_SECONDS, 30
                        ),
                        CONF_REQUEST_TIMEOUT: user_input.get(CONF_REQUEST_TIMEOUT, 60),
                    }
                    if provider_type in OPENAI_COMPATIBLE_TYPES:
                        updated_data[CONF_BASE_URL] = user_input.get(
                            CONF_BASE_URL,
                            current_data.get(CONF_BASE_URL, ""),
                        )
                        updated_data[CONF_BROWSERLESS_URL] = user_input.get(
                            CONF_BROWSERLESS_URL,
                            current_data.get(CONF_BROWSERLESS_URL, ""),
                        )
                    if provider_type == PROVIDER_TYPE_GEMINI:
                        updated_data[CONF_BROWSERLESS_URL] = user_input.get(
                            CONF_BROWSERLESS_URL,
                            current_data.get(CONF_BROWSERLESS_URL, ""),
                        )
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data=updated_data,
                    )
                    return self.async_create_entry(title="done", data={})
            except Exception:  # pylint: disable=broad-except  # noqa: BLE001
                LOGGER.exception(
                    "Unexpected error updating provider options for %s",
                    self._config_entry.entry_id,
                )
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="provider_details",
            data_schema=_provider_details_schema(
                provider_type,
                {
                    CONF_PROVIDER_NAME: current_data.get(CONF_PROVIDER_NAME, ""),
                    CONF_API_KEY: current_data.get(CONF_API_KEY, ""),
                    CONF_MODEL_NAME: current_data.get(CONF_MODEL_NAME, ""),
                    CONF_BASE_URL: current_data.get(CONF_BASE_URL, ""),
                    CONF_BROWSERLESS_URL: current_data.get(CONF_BROWSERLESS_URL, ""),
                    CONF_COOL_DOWN_SECONDS: current_data.get(
                        CONF_COOL_DOWN_SECONDS, 30
                    ),
                    CONF_REQUEST_TIMEOUT: current_data.get(CONF_REQUEST_TIMEOUT, 60),
                },
            ),
            errors=errors,
            description_placeholders={
                "provider_brand": PROVIDER_TYPES.get(provider_type, provider_type),
            },
        )

    async def async_step_scraper(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle scraper reconfiguration."""
        errors: dict[str, str] = {}
        provider_options = {
            entry.entry_id: entry.title
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_PROVIDER
        }

        if not provider_options:
            errors["base"] = "no_providers"

        if user_input is not None:
            try:
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
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        data={
                            **self._config_entry.data,
                            CONF_SCRAPER_NAME: user_input[CONF_SCRAPER_NAME],
                            CONF_PROVIDER_ID: user_input[CONF_PROVIDER_ID],
                            CONF_URL: user_input[CONF_URL],
                            CONF_PROMPT: user_input[CONF_PROMPT],
                            CONF_EXTRACTION_MODE: user_input[CONF_EXTRACTION_MODE],
                        },
                    )
                    return self.async_create_entry(title="done", data={})
            except Exception:  # pylint: disable=broad-except  # noqa: BLE001
                LOGGER.exception(
                    "Unexpected error updating scraper options for %s",
                    self._config_entry.entry_id,
                )
                errors["base"] = "unknown"

        schema_dict: dict[vol.Required, object] = {
            vol.Required(
                CONF_SCRAPER_NAME,
                default=self._config_entry.data.get(CONF_SCRAPER_NAME, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_URL,
                default=self._config_entry.data.get(CONF_URL, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            vol.Required(
                CONF_PROMPT,
                default=self._config_entry.data.get(CONF_PROMPT, vol.UNDEFINED),
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_EXTRACTION_MODE,
                default=self._config_entry.data.get(
                    CONF_EXTRACTION_MODE, vol.UNDEFINED
                ),
            ): vol.In(EXTRACTION_MODES),
        }

        if provider_options:
            schema_dict[
                vol.Required(
                    CONF_PROVIDER_ID,
                    default=self._config_entry.data.get(
                        CONF_PROVIDER_ID, vol.UNDEFINED
                    ),
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=entry_id, label=label
                        )
                        for entry_id, label in provider_options.items()
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="scraper",
            data_schema=schema,
            errors=errors,
        )
