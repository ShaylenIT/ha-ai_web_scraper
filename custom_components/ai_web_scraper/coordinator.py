"""DataUpdateCoordinator for ai_web_scraper."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientError,
)
from .const import CONF_EXTRACTION_MODE, CONF_PROMPT, CONF_PROVIDER_NAME, CONF_URL, DOMAIN

if TYPE_CHECKING:
    from .data import IntegrationBlueprintConfigEntry

STORAGE_VERSION = 1


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

    def _storage(self) -> Store[dict[str, Any]]:
        """Return the storage helper for this scraper entry."""
        return Store(
            self.hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{self.config_entry.entry_id}.scrape_state",
        )

    async def async_load_from_storage(self) -> None:
        """Restore the last persisted scrape state before fetching new data."""
        if stored := await self._storage().async_load():
            self.async_set_updated_data(stored)

    async def _async_save_to_storage(self, data: dict[str, Any]) -> None:
        """Persist scrape state so entities survive restarts."""
        await self._storage().async_save(data)

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
            await self._async_save_to_storage(new_data)
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
            await self._async_save_to_storage(failure_data)
            return failure_data
