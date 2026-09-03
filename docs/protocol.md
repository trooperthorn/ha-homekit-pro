# HomeKit Accessory Protocol (HAP) and device facts

Verified rows come from reading this integration's own code and the
[aiohomekit](https://github.com/trooperthorn/aiohomekit) fork it depends on.
Unverified rows describe behavior that affects the code but has not been
confirmed against Apple's own HAP specification.

## Pairing error codes

`config_flow.py`'s pairing step maps every one of these HAP-level failures to
the same user-facing `authentication_error`; the underlying HAP stage tells
you which side rejected the exchange when debugging a failed pairing:

| Stage | Failure | Status |
| --- | --- | --- |
| PairSetup M4 | SRP proof failed | Verified |
| PairSetup M6 | Ed25519 signature verification failed | Verified |
| PairVerify M4 | Decryption failed | Verified |
| PairVerify M4 | Device not recognised | Verified |
| PairVerify M4 | Ed25519 signature verification failed | Verified |

## BLE accessory state

- The GATT sequence number (GSN) is restored from the accessory on
  reconnect; a catch-up poll fires automatically via disconnected events if
  the GSN shows the device is out of sync. If the BLE connection failed
  before Home Assistant finished starting, `async_setup` schedules one more
  forced update once `EVENT_HOMEASSISTANT_STARTED` fires, to be sure. Verified.
- HAP over BLE has no "device went away" callback; a disconnect is not the
  same as unavailability. The integration polls periodically on a timer to
  detect a BLE accessory going unavailable instead of relying on a callback.
  Verified.

## IP accessory state after restart

The `/accessories` endpoint can return cached values from the accessory's
own perspective even though `async_populate_accessories_state` already
fetched the accessory database. Ecobee thermostats have been observed
reporting a stale value (for example 100C) in `/accessories` right after a
restart. `async_setup` explicitly polls all characteristics
(`poll_all=True`) before processing the entity map, because entities have
not registered which characteristics they care about yet at that point.
Verified for Ecobee; unverified whether other vendors exhibit the same
staleness.

## Thread status bitmask

`ThreadStatus` (`sensor.py`) is a bitmask, checked in an order that matters:
a device can be both a router and the network's leader, or both a router
and the border router, so the checks test the more specific role first.
`BORDER_ROUTER` bridges the Thread network to WiFi/Ethernet; `LEADER` is
unique per network and manages which nodes are routers; a plain `ROUTER`
participates in mesh routing without either extra role. Verified against
the bitmask definition.

## Climate characteristics

Two different accessory generations expose the target HVAC mode under
different characteristics with different value ranges:

| Characteristic | Values | Meaning |
| --- | --- | --- |
| `TARGET_HEATER_COOLER_STATE` | 0-2 (Auto, Heat, Cool) | Should the device start heating/cooling when the room crosses the target temperature. |
| `HEATING_COOLING_TARGET` | 0-3 (Off, Heat, Cool, Auto) | Same concept, older characteristic with an explicit Off value. |

Both are verified against the accessory characteristic definitions used in
`climate.py`.

## Vendor quirks

| Vendor | Quirk | Status |
| --- | --- | --- |
| Ecobee | Clearing a hold: writing `true` alone is not always applied. The accessory appears to cache the characteristic's state and ignore a write it thinks has no effect, so `HomeKitClearHoldButton` writes `false` then `true` to force the change through. | Verified |
| Some HomeKit lights | Implement color temperature using HUE/SATURATION instead of `COLOR_TEMPERATURE`, because the HAP spec does not technically permit `COLOR_TEMPERATURE` and HUE/SATURATION to be present on the same service at once. `light.py` falls back to converting a requested color temperature to HS for these devices. | Verified |

## Entity registry migration

`async_get_entity_id` takes the platform in the domain-shaped argument and
the domain (`homekit_controller_pro`) in the platform-shaped argument when
looking up a legacy unique ID, because HomeKit's early entity IDs were built
as `PLATFORM.INTEGRATION` instead of today's `INTEGRATION.PLATFORM`. This is
a HA-history fact, not a HomeKit protocol fact, but it only makes sense
next to the migration code that still has to account for it.
