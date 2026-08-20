# Per-device notes

Confirmed facts only -- update this from live diagnostics (Phase 1), not
from public reviews/community reports. Generic reports have already been
wrong once here (see Ecobee).

## Ecobee thermostat

**Model**: older-generation ecobee (exact model TBD from Phase 1 diagnostics).

**Confirmed working via HomeKit today** (from live HA entity state, 2026-08-20):
- Full climate control: `hvac_modes` off/heat/cool/heat_cool, `fan_modes`
  on/auto, current/target temperature, current/target humidity.
- Per-room remote sensors: temperature, motion, and occupancy all exposed
  and working -- this directly contradicts generic community reports
  claiming Ecobee's HomeKit firmware never exposes SmartSensor data. That
  ceiling does not apply to this unit; do not assume it without re-checking
  per device.
- "Current Mode" (home/sleep/away) surfaces as its own separate entity (a
  select with those three options), not as the climate entity's
  `preset_mode`. Confirmed from live `supported_features: 399` -- decodes
  to TARGET_TEMPERATURE + TARGET_TEMPERATURE_RANGE + TARGET_HUMIDITY +
  FAN_MODE + TURN_ON + TURN_OFF, with no PRESET_MODE bit (16) set.

**Known rough edges from research** (home-assistant/core issues, upstream
closed "Not planned"): fan-state-while-idle display bug, current-mode
(home/sleep/away) reporting reliability, AUX-mode control. Verify against
this specific unit in Phase 1 before assuming any of these apply here.

**Sample entity snapshot** (climate.home, 2026-08-20, for reference):
```yaml
state: cool  # hvac_action: idle
current_temperature: 77
temperature: 76
current_humidity: 48
humidity: 36  # target humidity setpoint
fan_mode: auto
supported_features: 399
```

## First Alert Onelink Safe & Sound (model 1039102)

Public-review baseline (AppleInsider, 2018, for the Safe & Sound variant):
3 HomeKit accessories -- Smoke Sensor, Carbon Monoxide Sensor, and a
nightlight exposed as a light bulb (brightness + color). Not yet confirmed
against this exact unit/firmware -- do that in Phase 1.

Two known upstream BLE pairing-failure bugs, both closed "Not planned",
never fixed: [core#77926](https://github.com/home-assistant/core/issues/77926)
(fails consistently regardless of prior Wi-Fi state), [core#80451](https://github.com/home-assistant/core/issues/80451)
(times out during the post-pair disconnect phase). This device has zero
native-integration fallback -- HomeKit is the only path -- so pairing
reliability (Phase 2) is the highest-risk, highest-value workstream.

## Yardian Pro irrigation controller

HomeKit exposes `Valve` per zone (mapped in stock `homekit_controller` to
the `switch` domain, on/off only -- no duration write support, confirmed
by source inspection) plus an `IrrigationSystem` parent service that stock
`homekit_controller` doesn't map to any entity at all today.

Native `yardian` HA integration is local and strictly richer (per-zone
duration control), which is why the user chose to improve the HomeKit path
anyway for consistency rather than to close a capability gap.

## Roku TV

Confirmed bug (user-reported, 2026-08-20): when the Roku is off, it shows
as unavailable/"lost" in HA rather than a clean `off` state. Likely cause:
`homekit_controller`/`aiohomekit` conflating "accessory in standby, slow to
accept new connections" with "accessory unreachable." Fix target for Phase 3.

HomeKit's Television service is a hard ceiling vs. Roku's native ECP
protocol (no full app catalog, no deep-linking, typically no volume) --
this is protocol-level, not a code gap; don't chase parity with the native
`roku` integration here.
