"""Select entities for SmartThings Extended."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, OvenController
from .microwave import MicrowaveController, async_get_microwave_controller


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up prepared-setting selectors."""
    entities: list[SelectEntity] = []

    oven = hass.data[DOMAIN].get("oven")
    if isinstance(oven, OvenController):
        entities.extend(
            [
                OvenModeSelect(oven, "upper", "Piekarnik górny — tryb"),
                OvenModeSelect(oven, "lower", "Piekarnik dolny — tryb"),
            ]
        )

    microwave = await async_get_microwave_controller(hass)
    if microwave is not None:
        entities.extend(
            [
                MicrowaveModeSelect(microwave),
                MicrowavePowerSelect(microwave),
            ]
        )

    async_add_entities(entities)


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


class MicrowaveBaseSelect(SelectEntity):
    """Base select entity for prepared microwave settings."""

    _attr_should_poll = False

    def __init__(self, controller: MicrowaveController, suffix: str) -> None:
        self.controller = controller
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_microwave_{suffix}"
        )

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)


class MicrowaveModeSelect(MicrowaveBaseSelect):
    """Prepared microwave mode selector."""

    _attr_name = "Mikrofalówka — tryb"
    _attr_icon = "mdi:microwave"

    def __init__(self, controller: MicrowaveController) -> None:
        super().__init__(controller, "mode")

    @property
    def options(self) -> list[str]:
        return [
            self.controller.mode_label(mode)
            for mode in self.controller.supported_modes()
        ]

    @property
    def current_option(self) -> str:
        return self.controller.mode_label(self.controller.selected_mode)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_mode(self.controller.mode_from_label(option))


class MicrowavePowerSelect(MicrowaveBaseSelect):
    """Prepared microwave power selector."""

    _attr_name = "Mikrofalówka — moc"
    _attr_icon = "mdi:flash"

    def __init__(self, controller: MicrowaveController) -> None:
        super().__init__(controller, "power")

    @property
    def available(self) -> bool:
        return bool(self.controller.power_levels())

    @property
    def options(self) -> list[str]:
        return self.controller.power_levels() or [self.controller.power_level]

    @property
    def current_option(self) -> str:
        return self.controller.power_level

    async def async_select_option(self, option: str) -> None:
        self.controller.set_power_level(option)
