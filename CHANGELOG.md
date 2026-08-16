# Changelog

## 0.4.0

- Added Samsung washer auto-detection using `samsungce.washerCycle.supportedCycles`.
- Added local prepared wash-program selection.
- Added dynamic water-temperature, spin-level and rinse-count selectors based on the selected program's advertised options.
- Added Bubble Soak control when the selected program supports it.
- Added Send settings, Start, Pause, Resume and Cancel buttons.
- Washer Start checks Smart Control before sending the start command.
- Prepared settings remain local until Send settings or Start is pressed.
- Cycle IDs are exposed as `Program XX` until localized SmartThings cycle names are mapped.

## 0.3.0

- Added Samsung microwave auto-detection using `kitchenModeSpecification.single`.
- Added microwave mode and power selectors.
- Added microwave operation time with 10-second resolution where advertised by the device.
- Added Send settings, Start, Pause and Stop buttons for the microwave.
- Added a door-state safety check before microwave Start when the device reports door state.
- Mode-specific controls become unavailable when the selected mode does not support them.

## 0.2.1

- Added HACS-ready repository structure.
- Added Home Assistant/HACS metadata and local brand icon.
- Fixed oven auto-detection so appliances such as microwaves exposing
  `samsungce.kitchenModeSpecification` are not mistaken for a dual-cavity oven.
- Preserved the v0.2 oven controls and generic `send_command` action.

## 0.2.0

- Added dual-cavity Samsung oven controls.
- Added dynamic mode, temperature and time preparation entities.
- Added Send settings, Start, Pause and Stop buttons per cavity.
- Start checks Smart Control before sending the start command.

## 0.1.0

- Initial generic SmartThings command service using the OAuth client from
  Home Assistant's official SmartThings integration.
