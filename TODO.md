# TODO

## Dishwasher — deferred physical verification

The Samsung dishwasher backend is intentionally left as **not physically verified** for now. Do not treat the current lifecycle/settings implementation as production-confirmed until another on-site test session.

Before resuming dishwasher testing:

- re-check lifecycle commands against the live `dishwasherOperatingState.setMachineState(run|pause|stop)` capability rather than assuming `samsungce.dishwasherOperation.start/pause/resume/cancel` is the correct control path;
- compare the current settings flow with Home Assistant's official SmartThings handling, especially the `cancel(false)` step before changing washing course/options;
- verify whether course + washing options should be sent as one prepared/batched request for this appliance;
- test in this order while physically present: Send settings -> verify state -> Start -> Pause/Resume -> Cancel -> Cancel + drain;
- only expose the Extended dishwasher action controls in the final dashboard after those tests pass.

## Washer — map cycle codes to verified names

Washer lifecycle is physically verified and working after v0.8.2, but the prepared-program select still exposes internal Samsung course codes as `Program XX`.

Device metadata from the tested washer:

- presentation: `DA-WM-WM-01011`
- cycle reference table: `Table_02`
- supported course codes: `1C`, `2B`, `1B`, `1E`, `1D`, `96`, `8F`, `25`, `26`, `33`, `24`, `32`, `20`, `22`, `23`, `2F`, `21`, `66`, `2E`, `2D`, `30`, `29`, `27`, `28`

Do **not** blindly copy a generic `Table_02` mapping from another Samsung model. SmartThings exposes these as manufacturer-specific custom capability values and the public API does not provide reliable localized course names.

To finish this cleanly:

- capture screenshots of the complete program list shown for this washer in the SmartThings app (or manually pair app names with course codes);
- add a model/reference-table-specific mapping in `washer.py`;
- keep an explicit fallback `Program <code>` for any unmapped future code;
- preserve the raw course ID internally so command behavior and entity unique IDs do not change.

Known working appliances from the same test session: refrigerator controls, microwave prepared settings (mode/power/time batch; physical Start required), washer lifecycle after v0.8.2, and oven prepared settings + remote Start after v0.8.3.
