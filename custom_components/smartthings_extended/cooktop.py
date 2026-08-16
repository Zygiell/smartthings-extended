"""Samsung cooktop support for SmartThings Extended."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN, SMARTTHINGS_DOMAIN

TIMER_CAPABILITY = "samsungce.countDownTimer"
HEATING_CAPABILITY = "samsungce.cooktopHeatingPower"
RESIDUAL_HEAT_CAPABILITY = "samsungce.surfaceResidualHeat"
KIDS_LOCK_CAPABILITY = "samsungce.kidsLockControl"

RESIDUAL_HEAT_LABELS = {
    "normal": "Normalna",
    "low": "Ciepła",
    "high": "Gorąca",
    "veryHigh": "Bardzo gorąca",
}

HEATING_MODE_LABELS = {
    "off": "Wyłączone",
    "onOff": "Włączone/Wyłączone",
    "manual": "Ręczny",
    "boost": "Boost",
    "keepWarm": "Podtrzymywanie ciepła",
    "quickPreheat": "Szybkie nagrzewanie",
    "defrost": "Rozmrażanie",
    "melt": "Roztapianie",
    "simmer": "Duszenie",
}


class CooktopController:
    """Cooktop read state, timer controls and child lock."""

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
        self.burners = sorted(
            component_id
            for component_id, component in components.items()
            if component_id.startswith("burner-")
            and isinstance(component, dict)
            and HEATING_CAPABILITY in component
            and TIMER_CAPABILITY in component
        )
        if not self.burners:
            raise HomeAssistantError(
                "Płyta nie zwróciła żadnych komponentów burner-* z wymaganymi capabilities."
            )

        main = components.get("main", {})
        self._kids_lock_supported = KIDS_LOCK_CAPABILITY in main

        self.manual_level: dict[str, float] = {}
        self.heating_mode: dict[str, str] = {}
        self.residual_heat: dict[str, str] = {}
        self.timer_start_value: dict[str, float] = {}
        self.timer_current_value: dict[str, float] = {}
        self.timer_status: dict[str, str] = {}
        self.timer_minutes: dict[str, int] = {}
        self.lock_state = "unlocked"

        self._load_status(raw_status)

        add_listener = getattr(client, "add_device_event_listener", None)
        if callable(add_listener):
            self._remove_device_listener = add_listener(
                device_id, self._handle_device_event
            )

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    @staticmethod
    def _value(
        component: dict[str, Any], capability: str, attribute: str, default: Any
    ) -> Any:
        return (
            component.get(capability, {})
            .get(attribute, {})
            .get("value", default)
        )

    def _load_status(self, raw_status: dict[str, Any]) -> None:
        components = raw_status.get("components", {})
        for burner in self.burners:
            component = components.get(burner, {})
            self.manual_level[burner] = float(
                self._value(component, HEATING_CAPABILITY, "manualLevel", 0)
                or 0
            )
            self.heating_mode[burner] = str(
                self._value(component, HEATING_CAPABILITY, "heatingMode", "manual")
            )
            self.residual_heat[burner] = str(
                self._value(
                    component,
                    RESIDUAL_HEAT_CAPABILITY,
                    "surfaceResidualHeat",
                    "normal",
                )
            )
            start_value = float(
                self._value(component, TIMER_CAPABILITY, "startValue", 0) or 0
            )
            self.timer_start_value[burner] = start_value
            self.timer_current_value[burner] = float(
                self._value(component, TIMER_CAPABILITY, "currentValue", 0) or 0
            )
            self.timer_status[burner] = str(
                self._value(component, TIMER_CAPABILITY, "status", "idle")
            )
            self.timer_minutes[burner] = max(1, int(round(start_value)))

        main = components.get("main", {})
        self.lock_state = str(
            self._value(main, KIDS_LOCK_CAPABILITY, "lockState", "unlocked")
        )

    def _handle_device_event(self, event: Any) -> None:
        component = str(getattr(event, "component_id", ""))
        capability = str(getattr(event, "capability", ""))
        attribute = str(getattr(event, "attribute", ""))
        value = getattr(event, "value", None)

        changed = False
        if component in self.burners:
            if capability == HEATING_CAPABILITY:
                if attribute == "manualLevel" and isinstance(value, (int, float)):
                    self.manual_level[component] = float(value)
                    changed = True
                elif attribute == "heatingMode" and isinstance(value, str):
                    self.heating_mode[component] = value
                    changed = True
            elif capability == RESIDUAL_HEAT_CAPABILITY:
                if attribute == "surfaceResidualHeat" and isinstance(value, str):
                    self.residual_heat[component] = value
                    changed = True
            elif capability == TIMER_CAPABILITY:
                if attribute == "startValue" and isinstance(value, (int, float)):
                    self.timer_start_value[component] = float(value)
                    changed = True
                elif attribute == "currentValue" and isinstance(value, (int, float)):
                    self.timer_current_value[component] = float(value)
                    changed = True
                elif attribute == "status" and isinstance(value, str):
                    self.timer_status[component] = value
                    changed = True
        elif component == "main" and capability == KIDS_LOCK_CAPABILITY:
            if attribute == "lockState" and isinstance(value, str):
                self.lock_state = value
                changed = True

        if changed:
            self._notify()

    def burner_number(self, burner: str) -> str:
        return burner.removeprefix("burner-").lstrip("0") or "0"

    def residual_heat_label(self, burner: str) -> str:
        value = self.residual_heat.get(burner, "normal")
        return RESIDUAL_HEAT_LABELS.get(value, value)

    def heating_mode_label(self, burner: str) -> str:
        value = self.heating_mode.get(burner, "manual")
        return HEATING_MODE_LABELS.get(value, value)

    def set_timer_minutes(self, burner: str, value: float) -> None:
        if burner not in self.burners:
            raise HomeAssistantError(f"Nieznane pole płyty: {burner}")
        minutes = int(round(value))
        if not 1 <= minutes <= 1440:
            raise HomeAssistantError("Timer musi mieć od 1 do 1440 minut.")
        self.timer_minutes[burner] = minutes
        self._notify()

    async def _command(
        self,
        component: str,
        capability: str,
        command: str,
        argument: Any | None = None,
    ) -> None:
        await self.client.execute_device_command(
            self.device_id,
            capability,
            command,
            component,
            argument=argument,
        )

    async def start_timer(self, burner: str) -> None:
        minutes = self.timer_minutes[burner]
        await self._command(
            burner,
            TIMER_CAPABILITY,
            "setStartValue",
            [minutes, "min"],
        )
        await self._command(burner, TIMER_CAPABILITY, "start")
        self.timer_start_value[burner] = float(minutes)
        self.timer_current_value[burner] = float(minutes)
        self.timer_status[burner] = "running"
        self._notify()

    async def pause_timer(self, burner: str) -> None:
        await self._command(burner, TIMER_CAPABILITY, "pause")
        self.timer_status[burner] = "paused"
        self._notify()

    async def resume_timer(self, burner: str) -> None:
        await self._command(burner, TIMER_CAPABILITY, "resume")
        self.timer_status[burner] = "running"
        self._notify()

    async def cancel_timer(self, burner: str) -> None:
        await self._command(burner, TIMER_CAPABILITY, "cancel")
        self.timer_status[burner] = "idle"
        self.timer_current_value[burner] = 0
        self._notify()

    @property
    def kids_lock_supported(self) -> bool:
        return self._kids_lock_supported

    @property
    def kids_lock_enabled(self) -> bool:
        return self.lock_state == "locked"

    async def set_kids_lock(self, enabled: bool) -> None:
        if not self._kids_lock_supported:
            raise HomeAssistantError("Płyta nie udostępnia sterowania blokadą dziecięcą.")
        await self._command(
            "main",
            KIDS_LOCK_CAPABILITY,
            "lock" if enabled else "unlock",
        )
        self.lock_state = "locked" if enabled else "unlocked"
        self._notify()


async def _auto_find_cooktop(
    hass: HomeAssistant,
) -> tuple[Any, str, dict[str, Any]]:
    """Find a Samsung cooktop exposing burner components."""
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
            device_type = (
                main.get("samsungce.kitchenDeviceIdentification", {})
                .get("type", {})
                .get("value")
            )
            burners = [
                component_id
                for component_id, component in components.items()
                if component_id.startswith("burner-")
                and isinstance(component, dict)
                and HEATING_CAPABILITY in component
                and TIMER_CAPABILITY in component
            ]
            if device_type == "cooktop" and burners:
                return client, device_id, raw_status

    raise HomeAssistantError(
        "Nie znaleziono płyty SmartThings z komponentami burner-* i timerami."
    )


async def async_get_cooktop_controller(
    hass: HomeAssistant,
) -> CooktopController | None:
    """Return the shared cooktop controller, discovering it once."""
    data = hass.data.setdefault(DOMAIN, {})
    existing = data.get("cooktop")
    if isinstance(existing, CooktopController):
        return existing
    if existing is False:
        return None

    lock = data.get("_cooktop_lock")
    if lock is None:
        lock = asyncio.Lock()
        data["_cooktop_lock"] = lock

    async with lock:
        existing = data.get("cooktop")
        if isinstance(existing, CooktopController):
            return existing
        if existing is False:
            return None

        try:
            client, device_id, raw_status = await _auto_find_cooktop(hass)
            controller = CooktopController(client, device_id, raw_status)
        except HomeAssistantError:
            data["cooktop"] = False
            return None

        data["cooktop"] = controller
        return controller
