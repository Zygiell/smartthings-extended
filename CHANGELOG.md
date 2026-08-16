# Changelog

## 0.8.2

- Fixed Samsung microwave prepared settings by sending mode, power and operation time in a single SmartThings device-command batch.
- This preserves the advertised microwave power control while avoiding `METHOD_NOT_ALLOWED` returned when `samsungce.microwavePower.setPowerLevel` is sent alone on the tested appliance.
- Changed washer Start, Pause, Resume and Cancel to use the live `washerOperatingState.setMachineState` capability (`run`, `pause`, `stop`) instead of the proposed `samsungce.washerOperatingState` command set.
- Washer Start still checks Smart Control before applying prepared settings and starting.

## 0.8.1

- Fixed device/area association on Home Assistant 2026.8 and newer.
- Migrated SmartThings Extended entity loading from legacy YAML platforms to a Home Assistant config entry.
- Existing `configuration.yaml` settings are automatically imported into the config entry, including an optional pinned oven device ID.
- Linked extended entities directly to the existing device-registry entries owned by the official SmartThings integration.
- Preserved existing entity IDs and unique IDs during the migration.
- Kept the v0.8.0 DeviceInfo helper temporarily for source compatibility; config-entry loading clears it before entities are added.

## 0.8.0

- Attempted to link SmartThings Extended entities to official SmartThings devices using matching DeviceInfo identifiers.
- This approach does not attach entities when they are loaded through legacy YAML platforms and is superseded by v0.8.1.
- Preserved existing entity IDs and unique IDs.

## 0.7.0

- Added Samsung cooktop auto-detection using `burner-*` components.
- Added one locally prepared countdown-timer value per burner.
- Added Start, Pause, Resume and Cancel controls for each burner timer.
- Added child-lock control using `samsungce.kidsLockControl`.
- Added SmartThings device-event tracking for burner, residual-heat, timer and lock state.
- Kept burner names generic (`Pole 1…6`) because the appliance does not advertise physical burner positions.
- Intentionally did not expose burner power or heating-mode writes: the tested `samsungce.cooktopHeatingPower` capability publishes attributes but no commands.
- Avoided duplicating the official SmartThings read-only burner level/mode entities.

## 0.6.0

- Added Samsung refrigerator auto-detection using the CoolSelect+ `cvroom` component.
- Added CoolSelect+ mode selection using the refrigerator's advertised modes.
- Added direct AutoFill Pitcher control.
- Added direct ice-maker Night Mode control.
- Added refrigerator Night Light control and Night Light brightness selection.
- Added door-alarm sound selection using the appliance-advertised sound list.
- Added the Home Assistant switch platform for direct refrigerator toggles.
- Avoided duplicating refrigerator controls already exposed by the official SmartThings integration.
- Night Mode schedule editing is deferred until a proper time-based Home Assistant UI is added.

## 0.5.0

- Added Samsung dishwasher auto-detection using `samsungce.dishwasherWashingCourse.supportedCourses`.
- Added local washing-course selection with friendly labels for the tested dishwasher courses.
- Added dynamic selected-zone, Speed Booster and Sanitize controls based on each course's advertised options.
- Added Send settings, Start, Pause, Resume, Cancel and Cancel-and-drain buttons.
- Dishwasher Start checks Smart Control before sending the start command.
- Prepared settings remain local until Send settings or Start is pressed.

## 0.4.0

- Added Samsung washer auto-detection using `samsungce.washerCycle.supportedCycles`.
- Added local prepared wash-program selection.
- Added dynamic water-temperature, spin-level and rinse-count selectors based on the selected program's advertised options.
- Added Bubble Soak control when supported by the selected program.
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