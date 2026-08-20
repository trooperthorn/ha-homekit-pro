"""Tests for the new Ecobee vendor sensors, against real captured data."""

from aiohomekit.model.characteristics import CharacteristicsTypes

from custom_components.homekit_controller_pro.entity import CharacteristicEntity
from custom_components.homekit_controller_pro.sensor import (
    SIMPLE_SENSOR,
    SimpleSensor,
    ecobee_equipment_running_to_str,
    ecobee_status_code_to_str,
)
from homeassistant.components.sensor import SensorDeviceClass

from .conftest import FakeHKDevice


class _FakeChar:
    def __init__(self, value: int) -> None:
        self.value = value


def test_ecobee_equipment_running_to_str_known_values() -> None:
    assert ecobee_equipment_running_to_str(_FakeChar(0)) == "idle"
    assert ecobee_equipment_running_to_str(_FakeChar(1)) == "heat"
    assert ecobee_equipment_running_to_str(_FakeChar(2)) == "cool"
    assert ecobee_equipment_running_to_str(_FakeChar(3)) == "fan"
    assert ecobee_equipment_running_to_str(_FakeChar(4)) == "aux"


def test_ecobee_equipment_running_to_str_unknown_value_does_not_raise() -> None:
    """An out-of-range value should degrade to "unknown", not KeyError."""
    assert ecobee_equipment_running_to_str(_FakeChar(99)) == "unknown"


def test_ecobee_status_code_to_str_known_values() -> None:
    assert ecobee_status_code_to_str(_FakeChar(0)) == "ok"
    assert ecobee_status_code_to_str(_FakeChar(1)) == "service"
    assert ecobee_status_code_to_str(_FakeChar(2)) == "alert"
    assert ecobee_status_code_to_str(_FakeChar(3)) == "error"


def test_ecobee_status_code_to_str_unknown_value_does_not_raise() -> None:
    assert ecobee_status_code_to_str(_FakeChar(99)) == "unknown"


def _make_simple_sensor(fake_ecobee: FakeHKDevice, char_type: str) -> SimpleSensor:
    thermostat = fake_ecobee.entity_map.aid(1).services.iid(16)
    char = thermostat[char_type]
    description = SIMPLE_SENSOR[char_type]
    info = {"aid": 1, "iid": thermostat.iid}
    return SimpleSensor(fake_ecobee, info, char, description)


def test_alert_text_sensor_reads_real_maintenance_message(fake_ecobee: FakeHKDevice) -> None:
    sensor = _make_simple_sensor(fake_ecobee, CharacteristicsTypes.VENDOR_ECOBEE_ALERT_TEXT)

    assert sensor.native_value == (
        "Time to change your UV lamp.  It was last changed on Jul 21, 2024."
    )


def test_equipment_running_sensor_end_to_end(fake_ecobee: FakeHKDevice) -> None:
    """Real captured value was 1 -- should render through the format function as "heat"."""
    sensor = _make_simple_sensor(
        fake_ecobee, CharacteristicsTypes.VENDOR_ECOBEE_EQUIPMENT_RUNNING
    )

    assert sensor.native_value == "heat"
    assert sensor.entity_description.device_class == SensorDeviceClass.ENUM
    assert "heat" in sensor.entity_description.options


def test_status_code_sensor_end_to_end(fake_ecobee: FakeHKDevice) -> None:
    """Real captured value was 0 -- should render as "ok"."""
    sensor = _make_simple_sensor(fake_ecobee, CharacteristicsTypes.VENDOR_ECOBEE_STATUS_CODE)

    assert sensor.native_value == "ok"


def test_simple_sensor_is_a_characteristic_entity() -> None:
    """Sanity check on the class hierarchy the entity_map lookups above depend on."""
    assert issubclass(SimpleSensor, CharacteristicEntity)
