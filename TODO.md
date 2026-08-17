# TODO

## Refrigerator — physical verification of v0.8.6 controls

The v0.8.5 refrigerator diagnostics captured the appliance's advertised capability schemas, and v0.8.6 implemented the remaining schema-confirmed controls: interior-lighting brightness, gradual brightening, the door-alarm master on/off switch and ice-maker Night Mode schedule editing.

Still pending an on-site test session:

- verify the new interior-lighting brightness selector matches the brightness setting shown in the SmartThings app (the previous confusion was caused by the separate night-light brightness attribute);
- verify the door-alarm on/off switch; the appliance reports the `doorAlarm` attribute as `null` until it first changes, so the switch may start in an unknown state;
- verify Night Mode schedule editing end to end (set start/end in Home Assistant, confirm in the SmartThings app and on the appliance).

The general rule stands: do not guess private `samsungce.*` command names; implement only commands advertised by the appliance's capability schemas.

## Dishwasher — deferred physical verification

The Samsung dishwasher backend is intentionally left as **not physically verified** for now. Do not treat the current lifecycle/settings implementation as production-confirmed until another on-site test session.

Before resuming dishwasher testing:

- re-check lifecycle commands against the live `dishwasherOperatingState.setMachineState(run|pause|stop)` capability rather than assuming `samsungce.dishwasherOperation.start/pause/resume/cancel` is the correct control path;
- compare the current settings flow with Home Assistant's official SmartThings handling, especially the `cancel(false)` step before changing washing course/options;
- verify whether course + washing options should be sent as one prepared/batched request for this appliance;
- test in this order while physically present: Send settings -> verify state -> Start -> Pause/Resume -> Cancel -> Cancel + drain;
- only expose the Extended dishwasher action controls in the final dashboard after those tests pass.

## Washer — verified state

Washer lifecycle is physically verified and working after v0.8.2.

For the tested washer (`DA-WM-WM-01011`, cycle reference table `Table_02`), the complete SmartThings app cycle list was captured and mapped in v0.8.4. The integration keeps raw Samsung course IDs internally and exposes friendly Polish program names in Home Assistant. Unknown tables/codes retain the safe `Program <code>` fallback.

Known working appliances from the same test session: refrigerator controls, microwave prepared settings (mode/power/time batch; physical Start required), washer lifecycle after v0.8.2, washer friendly cycle labels after v0.8.4, and oven prepared settings + remote Start after v0.8.3.
