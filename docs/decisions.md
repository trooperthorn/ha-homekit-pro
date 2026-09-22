# Decisions

## 2026-09-03: HACS "brands" check ignored

HACS validation fails the `brands` check unless a repository either ships
`custom_components/homekit_controller_pro/brand/icon.png` or is listed in
the home-assistant/brands repository. This repository is a personal fork
installed directly by URL, not a submission to the HACS default store or
to home-assistant/brands, and has no icon artwork to ship. `validate.yml`
ignores the `brands` check rather than fabricating a placeholder icon;
revisit if real brand artwork is ever produced.

## 2026-09-03: removed the space in the aiohomekit requirement URL

`manifest.json`'s `aiohomekit` requirement used the PEP 508 direct-URL form
`aiohomekit @ https://...`. hassfest hard-rejects any requirement string
containing a space, so this failed manifest validation the first time this
repository actually ran hassfest in CI. PEP 508's grammar does not require
whitespace around `@`; the requirement is now `aiohomekit@https://...`,
which `packaging.requirements.Requirement` parses identically.

## Undated: lowercase homekit_id storage workaround

An earlier version of this integration stored a pairing's `homekit_id` in
the entity-map storage cache in lowercase for some pairings. `async_delete_map`
checks both the stored ID and its lowercased form when deleting a cache
entry, so a cache entry written under the old lowercase behavior is still
found and removed. The workaround stays until the storage format is
verified clean of lowercase-keyed entries across all installs, which cannot
be confirmed from this repository alone.

## 2026-09-22: STATUS_ACTIVE surfaced, STATUS_LO_BATT suppression rule changed

The Rear Bedroom ecobee remote sensor failed on 2026-08-20 and reported it
three independent ways -- `STATUS_ACTIVE` false on all three of its copies,
`STATUS_LO_BATT` set on all four of its copies, and `Current Temperature`
pinned at its declared `maxValue` sentinel (100.0 C) -- while the
integration surfaced only `BATTERY_LEVEL=100`, the one value that was
actually wrong (see docs/device-notes.md). Two changes:

- `STATUS_ACTIVE` is now surfaced as a diagnostic binary sensor
  (`BinarySensorDeviceClass.CONNECTIVITY`, `True` means the sensor is
  actively reporting valid data; see
  `homeassistant/components/binary_sensor/__init__.py` line 47 in the core
  2026.9.1 reference clone: "On means connected, Off means disconnected").
  Registered in both `binary_sensor.CHARACTERISTIC_BINARY_SENSORS` and
  `const.CHARACTERISTIC_PLATFORMS`; each remote sensor exposes three copies
  (Motion/Occupancy/Temperature services) and only one becomes an entity.
  A name- or service-label-based duplicate key (the approach already used
  for low battery dedup elsewhere in this file's history) does not work
  here: each service's own `NAME` characteristic differs from the others
  (e.g. "Rear Bedroom Motion" vs "Rear Bedroom Occupancy" vs "Rear Bedroom
  Temperature"), so a same-key comparison never matches and all three
  copies would become separate entities. `_is_earliest_service_for_characteristic`
  instead picks whichever service has the lowest `iid`, unconditionally, with
  no name-based scoping (kept as a separate function from the low battery
  dedup helper for that reason, rather than sharing one).
- `STATUS_LO_BATT` no longer suppresses every copy just because the
  accessory has a `BATTERY_SERVICE`. The old rule
  (`_should_skip_low_battery_characteristic`) rejected the battery
  service's own copy outright and then rejected the rest whenever any
  `BATTERY_SERVICE` existed at all, producing zero low battery entities on
  any accessory whose battery service also reports `BATTERY_LEVEL` (every
  ecobee SmartSensor). The new rule (`_is_chosen_low_battery_characteristic`)
  creates exactly one low battery entity per accessory: the battery
  service's own copy when the battery service exposes `STATUS_LO_BATT`,
  otherwise the earliest remaining copy by service iid. This is additive
  for existing users: it only creates entities where none existed, no
  entity that previously existed disappears or changes ID.
- `HomeKitBatterySensor.extra_state_attributes` now includes `low_battery`
  (bool, from the existing `is_low_battery` property) as a belt-and-braces
  measure, so the contradiction is visible even on an accessory where no
  low battery binary sensor entity ends up being created for some other
  reason.
- Range/clamp validation on `Current Temperature` was explicitly considered
  and rejected: 100.0 C sits exactly at the characteristic's own declared
  `maxValue`, so a clamp or range check would treat it as a valid boundary
  value and would not have caught this. `STATUS_ACTIVE` is the correct
  detector for "this reading is not real data," not a value-range check.

### Tests must drive the dispatch path, not just the entity classes

The first version of these tests constructed `CharacteristicBinarySensor`
and `HomeKitBatterySensor` objects directly and asserted on `is_on` and
`native_value`. Those assertions are worth keeping, but on their own they
would have passed before the fix as well: the entity classes were never
broken, they were simply never instantiated, because
`async_add_characteristic` returned `False`.

`tests/conftest.py` therefore grew `dispatch_platform`, which runs a
platform's real `async_setup_entry`, captures the service listeners and
characteristic factories it registers, drives them over the whole entity
map, and returns the entities that were actually added. Entity counts from
that helper are what pin the regression: the low battery count was 0 before
this change and is 8 after.

The two dispatch tables are covered separately because they fail
differently. `CHARACTERISTIC_PLATFORMS` in `const.py` is consumed by
`connection.py` to decide which platform is offered a characteristic, so it
is not exercised by driving a single platform's factory; a direct assertion
covers it. `CHARACTERISTIC_BINARY_SENSORS` in the platform is covered by the
entity counts. Both mutations were verified to fail the suite before this
was committed. Registering a characteristic in one table only is the live
defect behind the missing ecobee `number` entities, so this pairing is the
guard against repeating it on a new characteristic.

## 2026-09-04: Two scanner findings judged not applicable

The `ha-dev-current` scanner flags `sensor.py`'s `self.default_name` under the
device-registry rule that retires `DeviceInfo(default_name=...)`. That
attribute is `HomeKitEntity.default_name`, the entity's own property built
from the characteristic name, and never reaches `DeviceInfo`. It also flags
the doorbell event entity under the 2027.4 `DoorbellEventType.RING` rule
because it keys on `EventDeviceClass.DOORBELL`; `DOORBELL_EVENT_VALUES`
already maps a single press to `DoorbellEventType.RING`, matching core's
`homekit_controller`. Neither site changes.

