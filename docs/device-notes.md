# Per-device notes

Confirmed from real HA diagnostics exports (`diagnostics_raw/*.json` in
this repo, gitignored -- contains pairing key material, never committed)
pulled 2026-08-20. This supersedes the earlier research-only version of
this file. HAP type UUIDs below use the standard base
`XXXXXXXX-0000-1000-8000-0026BB765291` unless shown in full (full UUID =
vendor/custom characteristic).

## Network topology (matters for Phase 2+ live pairing work)

Not all four devices are on the same subnet:
- Ecobee, Onelink, Yardian: `192.168.1.x` (reachable now via the bridged NIC).
- **Roku is on `192.168.30.x`** (a separate VLAN/subnet) -- this is *why*
  it never appeared in `192.168.1.0/24` mDNS discovery; it's not a bug in
  the discovery approach. Live pairing/inspection of the Roku will need
  network access to that subnet too.

## Ecobee (model `ecobee3`, config entry "Home Ecobee")

**This is a HomeKit bridge exposing 9 separate HAP accessories under one
pairing**, not just a thermostat: the ecobee3 unit itself (`aid=1`, name
"Home") plus **8 SmartSensor remote sensors** (model `EBRSE4` each): Great
Room, Master, Kitchen, Office, Upstairs Office, Upstairs main, Front BD RM,
Rear Bedroom. Each remote sensor has its own Battery + Temperature +
Occupancy + Motion services -- confirms and exceeds what showed up in HA
(this is a much larger SmartSensor deployment than the 3-per-room example
seen in chat).

**Already surfaced in HA today** (9 entities under "Home", confirmed from
the diagnostics `devices` block): the `climate.home` entity itself (folds
in Current/Target Heating-Cooling State, Target Temperature, Cooling/
Heating Threshold Temperature, Target/Current Fan State), plus separately:
Current Humidity (sensor), Current Mode (select), Current Temperature
(sensor), Temperature Display Units, Identify (button), Motion
(binary_sensor), Occupancy (binary_sensor), **Clear Hold (button)** --
that last one confirms `VENDOR_ECOBEE_CLEAR_HOLD` is already wired up,
correcting an earlier assumption in this file. Same pattern (Battery/
Identify/Motion/Occupancy/Temperature) repeats per remote sensor and is
already working per the user's report.

**Correction (2026-08-20, second pass)**: an earlier version of this file
misattributed iid=49 (`4A6AE4F6-...`) to `VENDOR_ECOBEE_CURRENT_MODE`. Direct
inspection of the `aiohomekit` fork's `characteristic_types.py` (which has
these fully identified, with reverse-engineering notes citing aiohomekit
PRs #384/#548) shows the real mapping:
- `VENDOR_ECOBEE_CURRENT_MODE` is actually `B7DDB9A3-...` (iid=33 in the
  dump) -- current mode home(0)/sleep(1)/away(2)/temp(3), **`pr` only, no
  `pw`** -- read-only over HAP, confirmed. The conclusion below about
  `preset_mode` still holds, just against the correct iid.
- iid=49 (`4A6AE4F6-...`) is actually `VENDOR_ECOBEE_EQUIPMENT_RUNNING`
  (idle/heat/cool/fan/aux) -- also `pr` only. This directly contradicts the
  Phase-0 research assumption that equipment-running status "isn't
  published over HAP for Ecobee" -- on this unit, over this HomeKit path,
  it is.

**Already wired up as of this session** (all `homekit_controller_pro`-only
changes, no `aiohomekit` changes needed -- the library already modeled all
of these, they just weren't dispatched to a platform):
- `VENDOR_ECOBEE_ALERT_TEXT` (`1B1515F2-...`) → `sensor` (currently: *"Time
  to change your UV lamp. It was last changed on Jul 21, 2024."*).
- `VENDOR_ECOBEE_EQUIPMENT_RUNNING` (`4A6AE4F6-...`) → `sensor`, enum
  idle/heat/cool/fan/aux.
- `VENDOR_ECOBEE_STATUS_CODE` (`DB7BF261-...`) → `sensor`, enum
  ok/service/alert/error, diagnostic category.
- `VENDOR_ECOBEE_AUX_HEAT_ACTIVE` (`41935E3E-...`) → `binary_sensor`,
  device_class `running`.

**Caveat carried over from the aiohomekit source comments**: the value
meanings for `EQUIPMENT_RUNNING`, `STATUS_CODE`, and `AUX_HEAT_ACTIVE`
were "observed on a single unit (PR #548) and not yet independently
confirmed" -- cross-check against real behavior once live (Phase 5), the
enum label text in `sensor.py`'s two `ecobee_*_to_str` functions may need
correcting if this unit's behavior disagrees.

**Confirmed published but still NOT surfaced in HA** (real remaining gap):
- Six vendor float setpoints -- Home/Sleep/Away × target-cool/target-heat
  (values seen: 21.6/24.3, 18.9/26.1, 21.1/23.9 °C) -- `const.py`'s
  `CHARACTERISTIC_PLATFORMS` already maps these to `number`; not yet
  verified end-to-end that they actually produce working entities.
- The writable fan-speed percentage (`VENDOR_ECOBEE_FAN_WRITE_SPEED`,
  0-100%, currently 0) is mapped to `number`; its read-only counterpart
  `VENDOR_ECOBEE_FAN_READ_SPEED` (`48F62AEC-...`, value 100) is **not**
  mapped to anything -- small follow-up.
- The hold-schedule pair (`VENDOR_ECOBEE_SET_HOLD_SCHEDULE` write-only
  uint8, already mapped to `number`; `VENDOR_ECOBEE_NEXT_SCHEDULED_CHANGE_TIME`
  read/write string, currently unmapped) -- lower priority, edge-case
  scheduling data.

**Eve-pattern UUIDs on remote sensors**: each sensor's Motion and
Occupancy services carry a companion "seconds since last activation"
vendor characteristic (`BFE61C70-4A40-11E6-BDF4-0800200C9A66` and
`A8F798E0-4A40-11E6-BDF4-0800200C9A66` respectively) -- these UUID
suffixes match Elgato Eve's known custom-characteristic pattern. Check
whether `aiohomekit` already models these under its Eve vendor
characteristics before treating them as new.

## First Alert Onelink Safe & Sound (model `1039102`)

Confirmed accessory structure (one bridge, `aid=1`): Nightlight
(`LIGHTBULB` -- On/Brightness/Saturation/Hue, full RGB, already working:
`light.onelink_safe_sound_caf4_nightlight`), CO Sensor, Smoke Sensor
(both already working), and a **Battery service** (Battery Level 100%,
Charging State, Status Low Battery) that exists in HA's entity registry
but is **disabled** (`disabled_by: "user"`) -- the data path already
works, it just needs re-enabling, not new code.

**Identified (correction)**: `iid=80`, type `0000022A-...`, is
`ServicesTypes.WI_FI_TRANSPORT` -- a standard HAP service reporting the
accessory's own WiFi/network transport info (`CURRENT_TRANSPORT`,
`WI_FI_CAPABILITIES`, `WI_FI_CONFIGURATION_CONTROL`). Not vendor-specific,
not end-user actionable -- it's accessory network diagnostics, not device
data. Correctly deprioritized; not worth wiring up.

Also present but hidden from the Home app itself (`hd` permission, so
almost certainly not worth surfacing): an accessory-info characteristic
(`34AB8811-AC7F-4340-BAC3-FD6A85F9943B`) holding a version-ish string
(`"6.1;72ca72be"`) -- same pattern appears on the Ecobee and Roku too, so
this is likely a generic Apple/MFi system characteristic, not
device-specific data.

## Yardian Pro (model `PRO1900`)

Confirmed exactly as predicted from source-code inspection: 12 `Valve`
child services (5 actually configured/named: Bushes, Font [sic] Left,
Front Right, Master Bedroom, Office Sprinkler; 7 are empty placeholder
zones "MyZone6"-"MyZone12" with `Is Configured = 0`), each mapped today to
a `switch.*` entity (on/off only). The parent `IrrigationSystem` service
(`iid=32`, "Yardian Irrigation System", with real Active/Program Mode/In
Use state) previously produced zero HA entities -- `HOMEKIT_ACCESSORY_DISPATCH`
in `const.py` had no entry for it.

**Fixed this session**: added `ServicesTypes.IRRIGATION_SYSTEM: "switch"`
to `HOMEKIT_ACCESSORY_DISPATCH`, plus a new `HomeKitIrrigationSystem`
switch entity (`switch.py`) exposing Active (on/off) with Program Mode and
In Use as `extra_state_attributes`. Additive only -- doesn't touch the 12
existing per-zone entities, so no migration/breaking-change concern.
Migrating the per-zone entities themselves to HA's native `valve` domain
is still an open, separately-flagged decision (breaking change, needs an
entity-ID migration path) -- not done yet.

No additional vendor characteristics (e.g. freeze-prevent, standby-mode)
showed up in this real dump beyond Active/ProgramMode/InUse/SetDuration/
RemainingDuration/IsConfigured/ValveType/ServiceLabelIndex -- don't assume
those exist without re-checking; the earlier note about them was
speculative and isn't confirmed here.

## Roku (model `3811X`, "Master Roku")

**On a different subnet (`192.168.30.x`)** -- see Network topology above.
Confirmed richer than assumed: alongside the Television service (Active,
ConfiguredName -- writable, RemoteKey -- write-only with valid values
`[0,1,4,5,6,7,8,9,11,15,16]`, i.e. most of the standard remote buttons
work over HomeKit already), the linked services are `ACCESS_CONTROL` and a
full **Speaker service** (`iid=80`) with a **read/write Volume
characteristic (0-100%, currently 100)** and the already-working Mute --
see the Input Source correction below, there is no `INPUT_SOURCE` service
in this snapshot despite what an earlier pass of this file assumed.

**Confirmed gap, not a protocol ceiling** (before this session): HA's
`media_player.master_roku` entity had `supported_features: 18817` = PLAY +
SELECT_SOURCE + TURN_OFF + TURN_ON + PAUSE only -- no `VOLUME_SET`/
`VOLUME_MUTE`, even though the device publishes a fully read/write Volume
characteristic. This directly contradicts the general research assumption
that Roku "typically" lacks HomeKit volume control -- this unit has it, HA
just wasn't wiring it in.

**Fixed this session**: `media_player.py`'s `HomeKitTelevision` now looks
up the linked `SPEAKER` service (same `parent_service` lookup pattern
already used for `INPUT_SOURCE`/`source_list`) and adds `volume_level`,
`is_volume_muted`, `async_set_volume_level`, `async_mute_volume`, with
`VOLUME_SET`/`VOLUME_MUTE` feature bits gated on the characteristics
actually being present. The existing bolted-on `switch.master_roku_mute`
(from `SWITCH_ENTITIES` in `switch.py`, keyed on the standalone `MUTE`
characteristic) still exists too -- redundant now that the media_player
entity has native mute, not removed this pass, low priority cleanup.

**Correction**: earlier notes said the Television service had a single
fixed `INPUT_SOURCE`. Re-checked against the raw dump -- the two services
actually linked from the Television service (`iid=129` type `000000DA`,
`iid=80` type `00000113`) are **`ACCESS_CONTROL`** and **`SPEAKER`**,
*not* `INPUT_SOURCE` at all. There is no Input Source service present in
this snapshot. `ACTIVE_IDENTIFIER` is present directly on the Television
service itself with value `0`, which is falsy so `source`/`source_list`
degrade gracefully (return `None`/`[]`) rather than crashing against the
`assert input_source` in `source` -- but if that value were ever nonzero
without an actual `INPUT_SOURCE` service present, that assert would raise.
Latent fragility, not yet hit; flagged for Phase 5 hardening rather than
fixed blindly.

**Still open, needs live access**: the reported "off = shows as
unavailable" bug. Traced the relevant code path in `connection.py`
(`async_request_update`, ~line 963-996): availability flips False either
immediately on `AccessoryNotFoundError`, or after `MAX_POLL_FAILURES_TO_DECLARE_UNAVAILABLE`
consecutive `AccessoryDisconnectedError`/`EncryptionError`/`TimeoutError`
poll failures, and separately via `async_update_available_state` tied to
`aiohomekit`'s own `pairing.is_available`. Two independent paths to
"unavailable" -- can't tell which one fires while the Roku is actually off
without live testing (this snapshot was captured while on/playing). Not
guessing a fix; needs instrumentation + a real off-state test in Phase 5.
This session's diagnostics pull also confirmed the Roku sits on a
different subnet (`192.168.30.x`) from the other three devices.
