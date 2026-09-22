"""Regression tests for the 2026-08-20 Rear Bedroom dead-sensor failure.

The Rear Bedroom ecobee SmartSensor reported a dead battery three
independent ways (STATUS_ACTIVE false, STATUS_LO_BATT true on both its
BATTERY_SERVICE and characteristic-scoped copies, and a saturated
Current Temperature reading pinned at the characteristic's own declared
maxValue) while the only HA entity that existed for it, the native
Battery Level sensor, kept reporting a healthy 100%. These tests pin
that contradiction against the real captured data in
tests/fixtures/ecobee_entity_map.json, and confirm the fix: a
status-active binary sensor exists and reflects STATUS_ACTIVE, a
low-battery binary sensor exists and reflects STATUS_LO_BATT, and both
are deduplicated to exactly one entity per accessory even though the
underlying characteristic is repeated across three or four services.
"""

from aiohomekit.model.characteristics import CharacteristicsTypes

from custom_components.homekit_controller_pro.binary_sensor import (
    CHARACTERISTIC_BINARY_SENSORS,
    CharacteristicBinarySensor,
    HomeKitBatteryLowSensor,
    _is_chosen_low_battery_characteristic,
    _is_earliest_service_for_characteristic,
    async_setup_entry as binary_sensor_async_setup_entry,
)
from custom_components.homekit_controller_pro.const import CHARACTERISTIC_PLATFORMS
from custom_components.homekit_controller_pro.sensor import HomeKitBatterySensor

from .conftest import (
    FakeHKDevice,
    dispatch_platform,
    load_entity_map_from_list,
    load_raw_entity_map,
)

# aiohomekit's Accessories collection keys accessories by their (large,
# non-sequential) `aid`, as pulled straight from the real HAP dump.
REAR_BEDROOM_AID = 4295591051
GREAT_ROOM_AID = 4295148922

STATUS_LO_BATT_DESCRIPTION = CHARACTERISTIC_BINARY_SENSORS[
    CharacteristicsTypes.STATUS_LO_BATT
]
STATUS_ACTIVE_DESCRIPTION = CHARACTERISTIC_BINARY_SENSORS[
    CharacteristicsTypes.STATUS_ACTIVE
]


def _low_battery_sensor(
    fake_ecobee: FakeHKDevice, aid: int, service_iid: int
) -> CharacteristicBinarySensor:
    service = fake_ecobee.entity_map.aid(aid).services.iid(service_iid)
    char = service[CharacteristicsTypes.STATUS_LO_BATT]
    return CharacteristicBinarySensor(
        fake_ecobee, {"aid": aid, "iid": service_iid}, char, STATUS_LO_BATT_DESCRIPTION
    )


def _status_active_sensor(
    fake_ecobee: FakeHKDevice, aid: int, service_iid: int
) -> CharacteristicBinarySensor:
    service = fake_ecobee.entity_map.aid(aid).services.iid(service_iid)
    char = service[CharacteristicsTypes.STATUS_ACTIVE]
    return CharacteristicBinarySensor(
        fake_ecobee, {"aid": aid, "iid": service_iid}, char, STATUS_ACTIVE_DESCRIPTION
    )


def test_rear_bedroom_low_battery_sensor_is_on(fake_ecobee: FakeHKDevice) -> None:
    """The dead Rear Bedroom sensor's BATTERY_SERVICE STATUS_LO_BATT was 1."""
    sensor = _low_battery_sensor(fake_ecobee, REAR_BEDROOM_AID, service_iid=192)

    assert sensor.is_on is True


def test_rear_bedroom_status_active_sensor_is_not_active(
    fake_ecobee: FakeHKDevice,
) -> None:
    """The dead Rear Bedroom sensor's STATUS_ACTIVE was false on every service."""
    sensor = _status_active_sensor(fake_ecobee, REAR_BEDROOM_AID, service_iid=56)

    assert sensor.is_on is False


def test_great_room_low_battery_sensor_is_off(fake_ecobee: FakeHKDevice) -> None:
    """Great Room was healthy: STATUS_LO_BATT was 0. Verified against the fixture."""
    sensor = _low_battery_sensor(fake_ecobee, GREAT_ROOM_AID, service_iid=192)

    assert sensor.is_on is False


def test_great_room_status_active_sensor_is_active(fake_ecobee: FakeHKDevice) -> None:
    """Great Room was healthy: STATUS_ACTIVE was true. Verified against the fixture."""
    sensor = _status_active_sensor(fake_ecobee, GREAT_ROOM_AID, service_iid=56)

    assert sensor.is_on is True


def test_rear_bedroom_low_battery_has_exactly_one_chosen_characteristic(
    fake_ecobee: FakeHKDevice,
) -> None:
    """Rear Bedroom exposes STATUS_LO_BATT on 4 services; exactly 1 becomes an entity."""
    accessory = fake_ecobee.entity_map.aid(REAR_BEDROOM_AID)
    candidates = [
        service[CharacteristicsTypes.STATUS_LO_BATT]
        for service in accessory.services
        if service.has(CharacteristicsTypes.STATUS_LO_BATT)
    ]

    assert len(candidates) == 4
    chosen = [c for c in candidates if _is_chosen_low_battery_characteristic(c)]
    assert len(chosen) == 1
    # The BATTERY_SERVICE's own copy (service iid 192) is preferred.
    assert chosen[0].service.iid == 192


def test_rear_bedroom_status_active_has_exactly_one_chosen_characteristic(
    fake_ecobee: FakeHKDevice,
) -> None:
    """Rear Bedroom exposes STATUS_ACTIVE on 3 services; exactly 1 becomes an entity."""
    accessory = fake_ecobee.entity_map.aid(REAR_BEDROOM_AID)
    candidates = [
        service[CharacteristicsTypes.STATUS_ACTIVE]
        for service in accessory.services
        if service.has(CharacteristicsTypes.STATUS_ACTIVE)
    ]

    assert len(candidates) == 3
    chosen = [c for c in candidates if _is_earliest_service_for_characteristic(c)]
    assert len(chosen) == 1
    # The earliest (lowest iid) service is Motion, iid 56.
    assert chosen[0].service.iid == 56


def test_great_room_status_active_has_exactly_one_chosen_characteristic(
    fake_ecobee: FakeHKDevice,
) -> None:
    """Same dedup holds for a healthy accessory, not just the dead one."""
    accessory = fake_ecobee.entity_map.aid(GREAT_ROOM_AID)
    candidates = [
        service[CharacteristicsTypes.STATUS_ACTIVE]
        for service in accessory.services
        if service.has(CharacteristicsTypes.STATUS_ACTIVE)
    ]

    assert len(candidates) == 3
    chosen = [c for c in candidates if _is_earliest_service_for_characteristic(c)]
    assert len(chosen) == 1


def test_rear_bedroom_battery_level_contradicts_low_battery_attribute(
    fake_ecobee: FakeHKDevice,
) -> None:
    """Pin the exact contradiction that was invisible before this fix.

    The native Battery Level value stayed a healthy 100 while the sensor was
    dead; the new `low_battery` attribute now surfaces the true status
    alongside that same misleading native value, so the contradiction is
    visible instead of hidden.
    """
    battery_service_iid = 192
    sensor = HomeKitBatterySensor(
        fake_ecobee, {"aid": REAR_BEDROOM_AID, "iid": battery_service_iid}
    )

    assert sensor.native_value == 100
    assert sensor.is_low_battery is True
    assert sensor.extra_state_attributes == {"low_battery": True}


def test_great_room_battery_level_and_low_battery_attribute_agree(
    fake_ecobee: FakeHKDevice,
) -> None:
    """Sanity check: a healthy sensor's attribute agrees with its native value."""
    battery_service_iid = 192
    sensor = HomeKitBatterySensor(
        fake_ecobee, {"aid": GREAT_ROOM_AID, "iid": battery_service_iid}
    )

    assert sensor.native_value == 100
    assert sensor.is_low_battery is False
    assert sensor.extra_state_attributes == {"low_battery": False}


# The tests above construct entities directly, which proves the entity classes
# read the right characteristic but would pass even with the bug present: the
# classes were never broken, they were simply never instantiated. The tests
# below drive the real dispatch path instead, so a characteristic registered in
# one dispatch table but not the other fails here.


def test_status_active_is_registered_in_both_dispatch_tables() -> None:
    """Both tables are required; one alone silently produces no entities.

    CHARACTERISTIC_PLATFORMS only selects which platform is offered the
    characteristic. The platform then consults its own accept-list and returns
    False on a miss. This is why the ecobee number entities do not exist: they
    are in CHARACTERISTIC_PLATFORMS only.
    """
    assert (
        CHARACTERISTIC_PLATFORMS[CharacteristicsTypes.STATUS_ACTIVE] == "binary_sensor"
    )
    assert CharacteristicsTypes.STATUS_ACTIVE in CHARACTERISTIC_BINARY_SENSORS


async def test_dispatch_creates_one_status_active_entity_per_remote_sensor(
    fake_ecobee: FakeHKDevice,
) -> None:
    """Drive async_setup_entry over the whole ecobee bridge and count entities.

    The 8 SmartSensors each publish STATUS_ACTIVE on their Motion, Occupancy
    and Temperature services. The thermostat accessory (aid 1) publishes none.
    """
    added = await dispatch_platform(binary_sensor_async_setup_entry, fake_ecobee)

    status_active = [
        e
        for e in added
        if isinstance(e, CharacteristicBinarySensor)
        and e.entity_description.key == CharacteristicsTypes.STATUS_ACTIVE
    ]

    assert len(status_active) == 8
    assert len({e.accessory.aid for e in status_active}) == 8


async def test_dispatch_creates_one_low_battery_entity_per_remote_sensor(
    fake_ecobee: FakeHKDevice,
) -> None:
    """The regression: this count was 0 before the fix, not 8."""
    added = await dispatch_platform(binary_sensor_async_setup_entry, fake_ecobee)

    low_battery = [
        e
        for e in added
        if isinstance(e, CharacteristicBinarySensor)
        and e.entity_description.key == CharacteristicsTypes.STATUS_LO_BATT
    ]

    assert len(low_battery) == 8
    assert len({e.accessory.aid for e in low_battery}) == 8


async def test_dispatch_creates_exactly_one_low_battery_entity_when_level_absent() -> (
    None
):
    """Cover the branch where a battery service exposes no BATTERY_LEVEL.

    _is_chosen_low_battery_characteristic defers to the service-level
    HomeKitBatteryLowSensor in that case, which async_add_service creates
    because BATTERY_LEVEL is its reject characteristic. The accessory must
    still end up with exactly one low battery entity, not zero and not two.
    """
    raw = load_raw_entity_map("ecobee")
    for accessory in raw:
        if accessory["aid"] != REAR_BEDROOM_AID:
            continue
        for service in accessory["services"]:
            service["characteristics"] = [
                c
                for c in service["characteristics"]
                if not c["type"].startswith("00000068")
            ]

    conn = FakeHKDevice(load_entity_map_from_list(raw))
    added = await dispatch_platform(binary_sensor_async_setup_entry, conn)

    rear_bedroom_low_battery = [
        e
        for e in added
        if (
            isinstance(e, HomeKitBatteryLowSensor)
            and e.service.accessory.aid == REAR_BEDROOM_AID
        )
        or (
            isinstance(e, CharacteristicBinarySensor)
            and e.entity_description.key == CharacteristicsTypes.STATUS_LO_BATT
            and e.accessory.aid == REAR_BEDROOM_AID
        )
    ]

    assert len(rear_bedroom_low_battery) == 1
    assert isinstance(rear_bedroom_low_battery[0], HomeKitBatteryLowSensor)
