# Cutover: moving an accessory from `homekit_controller` to this fork

This integration is a fork of core's `homekit_controller` under a different
domain (`homekit_controller_pro`). The two can be installed side by side and
neither knows about the other, so moving an accessory across is a manual,
per-accessory operation.

## Why the fork cannot discover an already paired accessory

A HomeKit accessory advertises a status flag whose `0x01` bit means "not yet
paired". Discovery reads that bit and refuses to offer a pairing form for an
accessory that already belongs to some other controller:

```
config_flow.py:355
    if paired:
        # Device is paired but not to us - ignore it
        return self.async_abort(reason="already_paired")
```

The user-visible result is "No unpaired devices could be found", or, if the
accessory is reached by an explicit flow rather than discovery, the
`already_paired` message in `strings.json`: "This accessory is already paired
to another device. Please reset the accessory and try again."

HAP does allow an accessory to hold more than one controller pairing, but
only an already paired admin controller can add another one, and Home
Assistant exposes no way to issue that. There is therefore no way to join
alongside the stock integration. The stock pairing has to be released first.

Unpairing from `homekit_controller` does not affect the accessory's pairing
with Apple Home, or with any other controller. Those are independent pairings
held by the accessory. An iPhone paired to the same accessory keeps working.

## What deleting the stock config entry actually does

It is not just a local forget. The stock integration removes the pairing on
the accessory itself, which is what makes it discoverable again. This fork
inherits the same code:

```
__init__.py:113
    await controller.remove_pairing(hkid)
```

The accessory must be reachable at that moment. If it is not, removal
succeeds locally and only logs a warning:

```
__init__.py:115
    "Accessory %s was removed from HomeAssistant but was not reachable to
     properly unpair. It may need resetting before you can use it with
     HomeKit again"
```

That is the failure case worth planning around. See "Recovering a failed
unpair" below.

## Before you start

- [ ] The accessory's 8 digit HomeKit setup code is in hand. For the ecobee3
      it is on the thermostat's own HomeKit screen and on the card that
      shipped with it. Without it the accessory cannot be re-paired, and the
      stock pairing is already gone by the time you find that out.
- [ ] The accessory is online and reachable from the Home Assistant host.
      Confirm in the UI that its entities are not `unavailable`.
- [ ] This fork is installed and loaded (Settings, Devices & Services shows
      "HomeKit Device Pro" as an available integration).
- [ ] You have a recent backup, or at minimum have noted the entity IDs this
      accessory currently owns.

## The cutover, one accessory at a time

Do not delete several stock entries and then pair them all. Each accessory
is independent, and batching them means a failure in the middle leaves you
unsure which ones are unpaired.

1. Settings, Devices & Services, HomeKit Device. Delete the single config
   entry for this accessory. This unpairs it and deletes its entities.
2. Wait for the accessory to re-advertise as unpaired. This is normally under
   a minute. A discovered card for it appears under HomeKit Device Pro.
3. Pair it with the setup code.
4. Confirm the entity IDs came back unsuffixed (see below) and that the
   entities are reporting real values, not just present.

Repeat for the next accessory only once the previous one is confirmed
working.

### Entity IDs: why delete and pair in one sitting

Entity IDs are reclaimed, not transferred. Deleting the stock config entry
deletes its entity registry entries, which frees names like
`sensor.kitchen_temperature`. If you pair with the fork promptly, the new
entities take those same IDs and existing dashboards and automations keep
working untouched.

If the stock entry is left in place, or left deleted for long enough that
something else claims the name, the fork's entities arrive as
`sensor.kitchen_temperature_2` and every reference to them breaks. There is
no automatic fix for this; it is a manual rename per entity.

### Ordering

Move low-stakes accessories first and the thermostat last. Between the delete
and a successful pair there is no climate entity at all, so any automation
that drives heating or cooling has nothing to act on. The Rokus and the
remote sensors are safe to move on an ordinary day; the ecobee3 is not.

There is no requirement to move everything. The two integrations coexist, so
leaving some accessories on stock `homekit_controller` indefinitely is a
supported end state.

## Recovering a failed unpair

If the accessory was unreachable when the stock entry was deleted, Home
Assistant has forgotten the pairing but the accessory has not. It still
advertises as paired, so the fork will refuse it with `already_paired`, and
nothing in Home Assistant can release it any more: the keys needed to send a
remove-pairing request went with the deleted config entry.

The only route back is a HomeKit reset on the accessory itself, which is a
vendor specific procedure, not a HomeKit one. That reset also drops every
other controller's pairing, including Apple Home, so those have to be
re-added afterwards.

This is the reason the reachability check is a precondition and not a
suggestion.

## After the cutover

- The fork's option `unreachable_media_player_as_off` is off by default. If
  the Roku accessories showing as unavailable when the television is off is
  what prompted the move, turn it on per entry under the integration's
  Configure button. See [decisions.md](decisions.md), 2026-09-22.
- Diagnostics exports from the fork use the new domain, so any previously
  captured export under `homekit_controller` is now historical. The
  per-accessory facts drawn from those exports are in
  [device-notes.md](device-notes.md).

## The alternative, and why it is not recommended

The pairing keys live in the config entry's `data`, and the cached accessory
structure lives in a store keyed by domain:

```
storage.py:13
    ENTITY_MAP_STORAGE_KEY = f"{DOMAIN}-entity-map"
```

So with Home Assistant stopped, an entry in `.storage/core.config_entries`
can be duplicated under the `homekit_controller_pro` domain and the matching
block copied from `homekit_controller-entity-map` into
`homekit_controller_pro-entity-map`. The accessory is never unpaired, no
setup code is needed, and there is no gap in service.

It is not recommended:

- It is hand editing `.storage`, where a malformed file takes down far more
  than this integration.
- If both config entries ever load at once, two controllers are using one set
  of pairing keys against the same accessory. That state is not tested here
  and the accessory's own behaviour under it is unverified.
- It is untested in this repository. The delete-and-pair path is the one the
  code is written for.

Use it only if an accessory's setup code is genuinely unobtainable and a
HomeKit reset is not acceptable.
