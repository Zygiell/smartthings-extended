# SmartThings Extended

Experimental Home Assistant custom integration that extends the official
SmartThings integration with Samsung appliance capabilities that Home Assistant
does not currently expose as native entities.

> **Status:** experimental. This project reuses the authenticated OAuth client
> from Home Assistant's official `smartthings` integration. It does not store
> a separate SmartThings PAT.

## Current support — v0.2.1

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

Then add to `configuration.yaml`:

```yaml
smartthings_extended:
```

For a specific oven you can optionally pin its SmartThings device ID:

```yaml
smartthings_extended:
  oven_device_id: "YOUR_SMARTTHINGS_DEVICE_ID"
```

Restart Home Assistant after changing YAML configuration.

## Safety

Oven controls can operate a real heating appliance. Test commands while
physically present at the appliance. The integration deliberately refuses a
remote `Start` when Smart Control is disabled, but users remain responsible for
safe operation.

## Notes

This is an independent community project. It is not affiliated with or endorsed
by Samsung, SmartThings, Home Assistant, or the Open Home Foundation.

## License

MIT
