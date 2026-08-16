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
from .cooktop import CooktopController, async_get_cooktop_controller
from .microwave import MicrowaveController, async_get_microwave_controller


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up prepared-setting numbers."""
    entities: list[NumberEntity] = []

    oven = hass.data[DOMAIN].get("oven")
    if isinstance(oven, OvenController):
        entities.extend(
            [
                OvenTemperatureNumber(
                    oven, "upper", "Piekarnik górny — temperatura"
                ),
                OvenTimeNumber(
                    oven, "upper", "Piekarnik górny — czas"
                ),
                OvenTemperatureNumber(
                    oven, "lower", "Piekarnik dolny — temperatura"
                ),
                OvenTimeNumber(
                    oven, "lower", "Piekarnik dolny — czas"
                ),
            ]
        )

    microwave = await async_get_microwave_controller(hass)
    if microwave is not None:
        entities.append(MicrowaveTimeNumber(microwave))

    cooktop = await async_get_cooktop_controller(hass)
    if cooktop is not None:
        entities.extend(
            [CooktopTimerNumber(cooktop, burner) for burner in cooktop.burners]
        )

    async_add_entities(entities)


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


class MicrowaveTimeNumber(NumberEntity):
    """Prepared microwave operation time in seconds."""

    _attr_should_poll = False
    _attr_name = "Mikrofalówka — czas"
    _attr_icon = "mdi:timer-outline"
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, controller: MicrowaveController) -> None:
        self.controller = controller
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_microwave_time"
        )

    @property
    def available(self) -> bool:
        return self.controller.has_operation_time()

    @property
    def native_value(self) -> float:
        return float(self.controller.time_seconds)

    @property
    def native_min_value(self) -> float:
        return float(self.controller.time_limits()[0])

    @property
    def native_max_value(self) -> float:
        return float(self.controller.time_limits()[1])

    @property
    def native_step(self) -> float:
        return float(self.controller.time_limits()[2])

    async def async_set_native_value(self, value: float) -> None:
        self.controller.set_time_seconds(value)

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)


class CooktopTimerNumber(NumberEntity):
    """Locally prepared countdown timer for one cooktop component."""

    _attr_should_poll = False
    _attr_icon = "mdi:timer-outline"
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = 1
    _attr_native_max_value = 1440
    _attr_native_step = 1

    def __init__(self, controller: CooktopController, burner: str) -> None:
        self.controller = controller
        self.burner = burner
        number = controller.burner_number(burner)
        self._attr_name = f"Płyta — Pole {number} — timer"
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_cooktop_{burner}_timer"
        )

    @property
    def native_value(self) -> float:
        return float(self.controller.timer_minutes[self.burner])

    async def async_set_native_value(self, value: float) -> None:
        self.controller.set_timer_minutes(self.burner, value)

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)
