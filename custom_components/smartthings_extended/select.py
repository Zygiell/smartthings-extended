"""Select entities for SmartThings Extended."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, OvenController


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up oven mode selectors."""
    controller: OvenController = hass.data[DOMAIN]["oven"]
    async_add_entities(
        [
            OvenModeSelect(controller, "upper", "Piekarnik górny — tryb"),
            OvenModeSelect(controller, "lower", "Piekarnik dolny — tryb"),
        ]
    )


class OvenModeSelect(SelectEntity):
    """Prepared oven mode selector."""

    _attr_should_poll = False
    _attr_icon = "mdi:chef-hat"

    def __init__(
        self, controller: OvenController, cavity: str, name: str
    ) -> None:
        self.controller = controller
        self.cavity = cavity
        self._attr_name = name
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_{cavity}_mode"
        )

    @property
    def options(self) -> list[str]:
        return [
            self.controller.mode_label(mode)
            for mode in self.controller.supported_modes(self.cavity)
        ]

    @property
    def current_option(self) -> str:
        return self.controller.mode_label(
            self.controller.selected_mode[self.cavity]
        )

    async def async_select_option(self, option: str) -> None:
        mode = self.controller.mode_from_label(self.cavity, option)
        self.controller.set_mode(self.cavity, mode)

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)
