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

