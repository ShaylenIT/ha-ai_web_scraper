"""Custom types and storage helpers for ai_web_scraper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.loader import Integration

    from .api import IntegrationBlueprintApiClient
    from .coordinator import AIWebScraperDataUpdateCoordinator

from .const import CONF_ENTRY_TYPE, ENTRY_TYPE_PROVIDER, ENTRY_TYPE_SCRAPER

IntegrationBlueprintConfigEntry = ConfigEntry


def get_provider_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Return provider config entries for this integration."""
    return [
        entry
        for entry in hass.config_entries.async_entries("ai_web_scraper")
        if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_PROVIDER
    ]


def get_provider_entry(hass: HomeAssistant, provider_id: str) -> ConfigEntry | None:
    """Return a provider config entry by ID."""
    return next(
        (
            entry
            for entry in get_provider_entries(hass)
            if entry.entry_id == provider_id
        ),
        None,
    )


def get_scraper_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Return scraper config entries for this integration."""
    return [
        entry
        for entry in hass.config_entries.async_entries("ai_web_scraper")
        if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_SCRAPER
    ]


def get_scraper_entry(hass: HomeAssistant, entry_id: str) -> ConfigEntry | None:
    """Return a scraper config entry by ID."""
    return next(
        (entry for entry in get_scraper_entries(hass) if entry.entry_id == entry_id),
        None,
    )


def provider_options(hass: HomeAssistant) -> dict[str, str]:
    """Return provider options for the scraper configuration form."""
    return {entry.entry_id: entry.title for entry in get_provider_entries(hass)}


@dataclass
class IntegrationBlueprintData:
    """Data for the ai_web_scraper integration."""

    client: IntegrationBlueprintApiClient
    coordinator: AIWebScraperDataUpdateCoordinator
    integration: Integration
