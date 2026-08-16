"""Switch entities for SmartThings Extended."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .cooktop import CooktopController, async_get_cooktop_controller
from .fridge import FridgeController, async_get_fridge_controller
from .linked_device import smartthings_device_info


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up refrigerator and cooktop switches."""
    entities: list[SwitchEntity] = []

    fridge = await async_get_fridge_controller(hass)
    if fridge is not None:
        entities.extend(
            [
                FridgeBooleanSwitch(
                    fridge,
                    "Lodówka — AutoFill",
                    "autofill",
                    "mdi:water-plus",
                    lambda: fridge.auto_fill,
                    fridge.set_auto_fill,
                    lambda: fridge.auto_fill_supported,
                ),
                FridgeBooleanSwitch(
                    fridge,
                    "Lodówka — tryb nocny kostkarki",
                    "icemaker_night_mode",
                    "mdi:weather-night",
                    lambda: fridge.icemaker_night_mode,
                    fridge.set_icemaker_night_mode,
                    lambda: fridge.icemaker_night_mode_supported,
                ),
                FridgeBooleanSwitch(
                    fridge,
                    "Lodówka — lampka nocna",
                    "night_light",
                    "mdi:lightbulb-night",
                    lambda: fridge.night_light,
                    fridge.set_night_light,
                    lambda: fridge.night_light_supported,
                ),
            ]
        )

    cooktop = await async_get_cooktop_controller(hass)
    if cooktop is not None:
        entities.append(CooktopKidsLockSwitch(cooktop))

    async_add_entities(entities)


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
        self._attr_device_info = smartthings_device_info(controller.device_id)

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


class CooktopKidsLockSwitch(SwitchEntity):
    """Direct cooktop child-lock control."""

    _attr_should_poll = False
    _attr_name = "Płyta — blokada dziecięca"
    _attr_icon = "mdi:lock"

    def __init__(self, controller: CooktopController) -> None:
        self.controller = controller
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_cooktop_kids_lock"
        )
        self._attr_device_info = smartthings_device_info(controller.device_id)

    @property
    def available(self) -> bool:
        return self.controller.kids_lock_supported

    @property
    def is_on(self) -> bool:
        return self.controller.kids_lock_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.controller.set_kids_lock(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.controller.set_kids_lock(False)

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)
