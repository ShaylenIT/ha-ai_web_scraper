# ruff: noqa: S101
"""Tests for the ai_web_scraper config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM

from custom_components.ai_web_scraper.const import (
    CONF_API_KEY,
    CONF_ENTRY_TYPE,
    CONF_EXTRACTION_MODE,
    CONF_INTERVAL_SECONDS,
    CONF_MODEL_NAME,
    CONF_PROMPT,
    CONF_PROVIDER_ID,
    CONF_PROVIDER_NAME,
    CONF_SCRAPER_NAME,
    CONF_URL,
    DOMAIN,
    ENTRY_TYPE_PROVIDER,
    ENTRY_TYPE_SCRAPER,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_config_flow_shows_choice(hass: HomeAssistant) -> None:
    """Test that the initial config flow step shows the entry type chooser."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert CONF_ENTRY_TYPE in result["data_schema"].schema


async def test_add_provider_profile(hass: HomeAssistant) -> None:
    """Test that the provider creation flow returns a created entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ENTRY_TYPE: ENTRY_TYPE_PROVIDER},
    )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "provider"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVIDER_NAME: "Test Provider",
            CONF_API_KEY: "test-key",
            CONF_MODEL_NAME: "gpt-4",
        },
    )

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "Test Provider"
    assert result["data"][CONF_ENTRY_TYPE] == ENTRY_TYPE_PROVIDER
    assert result["data"][CONF_PROVIDER_NAME] == "Test Provider"


async def test_add_scraper_requires_provider(hass: HomeAssistant) -> None:
    """Test that scraper creation requires a provider when none exist."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER},
    )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "scraper"
    assert result["errors"]["base"] == "no_providers"
    assert "entry_type" in result["data_schema"]


async def test_provider_list_populates_in_scraper_form(hass: HomeAssistant) -> None:
    """Test that available providers appear in the scraper form."""
    provider_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Provider",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_PROVIDER,
            CONF_PROVIDER_NAME: "Test Provider",
            CONF_API_KEY: "test-key",
            CONF_MODEL_NAME: "gpt-4",
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="provider-entry-id",
    )
    provider_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER},
    )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "scraper"
    assert CONF_PROVIDER_ID in result["data_schema"].schema


async def test_add_scraper_with_provider(hass: HomeAssistant) -> None:
    """Test that a scraper can be created when a provider exists."""
    provider_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Provider",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_PROVIDER,
            CONF_PROVIDER_NAME: "Test Provider",
            CONF_API_KEY: "test-key",
            CONF_MODEL_NAME: "gpt-4",
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="provider-entry-id",
    )
    provider_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER},
    )

    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "scraper"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_PROVIDER_ID: provider_entry.entry_id,
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 0,
        },
    )

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert result["data"][CONF_ENTRY_TYPE] == ENTRY_TYPE_SCRAPER
    assert result["data"][CONF_PROVIDER_ID] == provider_entry.entry_id
    assert result["data"][CONF_SCRAPER_NAME] == "Test Scraper"


async def test_provider_reconfigure_updates_entry(hass: HomeAssistant) -> None:
    """Test that provider options flow updates provider data."""
    provider_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Provider",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_PROVIDER,
            CONF_PROVIDER_NAME: "Test Provider",
            CONF_API_KEY: "test-key",
            CONF_MODEL_NAME: "gpt-4",
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="provider-entry-id",
    )
    provider_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(provider_entry.entry_id)
    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "provider"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVIDER_NAME: "Renamed Provider",
            CONF_API_KEY: "updated-key",
            CONF_MODEL_NAME: "gpt-4.1",
        },
    )

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert provider_entry.data[CONF_PROVIDER_NAME] == "Renamed Provider"
    assert provider_entry.data[CONF_API_KEY] == "updated-key"
    assert provider_entry.data[CONF_MODEL_NAME] == "gpt-4.1"


async def test_scraper_reconfigure_updates_entry(hass: HomeAssistant) -> None:
    """Test that scraper options flow updates scraper data."""
    provider_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Provider",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_PROVIDER,
            CONF_PROVIDER_NAME: "Test Provider",
            CONF_API_KEY: "test-key",
            CONF_MODEL_NAME: "gpt-4",
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="provider-entry-id",
    )
    provider_entry.add_to_hass(hass)

    scraper_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Scraper",
        data={
            CONF_ENTRY_TYPE: ENTRY_TYPE_SCRAPER,
            CONF_SCRAPER_NAME: "Test Scraper",
            CONF_PROVIDER_ID: provider_entry.entry_id,
            CONF_URL: "https://example.com",
            CONF_PROMPT: "Extract text",
            CONF_EXTRACTION_MODE: "dom",
            CONF_INTERVAL_SECONDS: 30,
        },
        source=config_entries.SOURCE_USER,
        options={},
        entry_id="scraper-entry-id",
    )
    scraper_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(scraper_entry.entry_id)
    assert result["type"] == RESULT_TYPE_FORM
    assert result["step_id"] == "scraper"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SCRAPER_NAME: "Updated Scraper",
            CONF_PROVIDER_ID: provider_entry.entry_id,
            CONF_URL: "https://example.org",
            CONF_PROMPT: "Update text",
            CONF_EXTRACTION_MODE: "vision",
            CONF_INTERVAL_SECONDS: 60,
        },
    )

    assert result["type"] == RESULT_TYPE_CREATE_ENTRY
    assert scraper_entry.data[CONF_SCRAPER_NAME] == "Updated Scraper"
    assert scraper_entry.data[CONF_URL] == "https://example.org"
    assert scraper_entry.data[CONF_EXTRACTION_MODE] == "vision"
    assert scraper_entry.data[CONF_INTERVAL_SECONDS] == 60
