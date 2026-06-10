"""Image platform for ai_web_scraper."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity

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
    """Set up the image platform."""
    screenshot_path = hass.config.path(DOMAIN, "screenshots", f"{entry.entry_id}.png")
    async_add_entities(
        [
            IntegrationBlueprintImage(
                hass, entry.runtime_data.coordinator, screenshot_path
            )
        ]
    )


class IntegrationBlueprintImage(IntegrationBlueprintEntity, ImageEntity):
    """ai_web_scraper Image class."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: AIWebScraperDataUpdateCoordinator,
        screenshot_path: str,
    ) -> None:
        """Initialize the image entity."""
        super().__init__(hass)
        self.coordinator = coordinator
        self._screenshot_path = Path(screenshot_path)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_screenshot"
        self._attr_name = f"{coordinator.config_entry.title} Screenshot"
        self._attr_content_type = "image/png"
        self._attr_device_info = {
            "identifiers": {
                (
                    coordinator.config_entry.domain,
                    coordinator.config_entry.entry_id,
                ),
            },
            "name": coordinator.config_entry.title,
            "manufacturer": "AI Web Scraper",
            "model": "Scraper Entry",
        }

    @property
    def image_last_updated(self) -> datetime | None:
        if not self._screenshot_path.is_file():
            return None
        return datetime.fromtimestamp(
            self._screenshot_path.stat().st_mtime, tz=timezone.utc
        )

    @property
    def available(self) -> bool:
        """Return whether the screenshot is available."""
        return self._screenshot_path.is_file()

    def image(self) -> bytes | None:
        """Return the last saved screenshot image."""
        if not self._screenshot_path.is_file():
            return None
        return self._screenshot_path.read_bytes()
