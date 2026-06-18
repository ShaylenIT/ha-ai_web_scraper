"""Sensor platform for ai_web_scraper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.util import dt as dt_util

from .const import SCRAPER_STATUS_ATTR
from .entity import AiWebScraperEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AIWebScraperDataUpdateCoordinator
    from .data import AiWebScraperConfigEntry

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="ai_web_scraper_data",
        name="Scraper Latest Data",
        icon="mdi:text-box",
    ),
    SensorEntityDescription(
        key="ai_web_scraper_previous_data",
        name="Scraper Previous Data",
        icon="mdi:text-box-outline",
    ),
    SensorEntityDescription(
        key="ai_web_scraper_status",
        name="Scraper Phase",
        icon="mdi:progress-clock",
    ),
    SensorEntityDescription(
        key="ai_web_scraper_last_scrape",
        name="Last Scrape",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: AiWebScraperConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        AiWebScraperSensor(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class AiWebScraperSensor(AiWebScraperEntity, SensorEntity):
    """ai_web_scraper Sensor class."""

    def __init__(
        self,
        coordinator: AIWebScraperDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description)

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        if self.entity_description.key == "ai_web_scraper_status":
            return self.coordinator.data.get("attributes", {}).get(
                SCRAPER_STATUS_ATTR, "unknown"
            )

        if self.entity_description.key == "ai_web_scraper_last_scrape":
            last_scrape = self.coordinator.data.get("attributes", {}).get("last_scrape")
            if isinstance(last_scrape, str):
                return dt_util.parse_datetime(last_scrape)
            return last_scrape

        if self.entity_description.key == "ai_web_scraper_previous_data":
            return self.coordinator.data.get("previous_state")

        state = self.coordinator.data.get("state")
        return state

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes of the sensor."""
        return self.coordinator.data.get("attributes")
