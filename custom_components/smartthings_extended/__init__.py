"""SmartThings Extended for Home Assistant.

Extends Home Assistant's official SmartThings integration with Samsung
capabilities that are not currently mapped to native HA entities.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .linked_device import smartthings_device_entry

DOMAIN = "smartthings_extended"
SMARTTHINGS_DOMAIN = "smartthings"

SERVICE_SEND_COMMAND = "send_command"
CONF_OVEN_DEVICE_ID = "oven_device_id"

PLATFORMS = [
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.TIME,
]

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Any(
            None,
            vol.Schema(
                {
                    vol.Optional(CONF_OVEN_DEVICE_ID): cv.string,
                }
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Optional("component", default="main"): cv.string,
        vol.Required("capability"): cv.string,
        vol.Required("command"): cv.string,
        vol.Optional("arguments"): vol.Any(
            None, list, dict, str, int, float, bool
        ),
    }
)

CAVITY_COMPONENT = {
    "upper": "main",
    "lower": "cavity-01",
}

# Order and labels intentionally match the SmartThings UI for this oven.
MODE_ORDER = {
    "upper": [
        "Convection",
        "LargeGrill",
        "TopConvection",
        "AirFry",
    ],
    "lower": [
        "Convection",
        "BottomConvection",
        "Bottom",
        "SteamCook",
        "SteamConvection",
        "SteamBottomConvection",
    ],
}

MODE_LABELS = {
    "Convection": "Termoobieg",
    "LargeGrill": "Duży grill",
    "TopConvection": "Górna grzałka + termoobieg",
    "AirFry": "Smażenie gorącym powietrzem",
    "BottomConvection": "Dolna grzałka + termoobieg",
    "Bottom": "Dolna grzałka",
    "SteamCook": "Pieczenie z użyciem pary",
    "SteamConvection": "Para + termoobieg",
    "SteamBottomConvection": "Para + dolna grzałka + termoobieg",
}


def _find_client_for_device(hass: HomeAssistant, device_id: str) -> Any:
    """Find OAuth SmartThings client which owns the specified device."""
    for entry in hass.config_entries.async_entries(SMARTTHINGS_DOMAIN):
        runtime_data = getattr(entry, "runtime_data", None)
        devices = getattr(runtime_data, "devices", None)
        if devices is not None and device_id in devices:
            client = getattr(runtime_data, "client", None)
            if client is not None:
                return client
    raise HomeAssistantError(
        f"Nie znaleziono urządzenia SmartThings {device_id} "
        "w załadowanej oficjalnej integracji SmartThings."
    )


async def _auto_find_oven(hass: HomeAssistant) -> tuple[Any, str, dict[str, Any]]:
    """Find a Samsung dual-cavity oven from its kitchen mode specification."""
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
            capability = main.get("samsungce.kitchenModeSpecification", {})
            specification = capability.get("specification", {}).get("value")

            # Some Samsung kitchen appliances (for example microwaves) also
            # expose kitchenModeSpecification. The oven supported by this
            # integration is identified by separate upper/lower cavity specs.
            if (
                isinstance(specification, dict)
                and isinstance(specification.get("upper"), list)
                and isinstance(specification.get("lower"), list)
                and specification["upper"]
                and specification["lower"]
            ):
                return client, device_id, raw_status

    raise HomeAssistantError(
        "Nie znaleziono dwukomorowego piekarnika SmartThings z sekcjami "
        "upper/lower w samsungce.kitchenModeSpecification."
    )


def _time_to_minutes(value: str) -> int:
    """Convert SmartThings HH:MM:SS to minutes."""
    parts = value.split(":")
    if len(parts) != 3:
        return 60
    hours, minutes, seconds = (int(x) for x in parts)
    total = hours * 60 + minutes
    if seconds:
        total += 1
    return max(1, total)


def _minutes_to_time(minutes: int) -> str:
    """Convert minutes to SmartThings HH:MM:SS."""
    minutes = max(1, int(minutes))
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}:00"


class OvenController:
    """Shared state and SmartThings API access for the oven entities."""

    def __init__(
        self,
        client: Any,
        device_id: str,
        raw_status: dict[str, Any],
    ) -> None:
        self.client = client
        self.device_id = device_id
        self.raw_status = raw_status
        self._listeners: list[Callable[[], None]] = []

        try:
            self.specification: dict[str, list[dict[str, Any]]] = (
                raw_status["components"]["main"]
                ["samsungce.kitchenModeSpecification"]
                ["specification"]["value"]
            )
        except (KeyError, TypeError) as err:
            raise HomeAssistantError(
                "Piekarnik nie zwrócił poprawnego kitchenModeSpecification."
            ) from err

        self.selected_mode: dict[str, str] = {}
        self.temperature: dict[str, float] = {}
        self.time_minutes: dict[str, int] = {}

        for cavity in CAVITY_COMPONENT:
            modes = self.supported_modes(cavity)
            if not modes:
                raise HomeAssistantError(
                    f"Brak obsługiwanych trybów ręcznych dla komory {cavity}."
                )

            preferred = "Convection" if "Convection" in modes else modes[0]
            self.selected_mode[cavity] = preferred

            options = self.mode_options(cavity, preferred)
            temp = options["temperature"]["C"]
            self.temperature[cavity] = float(temp["default"])

            operation_time = options["operationTime"]
            self.time_minutes[cavity] = _time_to_minutes(
                operation_time.get("default", "01:00:00")
            )

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

    def _spec_by_mode(self, cavity: str) -> dict[str, dict[str, Any]]:
        return {
            item["mode"]: item
            for item in self.specification.get(cavity, [])
            if isinstance(item, dict) and "mode" in item
        }

    def supported_modes(self, cavity: str) -> list[str]:
        """Return manual modes safe to expose in the UI."""
        specs = self._spec_by_mode(cavity)
        result: list[str] = []

        for mode in MODE_ORDER[cavity]:
            item = specs.get(mode)
            if not item:
                continue
            operations = set(item.get("supportedOperations", []))
            options = item.get("supportedOptions", {})
            if (
                {"set", "start"}.issubset(operations)
                and "temperature" in options
                and "operationTime" in options
            ):
                result.append(mode)

        return result

    def mode_options(self, cavity: str, mode: str | None = None) -> dict[str, Any]:
        selected = mode or self.selected_mode[cavity]
        item = self._spec_by_mode(cavity).get(selected)
        if item is None:
            raise HomeAssistantError(
                f"Tryb {selected} nie jest dostępny dla komory {cavity}."
            )
        return item.get("supportedOptions", {})

    def mode_label(self, mode: str) -> str:
        return MODE_LABELS.get(mode, mode)

    def mode_from_label(self, cavity: str, label: str) -> str:
        for mode in self.supported_modes(cavity):
            if self.mode_label(mode) == label:
                return mode
        raise HomeAssistantError(f"Nieznany tryb piekarnika: {label}")

    def set_mode(self, cavity: str, mode: str) -> None:
        if mode not in self.supported_modes(cavity):
            raise HomeAssistantError(
                f"Tryb {mode} nie jest obsługiwany dla komory {cavity}."
            )

        self.selected_mode[cavity] = mode
        options = self.mode_options(cavity, mode)

        temp = options["temperature"]["C"]
        self.temperature[cavity] = float(temp["default"])

        operation_time = options["operationTime"]
        self.time_minutes[cavity] = _time_to_minutes(
            operation_time.get("default", "01:00:00")
        )
        self._notify()

    def temperature_limits(self, cavity: str) -> tuple[float, float, float]:
        temp = self.mode_options(cavity)["temperature"]["C"]
        return (
            float(temp["min"]),
            float(temp["max"]),
            float(temp.get("resolution", 1)),
        )

    def set_temperature(self, cavity: str, value: float) -> None:
        minimum, maximum, step = self.temperature_limits(cavity)
        value = float(value)
        if not minimum <= value <= maximum:
            raise HomeAssistantError(
                f"Temperatura {value}°C jest poza zakresem "
                f"{minimum:g}–{maximum:g}°C."
            )
        aligned = minimum + round((value - minimum) / step) * step
        self.temperature[cavity] = float(
            min(max(aligned, minimum), maximum)
        )
        self._notify()

    def time_limits(self, cavity: str) -> tuple[int, int, int]:
        op = self.mode_options(cavity)["operationTime"]
        return (
            _time_to_minutes(op["min"]),
            _time_to_minutes(op["max"]),
            max(1, _time_to_minutes(op.get("resolution", "00:01:00"))),
        )

    def set_time_minutes(self, cavity: str, value: float) -> None:
        minimum, maximum, step = self.time_limits(cavity)
        value_int = int(round(value))
        if not minimum <= value_int <= maximum:
            raise HomeAssistantError(
                f"Czas {value_int} min jest poza zakresem "
                f"{minimum}–{maximum} min."
            )
        aligned = minimum + round((value_int - minimum) / step) * step
        self.time_minutes[cavity] = int(min(max(aligned, minimum), maximum))
        self._notify()

    async def _command(
        self,
        cavity: str,
        capability: str,
        command: str,
        argument: Any | None = None,
    ) -> None:
        component = CAVITY_COMPONENT[cavity]
        await self.client.execute_device_command(
            self.device_id,
            capability,
            command,
            component,
            argument=argument,
        )

    async def _batch_commands(self, commands: list[dict[str, Any]]) -> None:
        """Send multiple oven commands in one SmartThings request."""
        post = getattr(self.client, "_post", None)
        if post is None:
            raise HomeAssistantError(
                "Ta wersja pysmartthings nie obsługuje wymaganego batch requestu."
            )
        await post(
            f"v1/devices/{self.device_id}/commands",
            data={"commands": commands},
        )

    async def send_settings(self, cavity: str) -> None:
        """Send prepared mode, temperature and time together without starting."""
        component = CAVITY_COMPONENT[cavity]
        temperature = self.temperature[cavity]
        temperature_argument: int | float = (
            int(temperature) if temperature.is_integer() else temperature
        )

        commands: list[dict[str, Any]] = [
            {
                "component": component,
                "capability": "samsungce.ovenMode",
                "command": "setOvenMode",
                "arguments": [self.selected_mode[cavity]],
            },
            {
                "component": component,
                "capability": "ovenSetpoint",
                "command": "setOvenSetpoint",
                "arguments": [temperature_argument],
            },
            {
                "component": component,
                "capability": "samsungce.ovenOperatingState",
                "command": "setOperationTime",
                "arguments": [_minutes_to_time(self.time_minutes[cavity])],
            },
        ]
        await self._batch_commands(commands)

    async def remote_control_enabled(self) -> bool:
        """Read current Smart Control status before a remote start."""
        raw = await self.client.get_raw_device_status(self.device_id)
        value = (
            raw.get("components", {})
            .get("main", {})
            .get("remoteControlStatus", {})
            .get("remoteControlEnabled", {})
            .get("value")
        )
        return str(value).lower() == "true"

    async def start(self, cavity: str) -> None:
        """Apply prepared settings and start the selected cavity."""
        if not await self.remote_control_enabled():
            raise HomeAssistantError(
                "Smart Control piekarnika jest wyłączony. "
                "Włącz Inteligentne sterowanie na piekarniku przed Start."
            )

        await self.send_settings(cavity)
        await self._command(
            cavity, "samsungce.ovenOperatingState", "start"
        )

    async def pause(self, cavity: str) -> None:
        await self._command(
            cavity, "samsungce.ovenOperatingState", "pause"
        )

    async def stop(self, cavity: str) -> None:
        await self._command(
            cavity, "samsungce.ovenOperatingState", "stop"
        )


def _link_extended_entities(hass: HomeAssistant, entities: list[Any]) -> None:
    """Link legacy platform entities directly to official SmartThings devices."""
    for entity in entities:
        controller = getattr(entity, "controller", None)
        device_id = getattr(controller, "device_id", None)
        if not device_id:
            continue

        # v0.8.0 used DeviceInfo identifiers. HA 2026.8 no longer merges devices
        # across config entries, so clear that descriptor and link the entity to
        # the source SmartThings DeviceEntry directly.
        entity._attr_device_info = None
        entity.device_entry = smartthings_device_entry(hass, device_id)


def _install_config_entry_platform_adapters() -> None:
    """Adapt the existing platform builders to config-entry loading."""
    from . import button as button_platform
    from . import number as number_platform
    from . import select as select_platform
    from . import switch as switch_platform
    from . import time as time_platform

    for module in (
        select_platform,
        number_platform,
        button_platform,
        switch_platform,
        time_platform,
    ):
        if hasattr(module, "async_setup_entry"):
            continue

        legacy_setup = module.async_setup_platform

        async def async_setup_entry_adapter(
            hass: HomeAssistant,
            entry: ConfigEntry,
            async_add_entities: Any,
            *,
            _legacy_setup: Any = legacy_setup,
        ) -> None:
            def add_entities(
                entities: Any, update_before_add: bool = False
            ) -> None:
                entity_list = list(entities)
                _link_extended_entities(hass, entity_list)
                async_add_entities(entity_list, update_before_add)

            await _legacy_setup(hass, entry.data, add_entities, None)

        module.async_setup_entry = async_setup_entry_adapter


async def _register_service(hass: HomeAssistant) -> None:
    """Register the generic SmartThings command service once."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    async def handle_send_command(call: ServiceCall) -> None:
        device_id: str = call.data["device_id"]
        component: str = call.data["component"]
        capability: str = call.data["capability"]
        command: str = call.data["command"]
        service_client = _find_client_for_device(hass, device_id)

        kwargs: dict[str, Any] = {}
        if "arguments" in call.data:
            kwargs["argument"] = call.data["arguments"]

        try:
            await service_client.execute_device_command(
                device_id,
                capability,
                command,
                component,
                **kwargs,
            )
        except Exception as err:
            _LOGGER.exception(
                "SmartThings command failed: device=%s component=%s "
                "capability=%s command=%s",
                device_id,
                component,
                capability,
                command,
            )
            raise HomeAssistantError(
                f"SmartThings odrzucił komendę {capability}.{command}: {err}"
            ) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        handle_send_command,
        schema=SERVICE_SCHEMA,
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration and import the legacy YAML configuration."""
    await _register_service(hass)

    if DOMAIN in config and not hass.config_entries.async_entries(DOMAIN):
        domain_config = config.get(DOMAIN) or {}
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=dict(domain_config),
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartThings Extended from a config entry."""
    configured_oven_id = entry.data.get(CONF_OVEN_DEVICE_ID)

    try:
        if configured_oven_id:
            client = _find_client_for_device(hass, configured_oven_id)
            raw_status = await client.get_raw_device_status(configured_oven_id)
            oven_id = configured_oven_id
        else:
            client, oven_id, raw_status = await _auto_find_oven(hass)
    except HomeAssistantError as err:
        raise ConfigEntryNotReady(str(err)) from err

    controller = OvenController(client, oven_id, raw_status)

    data = hass.data.setdefault(DOMAIN, {})
    data["oven"] = controller

    _LOGGER.info("SmartThings Extended found oven %s", oven_id)

    _install_config_entry_platform_adapters()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload SmartThings Extended."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data.get(DOMAIN, {})
        for key in ("oven", "microwave", "washer", "dishwasher", "fridge", "cooktop"):
            data.pop(key, None)
    return unload_ok
