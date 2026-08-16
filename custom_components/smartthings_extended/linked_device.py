"""Helpers for linking extended entities to official SmartThings devices."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

SMARTTHINGS_DOMAIN = "smartthings"


def smartthings_device_info(device_id: str) -> DeviceInfo:
    """Link an entity to the device created by the official SmartThings integration."""
    return DeviceInfo(identifiers={(SMARTTHINGS_DOMAIN, device_id)})
