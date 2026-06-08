"""
Custom integration to integrate ai_web_scraper with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/ai_web_scraper
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import IntegrationBlueprintApiClient
from .const import (
    CONF_API_KEY,
    CONF_BROWSERLESS_URL,
    CONF_ENTRY_TYPE,
    CONF_EXTRACTION_MODE,
    CONF_INTERVAL_SECONDS,
    CONF_MODEL_NAME,
    CONF_PROMPT,
    CONF_PROVIDER_ID,
    CONF_PROVIDER_NAME,
    CONF_PROVIDER_TYPE,
    CONF_SCRAPER_NAME,
    CONF_URL,
    ENTRY_TYPE_PROVIDER,
    ENTRY_TYPE_SCRAPER,
    LOGGER,
    PROVIDER_TYPE_OPENAI,
)
from .coordinator import AIWebScraperDataUpdateCoordinator
from .data import (
    IntegrationBlueprintConfigEntry,
    IntegrationBlueprintData,
    get_provider_entry,
    get_scraper_entries,
)


def _build_entry_client(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> IntegrationBlueprintApiClient:
    provider_entry = get_provider_entry(hass, entry.data.get(CONF_PROVIDER_ID, ""))
    provider_name = ""
    api_key = ""
    model_name = ""
    browserless_url = ""

    if provider_entry is not None:
        provider_name = provider_entry.data.get(
            CONF_PROVIDER_NAME, provider_entry.title
        )
        api_key = provider_entry.data.get(CONF_API_KEY, "")
        model_name = provider_entry.data.get(CONF_MODEL_NAME, "")
        browserless_url = provider_entry.data.get(CONF_BROWSERLESS_URL, "")
        provider_type = provider_entry.data.get(
            CONF_PROVIDER_TYPE, PROVIDER_TYPE_OPENAI
        )
    else:
        provider_type = PROVIDER_TYPE_OPENAI

    return IntegrationBlueprintApiClient(
        provider_name=provider_name,
        api_key=api_key,
        model_name=model_name,
        browserless_url=browserless_url,
        provider_type=provider_type,
        scraper_name=entry.data.get(CONF_SCRAPER_NAME, entry.title),
        url=entry.data.get(CONF_URL, ""),
        prompt=entry.data.get(CONF_PROMPT, ""),
        extraction_mode=entry.data.get(CONF_EXTRACTION_MODE, "dom"),
        session=async_get_clientsession(hass),
    )


if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_PROVIDER:
        entry.async_on_unload(
            entry.add_update_listener(async_reload_provider_dependents)
        )
        return True

    if entry.data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_SCRAPER:
        return False

    update_interval = None
    interval_seconds = entry.data.get(CONF_INTERVAL_SECONDS, 60)
    if interval_seconds and interval_seconds > 0:
        update_interval = timedelta(seconds=int(interval_seconds))

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=entry.title,
        update_interval=update_interval,
    )
    coordinator.config_entry = entry

    entry.runtime_data = IntegrationBlueprintData(
        client=_build_entry_client(hass, entry),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_PROVIDER:
        return True
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_provider_dependents(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> None:
    """Reload scraper entries that depend on an updated provider."""
    for scraper_entry in get_scraper_entries(hass):
        if scraper_entry.data.get(CONF_PROVIDER_ID) == entry.entry_id:
            try:
                await hass.config_entries.async_reload(scraper_entry.entry_id)
            except Exception:  # pylint: disable=broad-except  # noqa: BLE001
                LOGGER.exception(
                    "Failed reloading scraper entry %s after provider update",
                    scraper_entry.entry_id,
                )


async def async_reload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> None:
    """Reload config entry."""
    try:
        await hass.config_entries.async_reload(entry.entry_id)
    except Exception:  # pylint: disable=broad-except  # noqa: BLE001
        LOGGER.exception(
            "Failed reloading config entry %s after options update",
            entry.entry_id,
        )
