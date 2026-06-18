"""
Custom integration to integrate ai_web_scraper with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/ai_web_scraper
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import AiWebScraperClient
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_BLOCK_CONSENT_MODALS,
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
    LOGGER,
    OPENAI_COMPATIBLE_TYPES,
    PROVIDER_BASE_URLS,
    ProviderType,
    SAVE_MARKDOWN_DEBUG,
)
from .coordinator import AIWebScraperDataUpdateCoordinator
from .data import (
    AiWebScraperConfigEntry,
    AiWebScraperData,
    get_provider_entry,
    get_scraper_entries,
)


def _build_entry_client(
    hass: HomeAssistant,
    entry: AiWebScraperConfigEntry,
) -> AiWebScraperClient:
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
        provider_type = provider_entry.data.get(CONF_PROVIDER_TYPE, ProviderType.OPENAI)
    else:
        provider_type = ProviderType.OPENAI

    # Resolve base URL: use user-configured value, or fall back to default for known providers
    base_url = provider_entry.data.get(CONF_BASE_URL, "") if provider_entry else ""
    if not base_url and provider_type in OPENAI_COMPATIBLE_TYPES:
        base_url = PROVIDER_BASE_URLS.get(provider_type, "https://api.openai.com/v1")

    screenshot_dir = hass.config.path(DOMAIN, "screenshots")
    Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

    markdown_dir = hass.config.path(DOMAIN, "markdown")
    Path(markdown_dir).mkdir(parents=True, exist_ok=True)

    block_consent_modals = entry.options.get(
        CONF_BLOCK_CONSENT_MODALS,
        entry.data.get(CONF_BLOCK_CONSENT_MODALS, True),
    )

    provider_id = entry.data.get(CONF_PROVIDER_ID, "")
    cooldown_seconds = (
        int(provider_entry.data.get(CONF_COOL_DOWN_SECONDS, 0)) if provider_entry else 0
    )
    request_timeout = (
        int(provider_entry.data.get(CONF_REQUEST_TIMEOUT, 30)) if provider_entry else 30
    )

    return AiWebScraperClient(
        provider_name=provider_name,
        api_key=api_key,
        model_name=model_name,
        browserless_url=browserless_url,
        provider_type=provider_type,
        base_url=base_url,
        scraper_name=entry.data.get(CONF_SCRAPER_NAME, entry.title),
        url=entry.data.get(CONF_URL, ""),
        prompt=entry.data.get(CONF_PROMPT, ""),
        extraction_mode=entry.data.get(CONF_EXTRACTION_MODE, "dom"),
        session=async_get_clientsession(hass),
        screenshot_dir=screenshot_dir,
        screenshot_filename=f"{entry.entry_id}.png",
        markdown_dir=markdown_dir,
        markdown_filename=f"{entry.entry_id}.md",
        save_markdown_debug=SAVE_MARKDOWN_DEBUG,
        block_consent_modals=block_consent_modals,
        provider_id=provider_id,
        cooldown_seconds=cooldown_seconds,
        request_timeout=request_timeout,
    )


if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.IMAGE,
    Platform.SWITCH,
    Platform.TEXT,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: AiWebScraperConfigEntry,
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
    interval_seconds = entry.data.get(CONF_INTERVAL_SECONDS, 0)
    if interval_seconds and interval_seconds > 0:
        update_interval = timedelta(seconds=int(interval_seconds))

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=entry.title,
        update_interval=update_interval,
    )
    coordinator.config_entry = entry

    entry.runtime_data = AiWebScraperData(
        client=_build_entry_client(hass, entry),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # Wire live status updates: client → coordinator → entity listeners
    entry.runtime_data.client.set_status_callback(coordinator._set_status_callback)

    await coordinator.async_load_from_storage()

    # Create entities BEFORE the first refresh so they're alive to receive
    # live phase updates (queued → rendering_page → ... → completed) and
    # serve the screenshot immediately after it's captured.
    entry.async_on_unload(entry.add_update_listener(async_on_scraper_config_update))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Fire the first refresh as a background task so async_setup_entry
    # returns immediately — the integration won't show "Initialising"
    # while waiting in the semaphore queue behind other scrapers.
    # Entities are already live with stored data from async_load_from_storage().
    #
    # async_config_entry_first_refresh is NOT used here because it calls
    # async_setup_done AFTER the refresh, keeping HA's "Starting"
    # notification visible until all scrapers finish. Instead we call
    # async_setup_done first and then manually trigger the refresh, so
    # HA considers the entry ready immediately.
    async def _initial_refresh() -> None:
        hass.config_entries.async_setup_done(entry)
        await coordinator._async_refresh(scheduled=False)
        # Stagger scraper startups so each one doesn't slam Browserless
        # immediately. The global semaphore in api.py already serialises
        # concurrent scrape operations — this extra delay spreads out the
        # initial load across several seconds to further help Browserless
        # keep up.
        await asyncio.sleep(3)

    refresh_task = hass.async_create_task(_initial_refresh())
    entry.async_on_unload(refresh_task.cancel)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: AiWebScraperConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_PROVIDER:
        return True
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_provider_dependents(
    hass: HomeAssistant,
    entry: AiWebScraperConfigEntry,
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


async def async_on_scraper_config_update(
    hass: HomeAssistant,
    entry: AiWebScraperConfigEntry,
) -> None:
    """
    Handle scraper config updates without full reload.

    Rebuilds the API client in-place so entities stay available.
    The number entity (scrape interval) already updates the coordinator
    interval directly, so no extra work is needed for that case.
    """
    runtime_data = entry.runtime_data
    if runtime_data is None:
        return

    # Rebuild the client with the updated config/options
    runtime_data.client = _build_entry_client(hass, entry)

    # Re-wire live status updates on the rebuilt client so phase
    # changes during manual refresh propagate to coordinator entities.
    runtime_data.client.set_status_callback(
        runtime_data.coordinator._set_status_callback
    )

    # If the interval changed, the number entity already set it on the
    # coordinator. If it hasn't (e.g. options flow change), sync it here.
    interval_seconds = entry.data.get(CONF_INTERVAL_SECONDS, 0)
    if interval_seconds and interval_seconds > 0:
        runtime_data.coordinator.update_interval = timedelta(
            seconds=int(interval_seconds)
        )
    else:
        runtime_data.coordinator.update_interval = None
