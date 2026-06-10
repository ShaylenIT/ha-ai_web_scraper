"""Camera platform for ai_web_scraper."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.camera import CameraEntity

from .entity import IntegrationBlueprintEntity
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AIWebScraperDataUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the camera platform."""
    screenshot_path = hass.config.path(DOMAIN, "screenshots", f"{entry.entry_id}.png")
    async_add_entities(
        [IntegrationBlueprintCamera(entry.runtime_data.coordinator, screenshot_path)]
    )


class IntegrationBlueprintCamera(IntegrationBlueprintEntity, CameraEntity):
    """ai_web_scraper Camera class."""

    def __init__(
        self,
        coordinator: AIWebScraperDataUpdateCoordinator,
        screenshot_path: str,
    ) -> None:
        """Initialize the camera entity."""
        super().__init__(coordinator)
        self._screenshot_path = screenshot_path
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_screenshot"
        self._attr_name = f"{coordinator.config_entry.title} Screenshot"

    @property
    def available(self) -> bool:
        """Return whether the screenshot is available."""
        return Path(self._screenshot_path).is_file()

    async def async_camera_image(self) -> bytes | None:
        """Return the last saved screenshot image."""
        screenshot_file = Path(self._screenshot_path)
        if not screenshot_file.is_file():
            return None
        return screenshot_file.read_bytes()
