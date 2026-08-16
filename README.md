# SmartThings Extended

Experimental Home Assistant custom integration that extends the official
SmartThings integration with Samsung appliance capabilities that Home Assistant
does not currently expose as native entities.

> **Status:** experimental. This project reuses the authenticated OAuth client
> from Home Assistant's official `smartthings` integration. It does not store
> a separate SmartThings PAT.

## Current support — v0.8.1

### Device registry integration

SmartThings Extended is loaded through a Home Assistant config entry and links
its entities directly to the existing device-registry entries owned by the
official SmartThings integration.

This is important on Home Assistant 2026.8 and newer, where devices are owned by
a single config entry and helper integrations should link their entities to the
source device instead of attempting to merge devices by matching identifiers.

Existing YAML configuration is automatically imported into the SmartThings
Extended config entry on first startup after upgrading. Existing entity IDs and
unique IDs are preserved, so dashboards and automations do not need to be
rewritten.

As a result, extended entities can use the same appliance device and area as the
official SmartThings entities, for example `Pralka / Pralnia` or
`Lodówka / Kuchnia`.

### Samsung dual-cavity oven

For each cavity the integration exposes local preparation controls:

- mode
- temperature
- operation time
- Send settings
- Start
- Pause
- Stop

The supported modes and temperature/time limits are read from the device's
`samsungce.kitchenModeSpecification`.

`Start` checks `remoteControlStatus.remoteControlEnabled` first and refuses to
start the oven when Smart Control is disabled.

### Samsung microwave

The microwave is auto-detected from a `single` kitchen mode specification that
contains a directly settable `MicroWave` mode.

The integration exposes:

- mode
- microwave power when the selected mode supports it
- operation time in seconds using the device-advertised limits and resolution
- Send settings
- Start
- Pause
- Stop

For the tested Samsung NQ7000B family, the device advertises microwave power
levels from 100 W to 900 W and a 10-second operation-time resolution. Other
compatible devices are read dynamically from their own SmartThings mode
specification.

Before microwave `Start`, the integration refuses to continue when SmartThings
reports that the door is open. This microwave reports `remoteControlStatus` as
unavailable, so the oven-specific Smart Control check is not applied to it.

### Samsung washer

The washer is auto-detected from `samsungce.washerCycle.supportedCycles` and
uses each cycle's advertised `supportedOptions` to build local preparation
controls dynamically.

The integration exposes:

- wash program
- water temperature when supported by the selected program
- spin level when supported by the selected program
- rinse count when supported by the selected program
- Bubble Soak when supported by the selected program
- Send settings
- Start
- Pause
- Resume
- Cancel

Changing the prepared program immediately recalculates the local option lists
and defaults. No washer command is sent until **Send settings** or **Start** is
pressed.

Program IDs are currently exposed as `Program XX` because the appliance status
provides cycle identifiers but not localized SmartThings display names. Friendly
cycle-name mapping can be added separately without changing the control model.

Washer `Start` checks `remoteControlStatus.remoteControlEnabled` first and
refuses to start when Smart Control is disabled.

### Samsung dishwasher

The dishwasher is auto-detected from
`samsungce.dishwasherWashingCourse.supportedCourses`. Course-specific option
availability and defaults are read from
`samsungce.dishwasherWashingCourseDetails.predefinedCourses`.

The integration exposes:

- washing course
- selected wash zone when supported by the selected course
- Speed Booster when supported by the selected course
- Sanitize when supported by the selected course
- Send settings
- Start
- Pause
- Resume
- Cancel
- Cancel and drain

Changing the prepared course immediately recalculates the local option lists
and defaults. No dishwasher command is sent until **Send settings** or **Start**
is pressed.

Dishwasher `Start` checks `remoteControlStatus.remoteControlEnabled` first and
refuses to start when remote control is disabled.

### Samsung refrigerator

The refrigerator extension intentionally does not duplicate controls that the
official SmartThings integration already exposes, such as compartment
temperatures, Power Cool, Power Freeze and the main ice-maker switches.

For compatible refrigerators with a `cvroom` CoolSelect+ component it adds:

- CoolSelect+ mode selection using the modes advertised by the appliance
- AutoFill Pitcher on/off
- ice-maker Night Mode on/off
- refrigerator Night Light on/off
- Night Light brightness selection
- door-alarm sound selection

These refrigerator controls are direct controls: changing an entity immediately
sends the corresponding SmartThings command. The current Night Mode schedule is
read by the controller but schedule editing is intentionally deferred until a
proper time-based Home Assistant UI is added.

### Samsung cooktop

The cooktop is auto-detected from `burner-*` components exposing
`samsungce.cooktopHeatingPower` and `samsungce.countDownTimer`.

For the tested cooktop SmartThings reports six logical burner components. The
integration intentionally keeps them named **Pole 1…6** because the device does
not advertise their physical positions.

The integration adds:

- one locally prepared countdown-timer value per burner
- Start / Pause / Resume / Cancel for each burner timer
- child-lock on/off using `samsungce.kidsLockControl`
- live burner/timer state tracking through SmartThings device events

The tested `samsungce.cooktopHeatingPower` capability exposes burner power level
and heating mode as attributes but advertises **no commands**. SmartThings
Extended therefore does not expose remote burner-power or heating-mode controls
and does not attempt undocumented commands. Existing read-only burner entities
from Home Assistant's official SmartThings integration are not duplicated.

The countdown-timer capability does not advertise a device-specific maximum in
its schema, so the Home Assistant preparation control is conservatively capped
at 1–1440 minutes. SmartThings remains the final validator of submitted values.

### Generic command service

The integration also exposes:

`smartthings_extended.send_command`

This can send an arbitrary SmartThings capability command through the OAuth
client already owned by Home Assistant's official SmartThings integration.

## Requirements

- Home Assistant with the official SmartThings integration configured
- HACS (recommended for installation and updates)
- A compatible Samsung appliance

## Installation with HACS

1. Open HACS.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add this repository as type **Integration**.
4. Download **SmartThings Extended**.
5. Restart Home Assistant.

Existing YAML configuration remains supported as an import source:

```yaml
smartthings_extended:
```

For a specific oven you can optionally pin its SmartThings device ID:

```yaml
smartthings_extended:
  oven_device_id: "YOUR_SMARTTHINGS_DEVICE_ID"
```

On first startup the YAML data is imported into a SmartThings Extended config
entry. The imported entry is then used to load all entity platforms.

## Safety

Oven, microwave, washer and dishwasher controls can operate real appliances.
Test command changes while physically present at the appliance. Refrigerator
controls can immediately alter operating modes or convenience features.
Cooktop support intentionally does not expose burner heating control because the
tested SmartThings heating-power capability does not publish write commands.
Cooktop timer and child-lock commands can still alter the appliance state.
The integration adds safety checks where the device exposes the required state,
but users remain responsible for safe operation.

## Notes

This is an independent community project. It is not affiliated with or endorsed
by Samsung, SmartThings, Home Assistant, or the Open Home Foundation.

## License

MIT
