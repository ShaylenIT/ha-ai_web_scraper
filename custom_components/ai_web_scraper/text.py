"""Text platform for ai_web_scraper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.text import TextEntity, TextEntityDescription

from .const import CONF_NOTES
from .entity import IntegrationBlueprintEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AIWebScraperDataUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    TextEntityDescription(
        key="ai_web_scraper_notes",
        name="Notes",
        icon="mdi:note-text-outline",
        native_max=255,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the text platform."""
    async_add_entities(
        IntegrationBlueprintText(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class IntegrationBlueprintText(IntegrationBlueprintEntity, TextEntity):
    """ai_web_scraper Text (Notes) entity."""

    def __init__(
        self,
        coordinator: AIWebScraperDataUpdateCoordinator,
        entity_description: TextEntityDescription,
    ) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, entity_description)
        self._attr_native_value = ""

    @property
    def native_value(self) -> str:
        """Return the current notes text."""
        if self.coordinator.data:
            return self.coordinator.data.get(CONF_NOTES, "")
        return self._attr_native_value

    async def async_set_value(self, value: str) -> None:
        """Set the notes text and persist it."""
        truncated = value[:255]
        self._attr_native_value = truncated

        # Update coordinator data to include the notes value
        if self.coordinator.data:
            updated = dict(self.coordinator.data)
            updated[CONF_NOTES] = truncated
            self.coordinator.async_set_updated_data(updated)
            await self.coordinator._async_save_to_storage(updated)

        self.async_write_ha_state()
