"""Number platform for ai_web_scraper."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)

from .const import CONF_INTERVAL_SECONDS
from .entity import IntegrationBlueprintEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AIWebScraperDataUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    NumberEntityDescription(
        key="ai_web_scraper_interval",
        name="Scrape interval",
        icon="mdi:timer-sand",
        native_unit_of_measurement="minutes",
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    async_add_entities(
        IntegrationBlueprintNumber(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class IntegrationBlueprintNumber(IntegrationBlueprintEntity, NumberEntity):
    """ai_web_scraper Number entity."""

    def __init__(
        self,
        coordinator: AIWebScraperDataUpdateCoordinator,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> int | float | None:
        """Return the current scrape interval in minutes."""
        interval_seconds = self.coordinator.config_entry.data.get(
            CONF_INTERVAL_SECONDS, 0
        )
        interval_minutes = interval_seconds / 60
        return (
            int(interval_minutes) if interval_minutes.is_integer() else interval_minutes
        )

    @property
    def native_min_value(self) -> int:
        """Return the minimum allowed value."""
        return 0

    @property
    def native_step(self) -> int:
        """Return the step size for the interval."""
        return 1

    async def async_set_native_value(self, value: float) -> None:
        """Update the scrape interval value."""
        seconds = int(value * 60)
        new_data = {
            **self.coordinator.config_entry.data,
            CONF_INTERVAL_SECONDS: seconds,
        }

        self.coordinator.update_interval = (
            timedelta(seconds=seconds) if seconds > 0 else None
        )
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry,
            data=new_data,
        )
        self.async_write_ha_state()

        # Reschedule the auto-refresh timer so the new interval takes
        # effect immediately instead of waiting for the old timer.
        if seconds > 0:
            self.coordinator._reschedule_refresh_timer()
