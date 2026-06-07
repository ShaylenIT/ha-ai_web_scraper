"""DataUpdateCoordinator for ai_web_scraper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientError,
)
from .const import CONF_EXTRACTION_MODE, CONF_PROMPT, CONF_PROVIDER_NAME, CONF_URL

if TYPE_CHECKING:
    from .data import IntegrationBlueprintConfigEntry


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class AIWebScraperDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: IntegrationBlueprintConfigEntry

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            return await self.config_entry.runtime_data.client.async_get_data()
        except IntegrationBlueprintApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except IntegrationBlueprintApiClientError as exception:
            return {
                "state": None,
                "attributes": {
                    "url": self.config_entry.data.get(CONF_URL, ""),
                    "prompt": self.config_entry.data.get(CONF_PROMPT, ""),
                    "provider_name": self.config_entry.data.get(CONF_PROVIDER_NAME, ""),
                    "extraction_mode": self.config_entry.data.get(
                        CONF_EXTRACTION_MODE, ""
                    ),
                    "scrape_duration_seconds": 0,
                    "last_successful_scrape": None,
                },
                "error_message": str(exception),
                "last_attempt_status": "failure",
            }
