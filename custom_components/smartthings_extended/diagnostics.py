"""Diagnostics support for SmartThings Extended."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .fridge import COOLSELECT_COMPONENT, async_get_fridge_controller

_FRIDGE_CAPABILITIES = (
    "samsungce.doorAlarm",
    "samsungce.icemakerNightMode",
    "samsungce.fridgeInteriorLighting",
    "samsungce.autoFillPitcher",
)


async def _capability_schema(client: Any, capability: str) -> Any:
    """Return a capability schema when SmartThings allows reading it."""
    get_capability = getattr(client, "get_capability", None)
    if not callable(get_capability):
        return {"error": "get_capability unavailable"}

    try:
        raw = await get_capability(capability)
    except Exception as err:  # noqa: BLE001
        return {"error": type(err).__name__, "message": str(err)}

    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return focused refrigerator diagnostics without credentials."""
    fridge = await async_get_fridge_controller(hass)
    if fridge is None:
        return {"refrigerator": None}

    raw_status = await fridge.client.get_raw_device_status(fridge.device_id)
    components = raw_status.get("components", {})
    main = components.get("main", {})
    cvroom = components.get(COOLSELECT_COMPONENT, {})

    status = {
        "main": {
            capability: main.get(capability)
            for capability in _FRIDGE_CAPABILITIES
            if capability in main
        },
        COOLSELECT_COMPONENT: {
            "custom.fridgeMode": cvroom.get("custom.fridgeMode")
        },
    }

    schemas: dict[str, Any] = {}
    for capability in (*_FRIDGE_CAPABILITIES, "custom.fridgeMode"):
        schemas[capability] = await _capability_schema(fridge.client, capability)

    return {
        "refrigerator": {
            "status": status,
            "capability_schemas": schemas,
            "night_mode_schedule": {
                "supported": fridge.icemaker_time_setting_supported,
                "start": fridge.icemaker_night_start,
                "end": fridge.icemaker_night_end,
            },
        }
    }
