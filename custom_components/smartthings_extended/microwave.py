"""Samsung microwave support for SmartThings Extended."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN, SMARTTHINGS_DOMAIN

MODE_ORDER = [
    "MicroWave",
    "Deodorization",
    "KeepWarm",
    "SteamClean",
]

MODE_LABELS = {
    "MicroWave": "Mikrofale",
    "Deodorization": "Usuwanie zapachów",
    "KeepWarm": "Utrzymuj ciepło",
    "SteamClean": "Czyszczenie parowe",
}


def _time_to_seconds(value: str) -> int:
    """Convert SmartThings HH:MM:SS to seconds."""
    try:
        hours, minutes, seconds = (int(part) for part in value.split(":"))
    except (TypeError, ValueError):
        return 30
    return max(1, hours * 3600 + minutes * 60 + seconds)


def _seconds_to_time(seconds: int) -> str:
    """Convert seconds to SmartThings HH:MM:SS."""
    seconds = max(1, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class MicrowaveController:
    """Prepared settings and SmartThings API access for a microwave."""

    def __init__(
        self,
        client: Any,
        device_id: str,
        raw_status: dict[str, Any],
    ) -> None:
        self.client = client
        self.device_id = device_id
        self._listeners: list[Callable[[], None]] = []

        try:
            specification = (
                raw_status["components"]["main"]
                ["samsungce.kitchenModeSpecification"]
                ["specification"]["value"]
            )
            self.specification: list[dict[str, Any]] = specification["single"]
        except (KeyError, TypeError) as err:
            raise HomeAssistantError(
                "Mikrofalówka nie zwróciła poprawnego kitchenModeSpecification.single."
            ) from err

        modes = self.supported_modes()
        if not modes:
            raise HomeAssistantError(
                "Brak obsługiwanych trybów ręcznych dla mikrofalówki."
            )

        self.selected_mode = "MicroWave" if "MicroWave" in modes else modes[0]
        self.power_level = "900W"
        self.time_seconds = 30
        self._apply_mode_defaults(self.selected_mode)

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to local prepared-setting changes."""
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _spec_by_mode(self) -> dict[str, dict[str, Any]]:
        return {
            item["mode"]: item
            for item in self.specification
            if isinstance(item, dict) and "mode" in item
        }

    def supported_modes(self) -> list[str]:
        """Return microwave modes that advertise direct set support."""
        specs = self._spec_by_mode()
        result: list[str] = []
        for mode in MODE_ORDER:
            item = specs.get(mode)
            if item and "set" in item.get("supportedOperations", []):
                result.append(mode)
        return result

    def mode_label(self, mode: str) -> str:
        return MODE_LABELS.get(mode, mode)

    def mode_from_label(self, label: str) -> str:
        for mode in self.supported_modes():
            if self.mode_label(mode) == label:
                return mode
        raise HomeAssistantError(f"Nieznany tryb mikrofalówki: {label}")

    def mode_options(self, mode: str | None = None) -> dict[str, Any]:
        selected = mode or self.selected_mode
        item = self._spec_by_mode().get(selected)
        if item is None:
            raise HomeAssistantError(
                f"Tryb {selected} nie jest dostępny dla mikrofalówki."
            )
        return item.get("supportedOptions", {})

    def _apply_mode_defaults(self, mode: str) -> None:
        options = self.mode_options(mode)

        operation_time = options.get("operationTime")
        if isinstance(operation_time, dict):
            self.time_seconds = _time_to_seconds(
                operation_time.get("default", "00:00:30")
            )

        power = options.get("powerLevel")
        if isinstance(power, dict):
            values = power.get("supportedValues", [])
            default = power.get("default")
            if default in values:
                self.power_level = default
            elif values:
                self.power_level = values[0]

    def set_mode(self, mode: str) -> None:
        if mode not in self.supported_modes():
            raise HomeAssistantError(
                f"Tryb {mode} nie jest obsługiwany przez mikrofalówkę."
            )
        self.selected_mode = mode
        self._apply_mode_defaults(mode)
        self._notify()

    def power_levels(self) -> list[str]:
        power = self.mode_options().get("powerLevel")
        if not isinstance(power, dict):
            return []
        return [
            str(value)
            for value in power.get("supportedValues", [])
            if isinstance(value, str)
        ]

    def set_power_level(self, value: str) -> None:
        if value not in self.power_levels():
            raise HomeAssistantError(
                f"Moc {value} nie jest dostępna dla trybu {self.selected_mode}."
            )
        self.power_level = value
        self._notify()

    def has_operation_time(self) -> bool:
        return isinstance(self.mode_options().get("operationTime"), dict)

    def time_limits(self) -> tuple[int, int, int]:
        operation_time = self.mode_options().get("operationTime")
        if not isinstance(operation_time, dict):
            return (10, 5400, 10)
        return (
            _time_to_seconds(operation_time.get("min", "00:00:10")),
            _time_to_seconds(operation_time.get("max", "01:30:00")),
            max(
                1,
                _time_to_seconds(
                    operation_time.get("resolution", "00:00:10")
                ),
            ),
        )

    def set_time_seconds(self, value: float) -> None:
        if not self.has_operation_time():
            raise HomeAssistantError(
                f"Tryb {self.selected_mode} nie obsługuje ustawiania czasu."
            )

        minimum, maximum, step = self.time_limits()
        value_int = int(round(value))
        if not minimum <= value_int <= maximum:
            raise HomeAssistantError(
                f"Czas {value_int} s jest poza zakresem {minimum}–{maximum} s."
            )

        aligned = minimum + round((value_int - minimum) / step) * step
        self.time_seconds = int(min(max(aligned, minimum), maximum))
        self._notify()

    async def _command(
        self,
        capability: str,
        command: str,
        argument: Any | None = None,
    ) -> None:
        await self.client.execute_device_command(
            self.device_id,
            capability,
            command,
            "main",
            argument=argument,
        )

    async def _batch_commands(self, commands: list[dict[str, Any]]) -> None:
        """Send multiple SmartThings commands in one device command request.

        pysmartthings currently exposes only execute_device_command(), which
        always posts a single command. Samsung microwave power is accepted by
        the tested appliance only when mode, power and time are sent together,
        so use the same authenticated pysmartthings POST helper for the batch.
        """
        post = getattr(self.client, "_post", None)
        if post is None:
            raise HomeAssistantError(
                "Ta wersja pysmartthings nie obsługuje wymaganego batch requestu."
            )
        await post(
            f"v1/devices/{self.device_id}/commands",
            data={"commands": commands},
        )

    async def send_settings(self) -> None:
        """Send prepared mode and options together without starting."""
        commands: list[dict[str, Any]] = [
            {
                "component": "main",
                "capability": "samsungce.ovenMode",
                "command": "setOvenMode",
                "arguments": [self.selected_mode],
            }
        ]

        if self.power_levels():
            commands.append(
                {
                    "component": "main",
                    "capability": "samsungce.microwavePower",
                    "command": "setPowerLevel",
                    "arguments": [self.power_level],
                }
            )

        if self.has_operation_time():
            commands.append(
                {
                    "component": "main",
                    "capability": "samsungce.ovenOperatingState",
                    "command": "setOperationTime",
                    "arguments": [_seconds_to_time(self.time_seconds)],
                }
            )

        await self._batch_commands(commands)

    async def _door_is_closed(self) -> bool | None:
        raw = await self.client.get_raw_device_status(self.device_id)
        value = (
            raw.get("components", {})
            .get("main", {})
            .get("samsungce.doorState", {})
            .get("doorState", {})
            .get("value")
        )
        if value is None:
            return None
        return str(value).lower() == "closed"

    async def start(self) -> None:
        """Apply prepared settings and start the microwave."""
        door_closed = await self._door_is_closed()
        if door_closed is False:
            raise HomeAssistantError(
                "Drzwi mikrofalówki są otwarte. Zamknij je przed uruchomieniem."
            )

        await self.send_settings()
        await self._command("samsungce.ovenOperatingState", "start")

    async def pause(self) -> None:
        await self._command("samsungce.ovenOperatingState", "pause")

    async def stop(self) -> None:
        await self._command("samsungce.ovenOperatingState", "stop")


async def _auto_find_microwave(
    hass: HomeAssistant,
) -> tuple[Any, str, dict[str, Any]]:
    """Find a microwave from its single-cavity mode specification."""
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

            main = raw_status.get("components", {}).get("main", {})
            specification = (
                main.get("samsungce.kitchenModeSpecification", {})
                .get("specification", {})
                .get("value")
            )
            if not isinstance(specification, dict):
                continue

            single = specification.get("single")
            if not isinstance(single, list):
                continue

            for item in single:
                if not isinstance(item, dict) or item.get("mode") != "MicroWave":
                    continue
                operations = item.get("supportedOperations", [])
                options = item.get("supportedOptions", {})
                if (
                    "set" in operations
                    and isinstance(options, dict)
                    and "powerLevel" in options
                    and "operationTime" in options
                ):
                    return client, device_id, raw_status

    raise HomeAssistantError(
        "Nie znaleziono mikrofalówki SmartThings z trybem MicroWave w "
        "samsungce.kitchenModeSpecification.single."
    )


async def async_get_microwave_controller(
    hass: HomeAssistant,
) -> MicrowaveController | None:
    """Return the shared microwave controller, discovering it once."""
    data = hass.data.setdefault(DOMAIN, {})
    existing = data.get("microwave")
    if isinstance(existing, MicrowaveController):
        return existing
    if existing is False:
        return None

    lock = data.get("_microwave_lock")
    if lock is None:
        lock = asyncio.Lock()
        data["_microwave_lock"] = lock

    async with lock:
        existing = data.get("microwave")
        if isinstance(existing, MicrowaveController):
            return existing
        if existing is False:
            return None

        try:
            client, device_id, raw_status = await _auto_find_microwave(hass)
            controller = MicrowaveController(client, device_id, raw_status)
        except HomeAssistantError:
            data["microwave"] = False
            return None

        data["microwave"] = controller
        return controller
