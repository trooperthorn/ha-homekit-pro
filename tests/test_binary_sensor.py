"""Tests for the new Ecobee aux-heat-active binary sensor, against real captured data."""

from aiohomekit.model.characteristics import CharacteristicsTypes

from custom_components.homekit_controller_pro.binary_sensor import (
    CHARACTERISTIC_BINARY_SENSORS,
    CharacteristicBinarySensor,
)

from .conftest import FakeHKDevice


def test_aux_heat_active_registered() -> None:
    assert (
        CharacteristicsTypes.VENDOR_ECOBEE_AUX_HEAT_ACTIVE in CHARACTERISTIC_BINARY_SENSORS
    )


def test_aux_heat_active_reads_real_value(fake_ecobee: FakeHKDevice) -> None:
    """Real captured value was False -- aux heat was not running at pull time."""
    thermostat = fake_ecobee.entity_map.aid(1).services.iid(16)
    char = thermostat[CharacteristicsTypes.VENDOR_ECOBEE_AUX_HEAT_ACTIVE]
    description = CHARACTERISTIC_BINARY_SENSORS[CharacteristicsTypes.VENDOR_ECOBEE_AUX_HEAT_ACTIVE]

    sensor = CharacteristicBinarySensor(
        fake_ecobee, {"aid": 1, "iid": thermostat.iid}, char, description
    )

    assert sensor.is_on is False
