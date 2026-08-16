"""Select entities for SmartThings Extended."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN, OvenController
from .dishwasher import DishwasherController, async_get_dishwasher_controller
from .fridge import FridgeController, async_get_fridge_controller
from .linked_device import smartthings_device_info
from .microwave import MicrowaveController, async_get_microwave_controller
from .washer import WasherController, async_get_washer_controller


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

    washer = await async_get_washer_controller(hass)
    if washer is not None:
        entities.extend(
            [
                WasherProgramSelect(washer),
                WasherTemperatureSelect(washer),
                WasherSpinSelect(washer),
                WasherRinseSelect(washer),
                WasherBubbleSelect(washer),
            ]
        )

    dishwasher = await async_get_dishwasher_controller(hass)
    if dishwasher is not None:
        entities.extend(
            [
                DishwasherCourseSelect(dishwasher),
                DishwasherZoneSelect(dishwasher),
                DishwasherSpeedBoosterSelect(dishwasher),
                DishwasherSanitizeSelect(dishwasher),
            ]
        )

    fridge = await async_get_fridge_controller(hass)
    if fridge is not None:
        entities.extend(
            [
                FridgeCoolSelectModeSelect(fridge),
                FridgeNightLightBrightnessSelect(fridge),
                FridgeDoorAlarmSoundSelect(fridge),
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
        self._attr_device_info = smartthings_device_info(controller.device_id)

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
        self._attr_device_info = smartthings_device_info(controller.device_id)

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


class WasherBaseSelect(SelectEntity):
    """Base select for locally prepared washer settings."""

    _attr_should_poll = False

    def __init__(self, controller: WasherController, suffix: str) -> None:
        self.controller = controller
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_washer_{suffix}"
        )
        self._attr_device_info = smartthings_device_info(controller.device_id)

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)


class WasherProgramSelect(WasherBaseSelect):
    _attr_name = "Pralka — program"
    _attr_icon = "mdi:washing-machine"

    def __init__(self, controller: WasherController) -> None:
        super().__init__(controller, "program")

    @property
    def options(self) -> list[str]:
        return [
            self.controller.program_label(value)
            for value in self.controller.supported_programs()
        ]

    @property
    def current_option(self) -> str:
        return self.controller.program_label(self.controller.selected_program)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_program(self.controller.program_from_label(option))


class WasherTemperatureSelect(WasherBaseSelect):
    _attr_name = "Pralka — temperatura"
    _attr_icon = "mdi:thermometer-water"

    def __init__(self, controller: WasherController) -> None:
        super().__init__(controller, "temperature")

    @property
    def available(self) -> bool:
        return bool(self.controller.temperature_values())

    @property
    def options(self) -> list[str]:
        return [
            self.controller.temperature_label(value)
            for value in self.controller.temperature_values()
        ]

    @property
    def current_option(self) -> str | None:
        if not self.controller.water_temperature:
            return None
        return self.controller.temperature_label(self.controller.water_temperature)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_temperature(
            self.controller.temperature_from_label(option)
        )


class WasherSpinSelect(WasherBaseSelect):
    _attr_name = "Pralka — wirowanie"
    _attr_icon = "mdi:rotate-right"

    def __init__(self, controller: WasherController) -> None:
        super().__init__(controller, "spin")

    @property
    def available(self) -> bool:
        return bool(self.controller.spin_values())

    @property
    def options(self) -> list[str]:
        return [
            self.controller.spin_label(value)
            for value in self.controller.spin_values()
        ]

    @property
    def current_option(self) -> str | None:
        if not self.controller.spin_level:
            return None
        return self.controller.spin_label(self.controller.spin_level)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_spin(self.controller.spin_from_label(option))


class WasherRinseSelect(WasherBaseSelect):
    _attr_name = "Pralka — płukania"
    _attr_icon = "mdi:waves"

    def __init__(self, controller: WasherController) -> None:
        super().__init__(controller, "rinse")

    @property
    def available(self) -> bool:
        return bool(self.controller.rinse_values())

    @property
    def options(self) -> list[str]:
        return self.controller.rinse_values()

    @property
    def current_option(self) -> str | None:
        return self.controller.rinse_cycles or None

    async def async_select_option(self, option: str) -> None:
        self.controller.set_rinse(option)


class WasherBubbleSelect(WasherBaseSelect):
    _attr_name = "Pralka — Bubble Soak"
    _attr_icon = "mdi:bubbles"

    def __init__(self, controller: WasherController) -> None:
        super().__init__(controller, "bubble_soak")

    @property
    def available(self) -> bool:
        return bool(self.controller.bubble_values())

    @property
    def options(self) -> list[str]:
        return [
            self.controller.bubble_label(value)
            for value in self.controller.bubble_values()
        ]

    @property
    def current_option(self) -> str | None:
        if not self.controller.bubble_values():
            return None
        return self.controller.bubble_label(self.controller.bubble_soak)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_bubble(self.controller.bubble_from_label(option))


class DishwasherBaseSelect(SelectEntity):
    """Base select for locally prepared dishwasher settings."""

    _attr_should_poll = False

    def __init__(self, controller: DishwasherController, suffix: str) -> None:
        self.controller = controller
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_dishwasher_{suffix}"
        )
        self._attr_device_info = smartthings_device_info(controller.device_id)

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)


class DishwasherCourseSelect(DishwasherBaseSelect):
    _attr_name = "Zmywarka — program"
    _attr_icon = "mdi:dishwasher"

    def __init__(self, controller: DishwasherController) -> None:
        super().__init__(controller, "course")

    @property
    def options(self) -> list[str]:
        return [
            self.controller.course_label(value)
            for value in self.controller.supported_courses()
        ]

    @property
    def current_option(self) -> str:
        return self.controller.course_label(self.controller.selected_course)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_course(self.controller.course_from_label(option))


class DishwasherZoneSelect(DishwasherBaseSelect):
    _attr_name = "Zmywarka — strefa"
    _attr_icon = "mdi:dishwasher"

    def __init__(self, controller: DishwasherController) -> None:
        super().__init__(controller, "zone")

    @property
    def available(self) -> bool:
        return bool(self.controller.zone_values())

    @property
    def options(self) -> list[str]:
        return [
            self.controller.zone_label(value)
            for value in self.controller.zone_values()
        ]

    @property
    def current_option(self) -> str | None:
        if not self.controller.selected_zone:
            return None
        return self.controller.zone_label(self.controller.selected_zone)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_zone(self.controller.zone_from_label(option))


class DishwasherSpeedBoosterSelect(DishwasherBaseSelect):
    _attr_name = "Zmywarka — Speed Booster"
    _attr_icon = "mdi:speedometer"

    def __init__(self, controller: DishwasherController) -> None:
        super().__init__(controller, "speed_booster")

    @property
    def available(self) -> bool:
        return bool(self.controller.speed_booster_values())

    @property
    def options(self) -> list[str]:
        return [
            self.controller.bool_label(value)
            for value in self.controller.speed_booster_values()
        ]

    @property
    def current_option(self) -> str | None:
        if not self.controller.speed_booster_values():
            return None
        return self.controller.bool_label(self.controller.speed_booster)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_speed_booster(
            self.controller.bool_from_label(option)
        )


class DishwasherSanitizeSelect(DishwasherBaseSelect):
    _attr_name = "Zmywarka — Sanitize"
    _attr_icon = "mdi:shield-check"

    def __init__(self, controller: DishwasherController) -> None:
        super().__init__(controller, "sanitize")

    @property
    def available(self) -> bool:
        return bool(self.controller.sanitize_values())

    @property
    def options(self) -> list[str]:
        return [
            self.controller.bool_label(value)
            for value in self.controller.sanitize_values()
        ]

    @property
    def current_option(self) -> str | None:
        if not self.controller.sanitize_values():
            return None
        return self.controller.bool_label(self.controller.sanitize)

    async def async_select_option(self, option: str) -> None:
        self.controller.set_sanitize(self.controller.bool_from_label(option))


class FridgeBaseSelect(SelectEntity):
    """Base select for refrigerator controls."""

    _attr_should_poll = False

    def __init__(self, controller: FridgeController, suffix: str) -> None:
        self.controller = controller
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_fridge_{suffix}"
        )
        self._attr_device_info = smartthings_device_info(controller.device_id)

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)


class FridgeCoolSelectModeSelect(FridgeBaseSelect):
    _attr_name = "Lodówka — CoolSelect+"
    _attr_icon = "mdi:fridge-bottom"

    def __init__(self, controller: FridgeController) -> None:
        super().__init__(controller, "coolselect_mode")

    @property
    def options(self) -> list[str]:
        return [
            self.controller.coolselect_label(value)
            for value in self.controller.coolselect_modes
        ]

    @property
    def current_option(self) -> str:
        return self.controller.coolselect_label(self.controller.coolselect_mode)

    async def async_select_option(self, option: str) -> None:
        value = self.controller.coolselect_from_label(option)
        await self.controller.set_coolselect_mode(value)


class FridgeNightLightBrightnessSelect(FridgeBaseSelect):
    _attr_name = "Lodówka — jasność lampki nocnej"
    _attr_icon = "mdi:brightness-6"

    def __init__(self, controller: FridgeController) -> None:
        super().__init__(controller, "night_light_brightness")

    @property
    def available(self) -> bool:
        return bool(self.controller.night_light_brightness_levels)

    @property
    def options(self) -> list[str]:
        return [
            self.controller.brightness_label(value)
            for value in self.controller.night_light_brightness_levels
        ]

    @property
    def current_option(self) -> str | None:
        if not self.controller.night_light_brightness:
            return None
        return self.controller.brightness_label(
            self.controller.night_light_brightness
        )

    async def async_select_option(self, option: str) -> None:
        value = self.controller.brightness_from_label(option)
        await self.controller.set_night_light_brightness(value)


class FridgeDoorAlarmSoundSelect(FridgeBaseSelect):
    _attr_name = "Lodówka — dźwięk alarmu drzwi"
    _attr_icon = "mdi:bell-ring"

    def __init__(self, controller: FridgeController) -> None:
        super().__init__(controller, "door_alarm_sound")

    @property
    def available(self) -> bool:
        return bool(self.controller.alarm_sounds)

    @property
    def options(self) -> list[str]:
        return [
            self.controller.alarm_sound_label(value)
            for value in self.controller.alarm_sounds
        ]

    @property
    def current_option(self) -> str | None:
        if not self.controller.alarm_sounds:
            return None
        return self.controller.alarm_sound_label(self.controller.alarm_sound)

    async def async_select_option(self, option: str) -> None:
        value = self.controller.alarm_sound_from_label(option)
        await self.controller.set_alarm_sound(value)
