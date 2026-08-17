"""Time entities for SmartThings Extended."""

from __future__ import annotations

from datetime import time, timedelta

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

from .fridge import FridgeController, async_get_fridge_controller
from .linked_device import smartthings_device_info

# The appliance reports and accepts full ISO-8601 UTC datetimes even though
# only the time of day is meaningful for the schedule.
DEVICE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up refrigerator schedule time entities."""
    entities: list[TimeEntity] = []

    fridge = await async_get_fridge_controller(hass)
    if fridge is not None and fridge.icemaker_time_setting_supported:
        entities.extend(
            [
                FridgeIcemakerNightTime(fridge, "start"),
                FridgeIcemakerNightTime(fridge, "end"),
            ]
        )

    async_add_entities(entities)


def _parse_local_time(value: object) -> time | None:
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    return dt_util.as_local(parsed).time()


class FridgeIcemakerNightTime(TimeEntity):
    """Start or end time of the refrigerator ice-maker Night Mode."""

    _attr_should_poll = False

    def __init__(self, controller: FridgeController, edge: str) -> None:
        self.controller = controller
        self._edge = edge
        if edge == "start":
            self._attr_name = "Lodówka — tryb nocny kostkarki — początek"
            self._attr_icon = "mdi:clock-start"
        else:
            self._attr_name = "Lodówka — tryb nocny kostkarki — koniec"
            self._attr_icon = "mdi:clock-end"
        self._attr_unique_id = (
            f"smartthings_extended_{controller.device_id}_fridge_"
            f"icemaker_night_{edge}"
        )
        self._attr_device_info = smartthings_device_info(controller.device_id)

    @property
    def available(self) -> bool:
        return self.controller.icemaker_time_setting_supported

    @property
    def native_value(self) -> time | None:
        raw = (
            self.controller.icemaker_night_start
            if self._edge == "start"
            else self.controller.icemaker_night_end
        )
        return _parse_local_time(raw)

    async def async_set_value(self, value: time) -> None:
        start = _parse_local_time(self.controller.icemaker_night_start)
        end = _parse_local_time(self.controller.icemaker_night_end)
        if self._edge == "start":
            start = value
        else:
            end = value
        if start is None or end is None:
            raise HomeAssistantError(
                "Lodówka nie zwróciła pełnego harmonogramu trybu nocnego "
                "kostkarki — nie można ustawić godziny."
            )

        now_local = dt_util.now()
        start_local = now_local.replace(
            hour=start.hour, minute=start.minute, second=0, microsecond=0
        )
        end_local = now_local.replace(
            hour=end.hour, minute=end.minute, second=0, microsecond=0
        )
        if end_local <= start_local:
            end_local += timedelta(days=1)

        await self.controller.set_icemaker_night_schedule(
            dt_util.as_utc(start_local).strftime(DEVICE_TIME_FORMAT),
            dt_util.as_utc(end_local).strftime(DEVICE_TIME_FORMAT),
        )

    async def async_added_to_hass(self) -> None:
        remove = self.controller.add_listener(self.async_write_ha_state)
        self.async_on_remove(remove)
