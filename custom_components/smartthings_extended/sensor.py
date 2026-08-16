"""Sensor entities for SmartThings Extended."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .cooktop import CooktopController, async_get_cooktop_controller


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up cooktop status sensors."""
    controller = await async_get_cooktop_controller(hass)
    if controller is None:
        return

    async_add_entities(
        [CooktopBurnerStatusSensor(controller, burner) for burner in controller.burners]
    )


class CooktopBurnerStatusSensor(SensorEntity):
    """Residual-heat state with burner details as attributes."""

    _attr_should_poll = False
    _attr_icon = "mdi:heat-wave"

    def __init__(self, controller: CooktopController, burner: str) -> None:
        self.controller = controller
        self.burner = burner
        number = controller.burner_number(burner)
        self._attr_name = f"Płyta — Pole {number} — ciepło resztkowe"
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_cooktop_{burner}_status"
        )

    @property
    def native_value(self) -> str:
        return self.controller.residual_heat_label(self.burner)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "component": self.burner,
            "manual_level": self.controller.manual_level.get(self.burner, 0),
            "heating_mode": self.controller.heating_mode.get(self.burner, "manual"),
            "heating_mode_label": self.controller.heating_mode_label(self.burner),
            "timer_start_value": self.controller.timer_start_value.get(self.burner, 0),
            "timer_current_value": self.controller.timer_current_value.get(self.burner, 0),
            "timer_status": self.controller.timer_status.get(self.burner, "idle"),
        }

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)
