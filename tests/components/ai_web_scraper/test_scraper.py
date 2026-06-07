"""Tests for the ai_web_scraper scraper entity behavior."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry

from custom_components.ai_web_scraper.const import (
    CONF_ENTRY_TYPE,
    CONF_PROVIDER_ID,
    CONF_SCRAPER_NAME,
    CONF_URL,
    CONF_PROMPT,
    CONF_EXTRACTION_MODE,
    CONF_INTERVAL_SECONDS,
    DOMAIN,
    ENTRY_TYPE_SCRAPER,
)
from custom_components.ai_web_scraper.coordinator import AIWebScraperDataUpdateCoordinator
from custom_components.ai_web_scraper.const import LOGGER
from custom_components.ai_web_scraper.data import IntegrationBlueprintData


async def test_coordinator_fetches_scrape_data(hass):
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_PROVIDER_ID: "provider-id",
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
        source="user",
        options={},
        entry_id="scraper-entry-id",
    )
    entry.add_to_hass(hass)

    coordinator = AIWebScraperDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name="Test Scraper",
        update_interval=None,
    )
    coordinator.config_entry = entry

    client = AsyncMock()
    client.async_get_data.return_value = {
        "state": "hello",
        "attributes": {"url": "https://example.com"},
        "error_message": "",
        "last_attempt_status": "success",
    }

    entry.runtime_data = IntegrationBlueprintData(
        client=client,
        integration=None,
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data["state"] == "hello"
    assert coordinator.data["attributes"]["url"] == "https://example.com"
    assert coordinator.data["last_attempt_status"] == "success"
