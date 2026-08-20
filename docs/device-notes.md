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

**Confirmed published but NOT surfaced in HA** (real gap, verified from
the raw `entity-map`, thermostat service `iid=16`):
- Six vendor float setpoints -- Home/Sleep/Away × target-cool/target-heat
  (full UUIDs `E4489BBC-...`, `7D381BAA-...`, `73AAB542-...`,
  `5DA985F0-...`, `05B97374-...`, `A251F6E7-...`; values seen: 21.6/24.3,
  18.9/26.1, 21.1/23.9 °C) -- these look like `VENDOR_ECOBEE_*_TARGET_COOL`/
  `_HEAT`, which `const.py`'s `CHARACTERISTIC_PLATFORMS` already maps to
  `number` -- confirm the exact UUID match in Phase 2/3, but this may
  already be a solved mapping that just needs verifying end-to-end rather
  than new code.
- A writable fan-speed percentage (`C35DA3C0-...`, `pr,pw`, 0-100%,
  currently 0) and a paired read-only percentage (`48F62AEC-...`, value
  100) -- likely `VENDOR_ECOBEE_FAN_WRITE_SPEED` (write) plus an actual
  readback; only the write side is in `CHARACTERISTIC_PLATFORMS` today.
- **A maintenance-alert string** (`1B1515F2-CC45-409F-991F-C480987F92C3`,
  read-only, currently: *"Time to change your UV lamp. It was last changed
  on Jul 21, 2024."*) -- not modeled anywhere in `aiohomekit` today. This
  is a genuinely new, useful diagnostic-sensor candidate and maps directly
  to the "identify and notify severe/notable events" goal from the
  original brief.
- Two unidentified status characteristics (`DB7BF261-...` uint8 0-3, value
  0; `41935E3E-...` bool, value false) and a hold-schedule-looking pair
  (`1B300BC2-...` write-only uint8 0-3; `1621F556-...` read/write string,
  currently `"2014-01-03T00:00:00-05:00R"`) -- identity not confirmed, flag
  for direct lookup against HAP spec / aiohomekit source in Phase 2 rather
  than guessing further.

**Important correction to the Phase 3 plan**: `VENDOR_ECOBEE_CURRENT_MODE`
(the characteristic backing the "Current Mode" select, iid=49) has **only
`pr` permission in the real data -- no `pw`**. It cannot be written over
HAP at all. This likely explains the "Current Mode reporting unreliable"
complaints found in research (a write attempt against a read-only
characteristic would fail/no-op). It also means folding this into the
climate entity's `preset_mode` (which implies user-settable) needs
rethinking -- the mode may only ever be legitimately read-only over
HomeKit regardless of which HA entity type wraps it. Confirm this can't be
set via *any* other characteristic before assuming preset_mode is viable.

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

**Unidentified service worth investigating in Phase 2**: `iid=80`, type
`0000022A-...`, with child characteristics using the unusual `tw`
(timed-write) and `wr` (write-response) permission flags on a `tlv8`
value -- this permission combination is characteristic of HAP's
firmware-update-over-HAP mechanism, but that's a guess, not confirmed.
Look this up directly against `aiohomekit`'s `ServicesTypes`/
`CharacteristicsTypes` or the HAP spec rather than assuming.

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
Use state) **produces zero HA entities today** -- `HOMEKIT_ACCESSORY_DISPATCH`
in `const.py` has no entry for it, confirmed directly in the source. This
is the cleanest, most concrete Phase 3 target of the four devices.

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
work over HomeKit already) and a single fixed InputSource, there's a full
**Speaker service** (`iid=80`) with a **read/write Volume characteristic
(0-100%, currently 100)** and the already-working Mute.

**Confirmed gap, not a protocol ceiling**: HA's `media_player.master_roku`
entity has `supported_features: 18817` = PLAY + SELECT_SOURCE + TURN_OFF +
TURN_ON + PAUSE only -- **no `VOLUME_SET` or `VOLUME_MUTE` feature bits**,
even though the device publishes a fully read/write Volume characteristic
and Mute is exposed as a bolted-on separate `switch.master_roku_mute`
entity instead of a native media_player volume control. This directly
contradicts the general research assumption that Roku "typically" lacks
HomeKit volume control -- this unit has it, HA just isn't wiring it into
the media_player entity properly. Concrete, verified Phase 3 fix.

This snapshot was captured while the TV was on/playing, so it doesn't
show the reported "off = unavailable" bug directly -- that still needs a
diagnostics pull (or live inspection) while the TV is actually off.
