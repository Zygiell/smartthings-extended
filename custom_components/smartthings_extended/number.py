"""Number entities for SmartThings Extended."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
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
    """Set up oven prepared-setting numbers."""
    controller: OvenController = hass.data[DOMAIN]["oven"]
    async_add_entities(
        [
            OvenTemperatureNumber(
                controller, "upper", "Piekarnik górny — temperatura"
            ),
            OvenTimeNumber(
                controller, "upper", "Piekarnik górny — czas"
            ),
            OvenTemperatureNumber(
                controller, "lower", "Piekarnik dolny — temperatura"
            ),
            OvenTimeNumber(
                controller, "lower", "Piekarnik dolny — czas"
            ),
        ]
    )


class OvenBaseNumber(NumberEntity):
    _attr_should_poll = False

    def __init__(
        self, controller: OvenController, cavity: str, name: str, suffix: str
    ) -> None:
        self.controller = controller
        self.cavity = cavity
        self._attr_name = name
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_{cavity}_{suffix}"
        )

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)


class OvenTemperatureNumber(OvenBaseNumber):
    _attr_icon = "mdi:thermometer"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self, controller: OvenController, cavity: str, name: str
    ) -> None:
        super().__init__(controller, cavity, name, "temperature")

    @property
    def native_value(self) -> float:
        return self.controller.temperature[self.cavity]

    @property
    def native_min_value(self) -> float:
        return self.controller.temperature_limits(self.cavity)[0]

    @property
    def native_max_value(self) -> float:
        return self.controller.temperature_limits(self.cavity)[1]

    @property
    def native_step(self) -> float:
        return self.controller.temperature_limits(self.cavity)[2]

    async def async_set_native_value(self, value: float) -> None:
        self.controller.set_temperature(self.cavity, value)


class OvenTimeNumber(OvenBaseNumber):
    _attr_icon = "mdi:timer-outline"
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(
        self, controller: OvenController, cavity: str, name: str
    ) -> None:
        super().__init__(controller, cavity, name, "time")

    @property
    def native_value(self) -> float:
        return float(self.controller.time_minutes[self.cavity])

    @property
    def native_min_value(self) -> float:
        return float(self.controller.time_limits(self.cavity)[0])

    @property
    def native_max_value(self) -> float:
        return float(self.controller.time_limits(self.cavity)[1])

    @property
    def native_step(self) -> float:
        return float(self.controller.time_limits(self.cavity)[2])

    async def async_set_native_value(self, value: float) -> None:
        self.controller.set_time_minutes(self.cavity, value)
