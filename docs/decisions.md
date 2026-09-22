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

## 2026-09-04: Two scanner findings judged not applicable

The `ha-dev-current` scanner flags `sensor.py`'s `self.default_name` under the
device-registry rule that retires `DeviceInfo(default_name=...)`. That
attribute is `HomeKitEntity.default_name`, the entity's own property built
from the characteristic name, and never reaches `DeviceInfo`. It also flags
the doorbell event entity under the 2027.4 `DoorbellEventType.RING` rule
because it keys on `EventDeviceClass.DOORBELL`; `DOORBELL_EVENT_VALUES`
already maps a single press to `DoorbellEventType.RING`, matching core's
`homekit_controller`. Neither site changes.


## 2026-09-22: unreachable media players may present as off

The two paired Roku accessories show every entity as `unavailable` whenever
the television is switched off. That is technically accurate, because a Roku
that is off leaves the network and stops answering HomeKit entirely, but it
reads to a user as a broken integration rather than a television someone
turned off.

HomeKit gives no way to distinguish the two. There is no "standby" or
"reachable but off" signal: the accessory is either answering or it is not.
So this cannot be fixed by reading the device more carefully, only by
choosing which of the two readings to present. That is a preference, not a
fact, so it is an option (`unreachable_media_player_as_off`, default off)
rather than a behaviour change.

When enabled, `HomeKitTelevision.available` returns True for an unreachable
accessory and `HomeKitTelevision.state` returns `MediaPlayerState.OFF`. The
default is unchanged.

The option is scoped to the media player platform and must stay that way.
Applying the same treatment to sensors would report a dead sensor as a
plausible looking value instead of as unavailable, which is precisely the
failure the STATUS_ACTIVE and low battery work exists to surface. The Rear
Bedroom SmartSensor spent over a month dead behind a healthy looking
reading. `test_option_does_not_apply_to_sensors` pins the boundary.

The separate, still open Roku issue recorded in docs/device-notes.md, that
availability may flip through either of two independent code paths in
connection.py, is not addressed here. This option changes presentation only.
It does not diagnose or change why an accessory is considered unavailable.
