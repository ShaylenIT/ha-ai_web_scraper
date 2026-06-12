"""DataUpdateCoordinator for ai_web_scraper."""

from __future__ import annotations

from datetime import datetime, timezone
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

    @staticmethod
    def _get_display_state(data: dict[str, Any]) -> str | None:
        """Return the value shown by the latest data sensor."""
        state = data.get("state")
        if state is None and data.get("last_attempt_status") == "failure":
            return data.get("error_message")
        return state

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            new_data = await self.config_entry.runtime_data.client.async_get_data()
            previous_state = None
            if self.data:
                previous_state = self.data.get("previous_state")
            if new_data.get("last_attempt_status") == "success" and self.data:
                previous_state = self._get_display_state(self.data)
            new_data["previous_state"] = previous_state
            return new_data
        except IntegrationBlueprintApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except IntegrationBlueprintApiClientError as exception:
            self.logger.exception(
                "Scraper data fetch failed for %s",
                self.config_entry.title,
            )
            failure_data = {
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
                    "last_scrape": datetime.now(timezone.utc).isoformat(),
                    "scraper_status": "failed",
                },
                "error_message": str(exception),
                "last_attempt_status": "failure",
            }
            if self.data:
                failure_data["previous_state"] = self.data.get("previous_state")
            return failure_data
