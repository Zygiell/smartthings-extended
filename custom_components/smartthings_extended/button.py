"""Button entities for SmartThings Extended."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, OvenController
from .dishwasher import DishwasherController, async_get_dishwasher_controller
from .microwave import MicrowaveController, async_get_microwave_controller
from .washer import WasherController, async_get_washer_controller


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up appliance command buttons."""
    entities: list[ButtonEntity] = []

    oven = hass.data[DOMAIN].get("oven")
    if isinstance(oven, OvenController):
        for cavity, label in (("upper", "górny"), ("lower", "dolny")):
            entities.extend(
                [
                    OvenButton(
                        oven,
                        cavity,
                        f"Piekarnik {label} — wyślij ustawienia",
                        "send_settings",
                        "mdi:send",
                        oven.send_settings,
                    ),
                    OvenButton(
                        oven,
                        cavity,
                        f"Piekarnik {label} — start",
                        "start",
                        "mdi:play",
                        oven.start,
                    ),
                    OvenButton(
                        oven,
                        cavity,
                        f"Piekarnik {label} — pauza",
                        "pause",
                        "mdi:pause",
                        oven.pause,
                    ),
                    OvenButton(
                        oven,
                        cavity,
                        f"Piekarnik {label} — stop",
                        "stop",
                        "mdi:stop",
                        oven.stop,
                    ),
                ]
            )

    microwave = await async_get_microwave_controller(hass)
    if microwave is not None:
        entities.extend(
            [
                MicrowaveButton(
                    microwave,
                    "Mikrofalówka — wyślij ustawienia",
                    "send_settings",
                    "mdi:send",
                    microwave.send_settings,
                ),
                MicrowaveButton(
                    microwave,
                    "Mikrofalówka — start",
                    "start",
                    "mdi:play",
                    microwave.start,
                ),
                MicrowaveButton(
                    microwave,
                    "Mikrofalówka — pauza",
                    "pause",
                    "mdi:pause",
                    microwave.pause,
                ),
                MicrowaveButton(
                    microwave,
                    "Mikrofalówka — stop",
                    "stop",
                    "mdi:stop",
                    microwave.stop,
                ),
            ]
        )

    washer = await async_get_washer_controller(hass)
    if washer is not None:
        entities.extend(
            [
                WasherButton(
                    washer,
                    "Pralka — wyślij ustawienia",
                    "send_settings",
                    "mdi:send",
                    washer.send_settings,
                ),
                WasherButton(
                    washer,
                    "Pralka — start",
                    "start",
                    "mdi:play",
                    washer.start,
                ),
                WasherButton(
                    washer,
                    "Pralka — pauza",
                    "pause",
                    "mdi:pause",
                    washer.pause,
                ),
                WasherButton(
                    washer,
                    "Pralka — wznów",
                    "resume",
                    "mdi:play-pause",
                    washer.resume,
                ),
                WasherButton(
                    washer,
                    "Pralka — anuluj",
                    "cancel",
                    "mdi:stop",
                    washer.cancel,
                ),
            ]
        )

    dishwasher = await async_get_dishwasher_controller(hass)
    if dishwasher is not None:
        entities.extend(
            [
                DishwasherButton(
                    dishwasher,
                    "Zmywarka — wyślij ustawienia",
                    "send_settings",
                    "mdi:send",
                    dishwasher.send_settings,
                ),
                DishwasherButton(
                    dishwasher,
                    "Zmywarka — start",
                    "start",
                    "mdi:play",
                    dishwasher.start,
                ),
                DishwasherButton(
                    dishwasher,
                    "Zmywarka — pauza",
                    "pause",
                    "mdi:pause",
                    dishwasher.pause,
                ),
                DishwasherButton(
                    dishwasher,
                    "Zmywarka — wznów",
                    "resume",
                    "mdi:play-pause",
                    dishwasher.resume,
                ),
                DishwasherButton(
                    dishwasher,
                    "Zmywarka — anuluj",
                    "cancel",
                    "mdi:stop",
                    dishwasher.cancel,
                ),
                DishwasherButton(
                    dishwasher,
                    "Zmywarka — anuluj i wypompuj",
                    "cancel_and_drain",
                    "mdi:water-pump",
                    dishwasher.cancel_and_drain,
                ),
            ]
        )

    async_add_entities(entities)


class OvenButton(ButtonEntity):
    """Stateless oven command button."""

    _attr_should_poll = False

    def __init__(
        self,
        controller: OvenController,
        cavity: str,
        name: str,
        suffix: str,
        icon: str,
        action: Callable[[str], Awaitable[None]],
    ) -> None:
        self.controller = controller
        self.cavity = cavity
        self._action = action
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_{cavity}_{suffix}"
        )

    async def async_press(self) -> None:
        await self._action(self.cavity)


class MicrowaveButton(ButtonEntity):
    """Stateless microwave command button."""

    _attr_should_poll = False

    def __init__(
        self,
        controller: MicrowaveController,
        name: str,
        suffix: str,
        icon: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        self.controller = controller
        self._action = action
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_microwave_{suffix}"
        )

    async def async_press(self) -> None:
        await self._action()


class WasherButton(ButtonEntity):
    """Stateless washer command button."""

    _attr_should_poll = False

    def __init__(
        self,
        controller: WasherController,
        name: str,
        suffix: str,
        icon: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        self.controller = controller
        self._action = action
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_washer_{suffix}"
        )

    async def async_press(self) -> None:
        await self._action()


class DishwasherButton(ButtonEntity):
    """Stateless dishwasher command button."""

    _attr_should_poll = False

    def __init__(
        self,
        controller: DishwasherController,
        name: str,
        suffix: str,
        icon: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        self.controller = controller
        self._action = action
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_dishwasher_{suffix}"
        )

    async def async_press(self) -> None:
        await self._action()
