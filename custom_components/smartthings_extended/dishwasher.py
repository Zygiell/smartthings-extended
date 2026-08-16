"""Samsung dishwasher support for SmartThings Extended."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN, SMARTTHINGS_DOMAIN

COURSE_LABELS = {
    "auto": "Automatyczny",
    "eco": "Eco",
    "intensive": "Intensywny",
    "delicate": "Delikatny",
    "express_0C": "Ekspresowy",
    "preWash": "Mycie wstępne",
    "extraSilence": "Bardzo cichy",
    "machineCare": "Czyszczenie zmywarki",
    "plastics": "Tworzywa sztuczne",
    "babycare": "Naczynia dziecięce",
    "potsAndPans": "Garnki i patelnie",
    "drinkware": "Szkło i naczynia do napojów",
}

ZONE_LABELS = {
    "none": "Brak",
    "lower": "Dolna",
    "upper": "Górna",
    "all": "Wszystkie",
}

BOOL_LABELS = {
    False: "Wyłączone",
    True: "Włączone",
}


class DishwasherController:
    """Prepared dishwasher settings and SmartThings API access."""

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

        course_capability = main.get("samsungce.dishwasherWashingCourse", {})
        supported_courses = (
            course_capability.get("supportedCourses", {}).get("value")
        )
        if not isinstance(supported_courses, list) or not supported_courses:
            raise HomeAssistantError(
                "Zmywarka nie zwróciła listy "
                "samsungce.dishwasherWashingCourse.supportedCourses."
            )

        details_capability = main.get(
            "samsungce.dishwasherWashingCourseDetails", {}
        )
        predefined = details_capability.get("predefinedCourses", {}).get("value")
        if not isinstance(predefined, list):
            predefined = []

        self.courses = [
            str(value) for value in supported_courses if isinstance(value, str)
        ]
        self.course_details: dict[str, dict[str, Any]] = {
            str(item["courseName"]): item
            for item in predefined
            if isinstance(item, dict) and isinstance(item.get("courseName"), str)
        }

        current_course = course_capability.get("washingCourse", {}).get("value")
        self.selected_course = (
            str(current_course)
            if isinstance(current_course, str) and current_course in self.courses
            else self.courses[0]
        )

        self.selected_zone = ""
        self.speed_booster = False
        self.sanitize = False
        self._apply_course_defaults(self.selected_course)

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

    def supported_courses(self) -> list[str]:
        return list(self.courses)

    def course_label(self, course: str) -> str:
        return COURSE_LABELS.get(course, course)

    def course_from_label(self, label: str) -> str:
        for course in self.supported_courses():
            if self.course_label(course) == label:
                return course
        raise HomeAssistantError(f"Nieznany program zmywarki: {label}")

    def course_options(self, course: str | None = None) -> dict[str, Any]:
        selected = course or self.selected_course
        details = self.course_details.get(selected, {})
        options = details.get("options", {}) if isinstance(details, dict) else {}
        return options if isinstance(options, dict) else {}

    def _settable(self, option_name: str) -> list[Any]:
        option = self.course_options().get(option_name)
        if not isinstance(option, dict):
            return []
        values = option.get("settable", [])
        return list(values) if isinstance(values, list) else []

    def _default(self, option_name: str, fallback: Any) -> Any:
        option = self.course_options().get(option_name)
        if not isinstance(option, dict):
            return fallback
        return option.get("default", fallback)

    def _apply_course_defaults(self, course: str) -> None:
        self.selected_course = course

        zones = self.zone_values()
        zone_default = str(self._default("selectedZone", ""))
        self.selected_zone = (
            zone_default if zone_default in zones else (zones[0] if zones else "")
        )

        speed_values = self.speed_booster_values()
        speed_default = bool(self._default("speedBooster", False))
        self.speed_booster = (
            speed_default if speed_default in speed_values else False
        )

        sanitize_values = self.sanitize_values()
        sanitize_default = bool(self._default("sanitize", False))
        self.sanitize = (
            sanitize_default if sanitize_default in sanitize_values else False
        )

    def set_course(self, course: str) -> None:
        if course not in self.supported_courses():
            raise HomeAssistantError(f"Program {course} nie jest obsługiwany.")
        self._apply_course_defaults(course)
        self._notify()

    def zone_values(self) -> list[str]:
        return [str(value) for value in self._settable("selectedZone")]

    def zone_label(self, value: str) -> str:
        return ZONE_LABELS.get(value, value)

    def zone_from_label(self, label: str) -> str:
        for value in self.zone_values():
            if self.zone_label(value) == label:
                return value
        raise HomeAssistantError(f"Nieznana strefa zmywania: {label}")

    def set_zone(self, value: str) -> None:
        if value not in self.zone_values():
            raise HomeAssistantError(
                f"Strefa {value} nie jest dostępna dla programu {self.selected_course}."
            )
        self.selected_zone = value
        self._notify()

    def speed_booster_values(self) -> list[bool]:
        return [value for value in self._settable("speedBooster") if isinstance(value, bool)]

    def sanitize_values(self) -> list[bool]:
        return [value for value in self._settable("sanitize") if isinstance(value, bool)]

    def bool_label(self, value: bool) -> str:
        return BOOL_LABELS[value]

    def bool_from_label(self, label: str) -> bool:
        for value, value_label in BOOL_LABELS.items():
            if value_label == label:
                return value
        raise HomeAssistantError(f"Nieznana wartość opcji: {label}")

    def set_speed_booster(self, value: bool) -> None:
        if value not in self.speed_booster_values():
            raise HomeAssistantError(
                f"Speed Booster nie jest dostępny dla programu {self.selected_course}."
            )
        self.speed_booster = value
        self._notify()

    def set_sanitize(self, value: bool) -> None:
        if value not in self.sanitize_values():
            raise HomeAssistantError(
                f"Sanitize nie jest dostępne dla programu {self.selected_course}."
            )
        self.sanitize = value
        self._notify()

    def prepared_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {}
        if self.zone_values():
            options["selectedZone"] = self.selected_zone
        if self.speed_booster_values():
            options["speedBooster"] = self.speed_booster
        if self.sanitize_values():
            options["sanitize"] = self.sanitize
        return options

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
        """Send prepared course and options without starting."""
        await self._command(
            "samsungce.dishwasherWashingCourse",
            "setWashingCourse",
            self.selected_course,
        )

        options = self.prepared_options()
        if options:
            await self._command(
                "samsungce.dishwasherWashingOptions",
                "setOptions",
                options,
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

    async def start(self) -> None:
        """Apply prepared settings and start the dishwasher."""
        if not await self.remote_control_enabled():
            raise HomeAssistantError(
                "Smart Control zmywarki jest wyłączony. "
                "Włącz zdalne sterowanie na zmywarce przed Start."
            )
        await self.send_settings()
        await self._command("samsungce.dishwasherOperation", "start")

    async def pause(self) -> None:
        await self._command("samsungce.dishwasherOperation", "pause")

    async def resume(self) -> None:
        await self._command("samsungce.dishwasherOperation", "resume")

    async def cancel(self) -> None:
        await self._command("samsungce.dishwasherOperation", "cancel")

    async def cancel_and_drain(self) -> None:
        await self._command("samsungce.dishwasherOperation", "cancel", True)


async def _auto_find_dishwasher(
    hass: HomeAssistant,
) -> tuple[Any, str, dict[str, Any]]:
    """Find a Samsung dishwasher exposing course metadata."""
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
            courses = (
                main.get("samsungce.dishwasherWashingCourse", {})
                .get("supportedCourses", {})
                .get("value")
            )
            operation = main.get("samsungce.dishwasherOperation")
            if (
                isinstance(courses, list)
                and bool(courses)
                and isinstance(operation, dict)
            ):
                return client, device_id, raw_status

    raise HomeAssistantError(
        "Nie znaleziono zmywarki SmartThings z "
        "samsungce.dishwasherWashingCourse.supportedCourses."
    )


async def async_get_dishwasher_controller(
    hass: HomeAssistant,
) -> DishwasherController | None:
    """Return the shared dishwasher controller, discovering it once."""
    data = hass.data.setdefault(DOMAIN, {})
    existing = data.get("dishwasher")
    if isinstance(existing, DishwasherController):
        return existing
    if existing is False:
        return None

    lock = data.get("_dishwasher_lock")
    if lock is None:
        lock = asyncio.Lock()
        data["_dishwasher_lock"] = lock

    async with lock:
        existing = data.get("dishwasher")
        if isinstance(existing, DishwasherController):
            return existing
        if existing is False:
            return None

        try:
            client, device_id, raw_status = await _auto_find_dishwasher(hass)
            controller = DishwasherController(client, device_id, raw_status)
        except HomeAssistantError:
            data["dishwasher"] = False
            return None

        data["dishwasher"] = controller
        return controller
