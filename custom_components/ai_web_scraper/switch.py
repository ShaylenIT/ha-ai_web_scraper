"""Switch platform for ai_web_scraper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

from .const import CONF_BLOCK_CONSENT_MODALS
from .entity import IntegrationBlueprintEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AIWebScraperDataUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key=CONF_BLOCK_CONSENT_MODALS,
        name="Block Overlays",
        icon="mdi:window-closed-variant",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities(
        IntegrationBlueprintSwitch(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class IntegrationBlueprintSwitch(IntegrationBlueprintEntity, SwitchEntity):
    """ai_web_scraper switch class."""

    def __init__(
        self,
        coordinator: AIWebScraperDataUpdateCoordinator,
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config_entry.options.get(
            CONF_BLOCK_CONSENT_MODALS,
            self.coordinator.config_entry.data.get(CONF_BLOCK_CONSENT_MODALS, True),
        )

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        new_options = {
            **self.coordinator.config_entry.options,
            CONF_BLOCK_CONSENT_MODALS: True,
        }
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry,
            options=new_options,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        new_options = {
            **self.coordinator.config_entry.options,
            CONF_BLOCK_CONSENT_MODALS: False,
        }
        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry,
            options=new_options,
        )
        self.async_write_ha_state()
