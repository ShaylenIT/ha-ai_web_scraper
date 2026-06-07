"""Button platform for ai_web_scraper."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription

from .entity import IntegrationBlueprintEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AIWebScraperDataUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    ButtonEntityDescription(
        key="ai_web_scraper_refresh",
        name="Refresh Scraper",
        icon="mdi:refresh",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    async_add_entities(
        IntegrationBlueprintButton(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class IntegrationBlueprintButton(IntegrationBlueprintEntity, ButtonEntity):
    """ai_web_scraper button entity."""

    def __init__(
        self,
        coordinator: AIWebScraperDataUpdateCoordinator,
        entity_description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator, entity_description)

    async def async_press(self) -> None:
        """Handle the button press by refreshing scraper data."""
        await self.coordinator.async_request_refresh()
