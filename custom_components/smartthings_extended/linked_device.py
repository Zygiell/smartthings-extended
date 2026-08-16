"""Helpers for linking extended entities to official SmartThings devices."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo

SMARTTHINGS_DOMAIN = "smartthings"


def smartthings_device_info(device_id: str) -> DeviceInfo:
    """Return the legacy v0.8.0 descriptor used by existing entity classes.

    The v0.8.1 config-entry adapter clears this descriptor before entities are
    added and links them directly to the official SmartThings DeviceEntry.
    """
    return DeviceInfo(identifiers={(SMARTTHINGS_DOMAIN, device_id)})


def smartthings_device_entry(
    hass: HomeAssistant, device_id: str
) -> DeviceEntry | None:
    """Return the device-registry entry owned by the official SmartThings config entry."""
    registry = dr.async_get(hass)

    for entry in hass.config_entries.async_entries(SMARTTHINGS_DOMAIN):
        device = registry.async_get_device_by_identifier(
            (SMARTTHINGS_DOMAIN, device_id), entry.entry_id
        )
        if device is not None:
            return device

    return None
