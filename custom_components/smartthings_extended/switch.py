"""Switch entities for SmartThings Extended."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .fridge import FridgeController, async_get_fridge_controller


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up refrigerator switches."""
    controller = await async_get_fridge_controller(hass)
    if controller is None:
        return

    async_add_entities(
        [
            FridgeBooleanSwitch(
                controller,
                "Lodówka — AutoFill",
                "autofill",
                "mdi:water-plus",
                lambda: controller.auto_fill,
                controller.set_auto_fill,
                lambda: controller.auto_fill_supported,
            ),
            FridgeBooleanSwitch(
                controller,
                "Lodówka — tryb nocny kostkarki",
                "icemaker_night_mode",
                "mdi:weather-night",
                lambda: controller.icemaker_night_mode,
                controller.set_icemaker_night_mode,
                lambda: controller.icemaker_night_mode_supported,
            ),
            FridgeBooleanSwitch(
                controller,
                "Lodówka — lampka nocna",
                "night_light",
                "mdi:lightbulb-night",
                lambda: controller.night_light,
                controller.set_night_light,
                lambda: controller.night_light_supported,
            ),
        ]
    )


class FridgeBooleanSwitch(SwitchEntity):
    """Direct on/off refrigerator control."""

    _attr_should_poll = False

    def __init__(
        self,
        controller: FridgeController,
        name: str,
        suffix: str,
        icon: str,
        state_getter: Callable[[], bool],
        state_setter: Callable[[bool], Awaitable[None]],
        availability_getter: Callable[[], bool],
    ) -> None:
        self.controller = controller
        self._state_getter = state_getter
        self._state_setter = state_setter
        self._availability_getter = availability_getter
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_fridge_{suffix}"
        )

    @property
    def available(self) -> bool:
        return self._availability_getter()

    @property
    def is_on(self) -> bool:
        return self._state_getter()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._state_setter(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._state_setter(False)

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)
