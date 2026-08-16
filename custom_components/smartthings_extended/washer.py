"""Samsung washer support for SmartThings Extended."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN, SMARTTHINGS_DOMAIN


class WasherController:
    """Prepared washer settings and SmartThings API access."""

    def __init__(
        self,
        client: Any,
        device_id: str,
        raw_status: dict[str, Any],
    ) -> None:
        self.client = client
        self.device_id = device_id
        self._listeners: list[Callable[[], None]] = []

        main = raw_status.get("components", {}).get("main", {})
        cycle_capability = main.get("samsungce.washerCycle", {})
        supported_cycles = (
            cycle_capability.get("supportedCycles", {}).get("value")
        )
        if not isinstance(supported_cycles, list) or not supported_cycles:
            raise HomeAssistantError(
                "Pralka nie zwróciła listy samsungce.washerCycle.supportedCycles."
            )

        self.cycles: list[dict[str, Any]] = [
            item
            for item in supported_cycles
            if isinstance(item, dict) and isinstance(item.get("cycle"), str)
        ]
        if not self.cycles:
            raise HomeAssistantError("Pralka nie zwróciła poprawnych programów.")

        current_course = (
            main.get("custom.supportedOptions", {})
            .get("course", {})
            .get("value")
        )
        cycle_ids = self.supported_programs()
        self.selected_program = (
            str(current_course) if str(current_course) in cycle_ids else cycle_ids[0]
        )

        self.water_temperature = ""
        self.spin_level = ""
        self.rinse_cycles = ""
        self.bubble_soak = "off"
        self._apply_program_defaults(self.selected_program)

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

    def _cycle_by_id(self) -> dict[str, dict[str, Any]]:
        return {item["cycle"]: item for item in self.cycles}

    def supported_programs(self) -> list[str]:
        return [item["cycle"] for item in self.cycles]

    def program_label(self, program: str) -> str:
        return f"Program {program}"

    def program_from_label(self, label: str) -> str:
        for program in self.supported_programs():
            if self.program_label(program) == label:
                return program
        raise HomeAssistantError(f"Nieznany program pralki: {label}")

    def program_options(self, program: str | None = None) -> dict[str, Any]:
        selected = program or self.selected_program
        item = self._cycle_by_id().get(selected)
        if item is None:
            raise HomeAssistantError(f"Program {selected} nie jest dostępny.")
        options = item.get("supportedOptions", {})
        return options if isinstance(options, dict) else {}

    def _option_values(self, option_name: str) -> list[str]:
        option = self.program_options().get(option_name)
        if not isinstance(option, dict):
            return []
        values = option.get("options", [])
        if not isinstance(values, list):
            return []
        return [str(value) for value in values if isinstance(value, (str, int))]

    def _option_default(self, option_name: str, fallback: str = "") -> str:
        option = self.program_options().get(option_name)
        if not isinstance(option, dict):
            return fallback
        default = option.get("default")
        if default is None:
            return fallback
        return str(default)

    def _apply_program_defaults(self, program: str) -> None:
        self.selected_program = program
        self.water_temperature = self._option_default(
            "waterTemperature", self.water_temperature
        )
        self.spin_level = self._option_default("spinLevel", self.spin_level)
        self.rinse_cycles = self._option_default("rinseCycle", self.rinse_cycles)
        self.bubble_soak = self._option_default("bubbleSoak", "off")

    def set_program(self, program: str) -> None:
        if program not in self.supported_programs():
            raise HomeAssistantError(f"Program {program} nie jest obsługiwany.")
        self._apply_program_defaults(program)
        self._notify()

    def temperature_values(self) -> list[str]:
        return self._option_values("waterTemperature")

    def spin_values(self) -> list[str]:
        return self._option_values("spinLevel")

    def rinse_values(self) -> list[str]:
        return self._option_values("rinseCycle")

    def bubble_values(self) -> list[str]:
        return self._option_values("bubbleSoak")

    def temperature_label(self, value: str) -> str:
        if value in {"cold", "tapCold"}:
            return "Zimna"
        if value == "none":
            return "Brak"
        if value.isdigit():
            return f"{value}°C"
        return value

    def temperature_from_label(self, label: str) -> str:
        for value in self.temperature_values():
            if self.temperature_label(value) == label:
                return value
        raise HomeAssistantError(f"Nieznana temperatura pralki: {label}")

    def spin_label(self, value: str) -> str:
        labels = {
            "rinseHold": "Zatrzymanie płukania",
            "noSpin": "Bez wirowania",
            "none": "Brak",
        }
        if value in labels:
            return labels[value]
        if value.isdigit():
            return f"{value} obr./min"
        return value

    def spin_from_label(self, label: str) -> str:
        for value in self.spin_values():
            if self.spin_label(value) == label:
                return value
        raise HomeAssistantError(f"Nieznany poziom wirowania: {label}")

    def bubble_label(self, value: str) -> str:
        return {"on": "Włączone", "off": "Wyłączone"}.get(value, value)

    def bubble_from_label(self, label: str) -> str:
        for value in self.bubble_values():
            if self.bubble_label(value) == label:
                return value
        raise HomeAssistantError(f"Nieznana opcja Bubble Soak: {label}")

    def set_temperature(self, value: str) -> None:
        if value not in self.temperature_values():
            raise HomeAssistantError(
                f"Temperatura {value} nie jest dostępna dla programu {self.selected_program}."
            )
        self.water_temperature = value
        self._notify()

    def set_spin(self, value: str) -> None:
        if value not in self.spin_values():
            raise HomeAssistantError(
                f"Wirowanie {value} nie jest dostępne dla programu {self.selected_program}."
            )
        self.spin_level = value
        self._notify()

    def set_rinse(self, value: str) -> None:
        if value not in self.rinse_values():
            raise HomeAssistantError(
                f"Liczba płukań {value} nie jest dostępna dla programu {self.selected_program}."
            )
        self.rinse_cycles = value
        self._notify()

    def set_bubble(self, value: str) -> None:
        if value not in self.bubble_values():
            raise HomeAssistantError(
                f"Bubble Soak nie jest dostępny dla programu {self.selected_program}."
            )
        self.bubble_soak = value
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

    async def send_settings(self) -> None:
        """Send prepared cycle and cycle-specific options without starting."""
        await self._command(
            "custom.supportedOptions",
            "setCourse",
            self.selected_program,
        )

        if self.temperature_values():
            await self._command(
                "custom.washerWaterTemperature",
                "setWasherWaterTemperature",
                self.water_temperature,
            )

        if self.spin_values():
            await self._command(
                "custom.washerSpinLevel",
                "setWasherSpinLevel",
                self.spin_level,
            )

        if self.rinse_values():
            await self._command(
                "custom.washerRinseCycles",
                "setWasherRinseCycles",
                self.rinse_cycles,
            )

        if self.bubble_values():
            await self._command(
                "samsungce.washerBubbleSoak",
                self.bubble_soak,
            )

    async def remote_control_enabled(self) -> bool:
        raw = await self.client.get_raw_device_status(self.device_id)
        value = (
            raw.get("components", {})
            .get("main", {})
            .get("remoteControlStatus", {})
            .get("remoteControlEnabled", {})
            .get("value")
        )
        return str(value).lower() == "true"

    async def _set_machine_state(self, state: str) -> None:
        """Set the washer state through the live washerOperatingState capability."""
        await self._command(
            "washerOperatingState",
            "setMachineState",
            state,
        )

    async def start(self) -> None:
        """Apply prepared settings and start the washer."""
        if not await self.remote_control_enabled():
            raise HomeAssistantError(
                "Smart Control pralki jest wyłączony. Włącz Smart Control na pralce przed Start."
            )
        await self.send_settings()
        await self._set_machine_state("run")

    async def pause(self) -> None:
        await self._set_machine_state("pause")

    async def resume(self) -> None:
        await self._set_machine_state("run")

    async def cancel(self) -> None:
        await self._set_machine_state("stop")


async def _auto_find_washer(
    hass: HomeAssistant,
) -> tuple[Any, str, dict[str, Any]]:
    """Find a Samsung washer exposing washer cycle metadata."""
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
            supported_cycles = (
                main.get("samsungce.washerCycle", {})
                .get("supportedCycles", {})
                .get("value")
            )
            machine_state = main.get("washerOperatingState")
            if (
                isinstance(supported_cycles, list)
                and bool(supported_cycles)
                and isinstance(machine_state, dict)
            ):
                return client, device_id, raw_status

    raise HomeAssistantError(
        "Nie znaleziono pralki SmartThings z samsungce.washerCycle.supportedCycles "
        "i washerOperatingState."
    )


async def async_get_washer_controller(
    hass: HomeAssistant,
) -> WasherController | None:
    """Return the shared washer controller, discovering it once."""
    data = hass.data.setdefault(DOMAIN, {})
    existing = data.get("washer")
    if isinstance(existing, WasherController):
        return existing
    if existing is False:
        return None

    lock = data.get("_washer_lock")
    if lock is None:
        lock = asyncio.Lock()
        data["_washer_lock"] = lock

    async with lock:
        existing = data.get("washer")
        if isinstance(existing, WasherController):
            return existing
        if existing is False:
            return None

        try:
            client, device_id, raw_status = await _auto_find_washer(hass)
            controller = WasherController(client, device_id, raw_status)
        except HomeAssistantError:
            data["washer"] = False
            return None

        data["washer"] = controller
        return controller
