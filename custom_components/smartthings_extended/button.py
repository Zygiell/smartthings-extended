"""Button entities for SmartThings Extended."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
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
    """Set up oven command buttons."""
    controller: OvenController = hass.data[DOMAIN]["oven"]
    entities: list[ButtonEntity] = []

    for cavity, label in (("upper", "górny"), ("lower", "dolny")):
        entities.extend(
            [
                OvenButton(
                    controller,
                    cavity,
                    f"Piekarnik {label} — wyślij ustawienia",
                    "send_settings",
                    "mdi:send",
                    controller.send_settings,
                ),
                OvenButton(
                    controller,
                    cavity,
                    f"Piekarnik {label} — start",
                    "start",
                    "mdi:play",
                    controller.start,
                ),
                OvenButton(
                    controller,
                    cavity,
                    f"Piekarnik {label} — pauza",
                    "pause",
                    "mdi:pause",
                    controller.pause,
                ),
                OvenButton(
                    controller,
                    cavity,
                    f"Piekarnik {label} — stop",
                    "stop",
                    "mdi:stop",
                    controller.stop,
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
