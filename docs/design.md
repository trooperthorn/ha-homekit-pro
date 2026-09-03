# Architecture and design rationale

## Lazy platform forwarding

`HKDevice` (`connection.py`) tracks which platforms it has already forwarded
the config entry to in `self.platforms`. A bridge accessory can grow new
child accessories after initial setup, which may need platforms nothing on
the bridge needed before; forwarding is done incrementally rather than
forwarding every platform up front (unnecessary for a single lightbulb) and
never forwarding the same platform twice, which `hass.config_entries`
treats as an error.

## Forced update at setup

Entities are added via dispatching, and each entity only subscribes to the
characteristics it cares about inside its own `async_added_to_hass`, which
runs after the entity is added. That is too late for the coordinator-style
update in `async_process_entity_map` to have picked up fresh values for
those characteristics. `async_setup` forces an explicit update (or, for BLE
with an already-known accessory, schedules one after Home Assistant finishes
starting) precisely so entities are added with real data rather than
whatever was last observed. See [protocol.md](protocol.md) for the BLE GSN
and IP staleness details this same call also handles.

## Device registry: legacy identifier collisions

A device can be found under a legacy identifier that spans several config
entries at once (`async_migrate_devices` in `connection.py`). Looking it up
with `device_registry.async_get_device` in that case returns a read-only
composite view, and updating it with `async_update_device` would silently
drop the identifier rename instead of applying it to the right entry. The
lookup is scoped to this config entry's own candidates
(`async_get_devices(identifiers=...)`) instead, so the rename only touches
the device this entry actually owns.

## Stale entity registry cleanup

`async_remove_stale_entities` builds a set of `(unique_id, aid, sid, iid)`
tuples from every registry entry that belongs to the current config entry,
using `None` for the parts that do not apply: a service-level entity has no
characteristic `iid`, and an accessory-level entity has neither a service
`sid` nor a characteristic `iid`. The tuple shape lets one set comparison
find entities that no longer correspond to anything in the current entity
map, at any of the three levels.

## `entity_map` reads live from the pairing

`HKDevice.entity_map` is a property that returns
`self.pairing.accessories_state.accessories` on every access, not a cached
attribute; `async_process_entity_map` and everything that reads
`self.entity_map` (workaround detection, device migration, entity creation)
always sees whatever the `Pairing` object currently holds. An older version
of this code apparently needed to push a fetched entity map onto the
`Pairing` object explicitly, based on a comment to that effect that no
longer matches this property-based implementation; that comment has been
removed rather than preserved, since it described behavior that is not
true of the current code (unverified whether it was ever accurate, or
simply drifted from an earlier `entity_map` implementation).

## Entity removal ordering

`_async_handle_entity_removed` unsubscribes from HomeKit characteristics
before scheduling the entity's actual removal. `async_will_remove_from_hass`
would also unsubscribe, but only runs once Home Assistant finishes removing
the entity, which is too late to stop an update from an already-removed
characteristic reaching it in between.

## Fresh characteristic lists on re-setup

`BaseCharacteristicEntity.setup` allocates new `pollable_characteristics`
and `watchable_characteristics` lists instead of clearing the existing ones,
because the previous lists were already passed to the connection layer;
mutating them in place would change what the connection sees for the
in-flight generation of the entity as well as the new one.

## Config flow: cleaning up an orphaned complete entry

`async_step_zeroconf` removes an existing "complete" config entry
automatically when the accessory reports itself as unpaired but the stored
entry still has an `AccessoryPairingID` and the entry was not deliberately
ignored by the user. A complete entry with no matching pairing on the
accessory almost always means the accessory was reset or re-paired
elsewhere; leaving the stale entry around would block re-adding it under
its now-correct pairing state.

## Config flow: the M1 pairing phase and displayed pins

`async_step_pair` doubles as the M1 phase (no pairing code yet) and the step
that submits a code once the user has one. A device without a display uses
a static code the user already knows. A device with a display needs
`async_start_pairing` called first so it shows a random pin, but that call
should only happen once the user actually clicks "Configure" in the UI, not
at discovery time — otherwise every discovered device would start pairing
mode unprompted. Calling `async_start_pairing` returns a callable that the
flow later calls with the code the user types in.

## Config flow: caching the accessories list separately

Most of a pairing record is stable enough to store directly on the config
entry, but the `accessories` key is comparatively volatile (it reflects the
current entity map) and is cached elsewhere rather than on the entry.
`_entry_from_accessory` copies the pairing data before mutating it, and
reads the accessories list from whatever the pairing operation just
produced when available, falling back to a fresh API request; both paths
remove the `accessories` key from `pairing_data` in the process so the
volatile part never ends up stored on the entry alongside the stable part.

## Device triggers: one trigger source per accessory

A bridge cannot host a doorbell and a remote control as separate trigger
sources under the same device ID; iOS's own HomeKit support does not do
this either, as far as this integration's testing has confirmed. Device
trigger setup refuses to register a second trigger source for a device ID
that already has one; the two devices have to be separate accessories
(they can still share the same bridge).
