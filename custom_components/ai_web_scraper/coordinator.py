"""DataUpdateCoordinator for ai_web_scraper."""

from __future__ import annotations

from datetime import datetime, timezone
from logging import Logger
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import (
    AiWebScraperClientAuthenticationError,
    AiWebScraperClientError,
)
from .const import (
    CONF_EXTRACTION_MODE,
    CONF_NOTES,
    CONF_PROMPT,
    CONF_PROVIDER_NAME,
    CONF_URL,
    DOMAIN,
    LOGGER,
    SCRAPER_STATUS_ATTR,
    ScraperPhase,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import AiWebScraperConfigEntry

STORAGE_VERSION = 1


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class AIWebScraperDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: AiWebScraperConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: AiWebScraperConfigEntry | None = None,
        logger: Logger | None = None,  # noqa: ARG002 Unused — passed through to parent
        **kwargs: Any,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, LOGGER, config_entry=config_entry, **kwargs)
        self._current_status: str = ScraperPhase.IDLE

    @property
    def current_status(self) -> str:
        """Return the live scraper status phase."""
        return self._current_status

    def _reschedule_refresh_timer(self) -> None:
        """Cancel the pending auto-refresh timer and schedule a new one.

        Called after the user changes the scrape interval so the new
        interval takes effect immediately instead of waiting for the
        old timer to fire first.
        """
        if self._unsub_refresh is not None:
            self._unsub_refresh()
            self._unsub_refresh = None
        self._unsub_refresh = async_call_later(
            self.hass,
            self.update_interval.total_seconds(),
            lambda _: self._async_refresh(),
        )

    def _set_status_callback(self, status: str) -> None:
        """Callback invoked by the API client when the scraper phase changes.

        Writes the new status into coordinator state immediately and
        notifies entity listeners so the phase sensor updates in real time.
        """
        if status != self._current_status:
            self._current_status = status
            if self.data:
                old_data = dict(self.data)
                attrs = dict(old_data.get("attributes", {}))
                attrs[SCRAPER_STATUS_ATTR] = status
                old_data["attributes"] = attrs
                self.async_set_updated_data(old_data)

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
        """Restore the last persisted scrape state before fetching new data.

        Resets the phase to idle since no scrape is actively running after
        a Home Assistant restart.
        """
        if stored := await self._storage().async_load():
            attrs = dict(stored.get("attributes", {}))
            attrs[SCRAPER_STATUS_ATTR] = ScraperPhase.IDLE
            stored["attributes"] = attrs
            self._current_status = ScraperPhase.IDLE
            self.async_set_updated_data(stored)

    async def _async_save_to_storage(self, data: dict[str, Any]) -> None:
        """Persist scrape state so entities survive restarts."""
        await self._storage().async_save(data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            new_data = await self.config_entry.runtime_data.client.async_get_data()

            # Preserve the notes value across scrape updates
            notes = ""
            if self.data:
                notes = self.data.get(CONF_NOTES, "")
            if notes:
                new_data[CONF_NOTES] = notes

            previous_state = None
            if self.data:
                previous_state = self.data.get("previous_state")
            if new_data.get("last_attempt_status") == "success" and self.data:
                previous_state = self._get_display_state(self.data)
            new_data["previous_state"] = previous_state
            await self._async_save_to_storage(new_data)
            return new_data
        except AiWebScraperClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except AiWebScraperClientError as exception:
            self.logger.exception(
                "Scraper data fetch failed for %s",
                self.config_entry.title,
            )
            error_message = str(exception)
            previous_state = self._get_display_state(self.data) if self.data else None
            failure_data = {
                "state": previous_state,
                "attributes": {
                    "url": self.config_entry.data.get(CONF_URL, ""),
                    "prompt": self.config_entry.data.get(CONF_PROMPT, ""),
                    "provider_name": self.config_entry.data.get(CONF_PROVIDER_NAME, ""),
                    "extraction_mode": self.config_entry.data.get(
                        CONF_EXTRACTION_MODE, ""
                    ),
                    "scrape_duration_seconds": 0,
                    "last_successful_scrape": (
                        self.data.get("attributes", {}).get("last_successful_scrape")
                        if self.data
                        else None
                    ),
                    "last_scrape": datetime.now(timezone.utc).isoformat(),
                    SCRAPER_STATUS_ATTR: f"failed - {error_message}",
                },
                "error_message": error_message,
                "last_attempt_status": "failure",
            }
            # Preserve the notes value on error
            if self.data and self.data.get(CONF_NOTES):
                failure_data[CONF_NOTES] = self.data[CONF_NOTES]
            if self.data and self.data.get("previous_state") is not None:
                failure_data["previous_state"] = self.data["previous_state"]
            await self._async_save_to_storage(failure_data)
            return failure_data
