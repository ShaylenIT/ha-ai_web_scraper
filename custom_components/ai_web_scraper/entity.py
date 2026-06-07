"""ai_web_scraper entity base class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .coordinator import AIWebScraperDataUpdateCoordinator


class IntegrationBlueprintEntity(CoordinatorEntity[AIWebScraperDataUpdateCoordinator]):
    """Base entity for ai_web_scraper."""

    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AIWebScraperDataUpdateCoordinator,
        entity_description: EntityDescription | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        if entity_description is not None:
            self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{entity_description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
            name=coordinator.config_entry.title,
            manufacturer="AI Web Scraper",
            model="Scraper Entry",
        )
