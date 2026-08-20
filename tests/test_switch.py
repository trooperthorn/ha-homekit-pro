"""Tests for the new HomeKitIrrigationSystem entity, against real Yardian data."""

from custom_components.homekit_controller_pro.switch import (
    ENTITY_TYPES,
    HomeKitIrrigationSystem,
    ServicesTypes,
)

from .conftest import FakeHKDevice


def test_irrigation_system_registered_in_entity_types() -> None:
    """IRRIGATION_SYSTEM must dispatch to HomeKitIrrigationSystem, not be silently dropped."""
    assert ENTITY_TYPES[ServicesTypes.IRRIGATION_SYSTEM] is HomeKitIrrigationSystem


def test_irrigation_system_reads_real_yardian_data(fake_yardian: FakeHKDevice) -> None:
    """Reads Active/Program Mode/In Use from the real captured dump."""
    entity = HomeKitIrrigationSystem(fake_yardian, {"aid": 1, "iid": 32})

    # is_on returns the raw HAP uint8 (1/0), not a Python bool -- same as
    # the existing HomeKitFaucet/HomeKitValve, not something this entity
    # introduces. Truthy check, not strict `is True`.
    assert entity.is_on
    assert entity.is_on == 1  # ACTIVE == 1 in the captured dump
    attrs = entity.extra_state_attributes
    assert attrs["in_use"] is False  # IN_USE == 0
    assert attrs["program_mode"] == 1


async def test_irrigation_system_turn_off_writes_active_false(
    fake_yardian: FakeHKDevice,
) -> None:
    """Turning off writes ACTIVE=False to the correct (aid, iid)."""
    entity = HomeKitIrrigationSystem(fake_yardian, {"aid": 1, "iid": 32})

    await entity.async_turn_off()

    fake_yardian.put_characteristics.assert_awaited_once()
    (payload,) = fake_yardian.put_characteristics.call_args[0]
    assert payload == [(1, 34, False)]


async def test_irrigation_system_turn_on_writes_active_true(
    fake_yardian: FakeHKDevice,
) -> None:
    """Turning on writes ACTIVE=True to the correct (aid, iid)."""
    entity = HomeKitIrrigationSystem(fake_yardian, {"aid": 1, "iid": 32})

    await entity.async_turn_on()

    (payload,) = fake_yardian.put_characteristics.call_args[0]
    assert payload == [(1, 34, True)]
