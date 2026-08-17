"""Samsung refrigerator support for SmartThings Extended."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN, SMARTTHINGS_DOMAIN

COOLSELECT_COMPONENT = "cvroom"

COOLSELECT_LABELS = {
    "CV_TTYPE_RF9000A_FREEZE": "Zamrażanie",
    "CV_TTYPE_RF9000A_SOFTFREEZE": "Soft Freeze",
    "CV_TTYPE_RF9000A_MEAT_FISH": "Mięso i ryby",
    "CV_TTYPE_RF9000A_FRUIT_VEGGIES": "Owoce i warzywa",
    "CV_TTYPE_RF9000A_BEVERAGE": "Napoje",
}

BRIGHTNESS_LABELS = {
    "low": "Niska",
    "medium": "Średnia",
    "high": "Wysoka",
}


class FridgeController:
    """Samsung refrigerator extended controls."""

    def __init__(
        self,
        client: Any,
        device_id: str,
        raw_status: dict[str, Any],
    ) -> None:
        self.client = client
        self.device_id = device_id
        self._listeners: list[Callable[[], None]] = []
        self._remove_device_listener: Callable[[], None] | None = None

        components = raw_status.get("components", {})
        main = components.get("main", {})
        cvroom = components.get(COOLSELECT_COMPONENT, {})

        mode_capability = cvroom.get("custom.fridgeMode", {})
        modes = mode_capability.get("supportedFullFridgeModes", {}).get("value")
        if not isinstance(modes, list) or not modes:
            raise HomeAssistantError(
                "Lodówka nie zwróciła trybów CoolSelect+ w komponencie cvroom."
            )
        self.coolselect_modes = [
            str(value) for value in modes if isinstance(value, str)
        ]
        current_mode = mode_capability.get("fridgeMode", {}).get("value")
        self.coolselect_mode = (
            str(current_mode)
            if isinstance(current_mode, str) and current_mode in self.coolselect_modes
            else self.coolselect_modes[0]
        )

        auto_fill = main.get("samsungce.autoFillPitcher", {})
        auto_fill_value = auto_fill.get("autoFillPitcher", {}).get("value")
        self.auto_fill_supported = auto_fill_value in ("on", "off")
        self.auto_fill = auto_fill_value == "on"

        icemaker_night = main.get("samsungce.icemakerNightMode", {})
        night_mode_value = icemaker_night.get("icemakerNightMode", {}).get("value")
        self.icemaker_night_mode_supported = night_mode_value in ("on", "off")
        self.icemaker_night_mode = night_mode_value == "on"
        self.icemaker_time_setting_supported = bool(
            icemaker_night.get("timeSettingSupported", {}).get("value")
        )
        self.icemaker_night_start = icemaker_night.get("startTime", {}).get("value")
        self.icemaker_night_end = icemaker_night.get("endTime", {}).get("value")

        lighting = main.get("samsungce.fridgeInteriorLighting", {})
        night_light_values = lighting.get("supportedNightLight", {}).get("value")
        self.night_light_supported = (
            isinstance(night_light_values, list)
            and "on" in night_light_values
            and "off" in night_light_values
        )
        night_light_value = lighting.get("nightLight", {}).get("value")
        self.night_light = night_light_value == "on"

        brightness_values = lighting.get(
            "supportedNightLightBrightnessLevels", {}
        ).get("value")
        self.night_light_brightness_levels = (
            [str(value) for value in brightness_values if isinstance(value, str)]
            if isinstance(brightness_values, list)
            else []
        )
        current_brightness = lighting.get("nightLightBrightnessLevel", {}).get(
            "value"
        )
        self.night_light_brightness = (
            str(current_brightness)
            if isinstance(current_brightness, str)
            and current_brightness in self.night_light_brightness_levels
            else (
                self.night_light_brightness_levels[0]
                if self.night_light_brightness_levels
                else ""
            )
        )

        interior_brightness_values = lighting.get(
            "supportedBrightnessesLevels", {}
        ).get("value")
        self.brightness_levels = (
            [
                str(value)
                for value in interior_brightness_values
                if isinstance(value, str)
            ]
            if isinstance(interior_brightness_values, list)
            else []
        )
        current_interior_brightness = lighting.get("brightnessLevel", {}).get(
            "value"
        )
        self.brightness_level = (
            str(current_interior_brightness)
            if isinstance(current_interior_brightness, str)
            and current_interior_brightness in self.brightness_levels
            else (self.brightness_levels[0] if self.brightness_levels else "")
        )

        brighten_value = lighting.get("brightenGradually", {}).get("value")
        self.brighten_gradually_supported = brighten_value in ("on", "off")
        self.brighten_gradually = brighten_value == "on"

        alarm = main.get("samsungce.doorAlarm", {})
        sounds = alarm.get("supportedAlarmSounds", {}).get("value")
        self.alarm_sounds = (
            [int(value) for value in sounds if isinstance(value, int)]
            if isinstance(sounds, list)
            else []
        )
        current_sound = alarm.get("alarmSound", {}).get("value")
        self.alarm_sound = (
            int(current_sound)
            if isinstance(current_sound, int) and current_sound in self.alarm_sounds
            else (self.alarm_sounds[0] if self.alarm_sounds else 0)
        )

        # The doorAlarm attribute is advertised with on/off commands but this
        # refrigerator reports its current value as null until it changes.
        door_alarm_value = alarm.get("doorAlarm", {}).get("value")
        self.door_alarm_supported = bool(alarm)
        self.door_alarm: bool | None = (
            door_alarm_value == "on" if door_alarm_value in ("on", "off") else None
        )

        add_listener = getattr(client, "add_device_event_listener", None)
        if callable(add_listener):
            self._remove_device_listener = add_listener(
                device_id, self._handle_device_event
            )

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to local and SmartThings state changes."""
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _handle_device_event(self, event: Any) -> None:  # noqa: PLR0912
        """Update extended refrigerator state from live SmartThings events."""
        component = str(getattr(event, "component_id", ""))
        capability = str(getattr(event, "capability", ""))
        attribute = str(getattr(event, "attribute", ""))
        value = getattr(event, "value", None)
        changed = False

        if component == COOLSELECT_COMPONENT and capability == "custom.fridgeMode":
            if (
                attribute == "fridgeMode"
                and isinstance(value, str)
                and value in self.coolselect_modes
                and value != self.coolselect_mode
            ):
                self.coolselect_mode = value
                changed = True

        elif component == "main" and capability == "samsungce.autoFillPitcher":
            if attribute == "autoFillPitcher" and value in ("on", "off"):
                enabled = value == "on"
                if enabled != self.auto_fill:
                    self.auto_fill = enabled
                    changed = True

        elif component == "main" and capability == "samsungce.icemakerNightMode":
            if attribute == "icemakerNightMode" and value in ("on", "off"):
                enabled = value == "on"
                if enabled != self.icemaker_night_mode:
                    self.icemaker_night_mode = enabled
                    changed = True
            elif attribute == "startTime" and value != self.icemaker_night_start:
                self.icemaker_night_start = value
                changed = True
            elif attribute == "endTime" and value != self.icemaker_night_end:
                self.icemaker_night_end = value
                changed = True
            elif attribute == "timeSettingSupported":
                supported = bool(value)
                if supported != self.icemaker_time_setting_supported:
                    self.icemaker_time_setting_supported = supported
                    changed = True

        elif component == "main" and capability == "samsungce.fridgeInteriorLighting":
            if attribute == "nightLight" and value in ("on", "off"):
                enabled = value == "on"
                if enabled != self.night_light:
                    self.night_light = enabled
                    changed = True
            elif (
                attribute == "nightLightBrightnessLevel"
                and isinstance(value, str)
                and value in self.night_light_brightness_levels
                and value != self.night_light_brightness
            ):
                self.night_light_brightness = value
                changed = True
            elif (
                attribute == "brightnessLevel"
                and isinstance(value, str)
                and value in self.brightness_levels
                and value != self.brightness_level
            ):
                self.brightness_level = value
                changed = True
            elif attribute == "brightenGradually" and value in ("on", "off"):
                enabled = value == "on"
                if enabled != self.brighten_gradually:
                    self.brighten_gradually = enabled
                    changed = True

        elif component == "main" and capability == "samsungce.doorAlarm":
            if (
                attribute == "alarmSound"
                and isinstance(value, int)
                and value in self.alarm_sounds
                and value != self.alarm_sound
            ):
                self.alarm_sound = value
                changed = True
            elif attribute == "doorAlarm" and value in ("on", "off"):
                enabled = value == "on"
                if enabled != self.door_alarm:
                    self.door_alarm = enabled
                    changed = True

        if changed:
            self._notify()

    async def _command(
        self,
        component: str,
        capability: str,
        command: str,
        argument: Any | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {}
        if argument is not None:
            kwargs["argument"] = argument
        await self.client.execute_device_command(
            self.device_id,
            capability,
            command,
            component,
            **kwargs,
        )

    def coolselect_label(self, value: str) -> str:
        return COOLSELECT_LABELS.get(value, value)

    def coolselect_from_label(self, label: str) -> str:
        for value in self.coolselect_modes:
            if self.coolselect_label(value) == label:
                return value
        raise HomeAssistantError(f"Nieznany tryb CoolSelect+: {label}")

    async def set_coolselect_mode(self, value: str) -> None:
        if value not in self.coolselect_modes:
            raise HomeAssistantError(f"Tryb CoolSelect+ {value} nie jest obsługiwany.")
        await self._command(
            COOLSELECT_COMPONENT,
            "custom.fridgeMode",
            "setFridgeMode",
            value,
        )
        self.coolselect_mode = value
        self._notify()

    async def set_auto_fill(self, enabled: bool) -> None:
        if not self.auto_fill_supported:
            raise HomeAssistantError("AutoFill Pitcher nie jest dostępny.")
        await self._command(
            "main",
            "samsungce.autoFillPitcher",
            "on" if enabled else "off",
        )
        self.auto_fill = enabled
        self._notify()

    async def set_icemaker_night_mode(self, enabled: bool) -> None:
        if not self.icemaker_night_mode_supported:
            raise HomeAssistantError("Tryb nocny kostkarki nie jest dostępny.")
        await self._command(
            "main",
            "samsungce.icemakerNightMode",
            "on" if enabled else "off",
        )
        self.icemaker_night_mode = enabled
        self._notify()

    async def set_night_light(self, enabled: bool) -> None:
        if not self.night_light_supported:
            raise HomeAssistantError("Lampka nocna lodówki nie jest dostępna.")
        value = "on" if enabled else "off"
        await self._command(
            "main",
            "samsungce.fridgeInteriorLighting",
            "setNightLight",
            value,
        )
        self.night_light = enabled
        self._notify()

    def brightness_label(self, value: str) -> str:
        return BRIGHTNESS_LABELS.get(value, value)

    def brightness_from_label(
        self, label: str, values: list[str] | None = None
    ) -> str:
        candidates = (
            values if values is not None else self.night_light_brightness_levels
        )
        for value in candidates:
            if self.brightness_label(value) == label:
                return value
        raise HomeAssistantError(f"Nieznana jasność: {label}")

    async def set_night_light_brightness(self, value: str) -> None:
        if value not in self.night_light_brightness_levels:
            raise HomeAssistantError(f"Jasność {value} nie jest obsługiwana.")
        await self._command(
            "main",
            "samsungce.fridgeInteriorLighting",
            "setNightLightBrightnessLevel",
            value,
        )
        self.night_light_brightness = value
        self._notify()

    async def set_brightness_level(self, value: str) -> None:
        if value not in self.brightness_levels:
            raise HomeAssistantError(f"Jasność {value} nie jest obsługiwana.")
        await self._command(
            "main",
            "samsungce.fridgeInteriorLighting",
            "setBrightnessLevel",
            value,
        )
        self.brightness_level = value
        self._notify()

    async def set_brighten_gradually(self, enabled: bool) -> None:
        if not self.brighten_gradually_supported:
            raise HomeAssistantError("Powolne rozjaśnianie nie jest dostępne.")
        await self._command(
            "main",
            "samsungce.fridgeInteriorLighting",
            "setBrightenGradually",
            "on" if enabled else "off",
        )
        self.brighten_gradually = enabled
        self._notify()

    def alarm_sound_label(self, value: int) -> str:
        return f"Dźwięk {value}"

    def alarm_sound_from_label(self, label: str) -> int:
        for value in self.alarm_sounds:
            if self.alarm_sound_label(value) == label:
                return value
        raise HomeAssistantError(f"Nieznany dźwięk alarmu drzwi: {label}")

    async def set_alarm_sound(self, value: int) -> None:
        if value not in self.alarm_sounds:
            raise HomeAssistantError(f"Dźwięk alarmu {value} nie jest obsługiwany.")
        await self._command(
            "main",
            "samsungce.doorAlarm",
            "setAlarmSound",
            value,
        )
        self.alarm_sound = value
        self._notify()

    async def set_door_alarm(self, enabled: bool) -> None:
        if not self.door_alarm_supported:
            raise HomeAssistantError("Alarm drzwi nie jest dostępny.")
        await self._command(
            "main",
            "samsungce.doorAlarm",
            "on" if enabled else "off",
        )
        self.door_alarm = enabled
        self._notify()

    async def set_icemaker_night_schedule(self, start: str, end: str) -> None:
        if not self.icemaker_time_setting_supported:
            raise HomeAssistantError(
                "Lodówka nie obsługuje ustawiania godzin trybu nocnego kostkarki."
            )
        await self._command(
            "main",
            "samsungce.icemakerNightMode",
            "setSchedule",
            [start, end],
        )
        self.icemaker_night_start = start
        self.icemaker_night_end = end
        self._notify()


async def _auto_find_fridge(
    hass: HomeAssistant,
) -> tuple[Any, str, dict[str, Any]]:
    """Find a Samsung refrigerator with a usable CoolSelect+ component."""
    for entry in hass.config_entries.async_entries(SMARTTHINGS_DOMAIN):
        runtime_data = getattr(entry, "runtime_data", None)
        client = getattr(runtime_data, "client", None)
        devices = getattr(runtime_data, "devices", None)
        if client is None or devices is None:
            continue

        for device_id in devices:
            try:
                raw_status = await client.get_raw_device_status(device_id)
            except Exception:  # noqa: BLE001
                continue

            components = raw_status.get("components", {})
            main = components.get("main", {})
            cvroom = components.get(COOLSELECT_COMPONENT, {})
            modes = (
                cvroom.get("custom.fridgeMode", {})
                .get("supportedFullFridgeModes", {})
                .get("value")
            )
            auto_fill = main.get("samsungce.autoFillPitcher")
            if isinstance(modes, list) and modes and isinstance(auto_fill, dict):
                return client, device_id, raw_status

    raise HomeAssistantError(
        "Nie znaleziono lodówki SmartThings z komponentem CoolSelect+ cvroom."
    )


async def async_get_fridge_controller(
    hass: HomeAssistant,
) -> FridgeController | None:
    """Return the shared refrigerator controller, discovering it once."""
    data = hass.data.setdefault(DOMAIN, {})
    existing = data.get("fridge")
    if isinstance(existing, FridgeController):
        return existing
    if existing is False:
        return None

    lock = data.get("_fridge_lock")
    if lock is None:
        lock = asyncio.Lock()
        data["_fridge_lock"] = lock

    async with lock:
        existing = data.get("fridge")
        if isinstance(existing, FridgeController):
            return existing
        if existing is False:
            return None

        try:
            client, device_id, raw_status = await _auto_find_fridge(hass)
            controller = FridgeController(client, device_id, raw_status)
        except HomeAssistantError:
            data["fridge"] = False
            return None

        data["fridge"] = controller
        return controller
