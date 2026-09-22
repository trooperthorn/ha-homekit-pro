"""Shared test fixtures.

These tests exercise entity logic directly against real captured HAP data
(tests/fixtures/*_entity_map.json, extracted from live diagnostics pulls --
see docs/device-notes.md) using a minimal fake HKDevice stub, rather than
spinning up a full Home Assistant instance. This keeps them fast and keeps
the assertions grounded in what the real devices actually publish.
"""

from collections.abc import Callable, Iterable
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from aiohomekit.model import Accessories
import pytest

from custom_components.homekit_controller_pro.const import KNOWN_DEVICES

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_entity_map(name: str) -> Accessories:
    """Load a captured entity-map fixture into a real aiohomekit Accessories object."""
    with (FIXTURES_DIR / f"{name}_entity_map.json").open() as f:
        return Accessories.from_list(json.load(f))


def load_entity_map_from_list(raw: list[dict[str, Any]]) -> Accessories:
    """Build an Accessories object from an already-mutated raw entity map.

    Used by tests that need a variant of a captured fixture (for example a
    battery service with its BATTERY_LEVEL characteristic removed) without
    committing a second near-duplicate fixture file.
    """
    return Accessories.from_list(raw)


def load_raw_entity_map(name: str) -> list[dict[str, Any]]:
    """Load a captured entity-map fixture as raw JSON, for mutation by tests."""
    with (FIXTURES_DIR / f"{name}_entity_map.json").open() as f:
        return json.load(f)


class FakeHKDevice:
    """Minimal stand-in for connection.HKDevice.

    Only implements what HomeKitEntity.async_setup()/available/
    async_put_characteristics() actually touch -- not a full connection.

    It also records the service listeners and characteristic factories that a
    platform's async_setup_entry registers, so tests can drive the real
    dispatch path. That path, not the entity classes themselves, is where the
    2026-08-20 Rear Bedroom failure lived: the entity classes always worked,
    they were simply never instantiated. See dispatch_platform below.
    """

    def __init__(self, entity_map: Accessories, unique_id: str = "00:00:00:00:00:00") -> None:
        self.entity_map = entity_map
        self.unique_id = unique_id
        self.available = True
        self.put_characteristics = AsyncMock()
        self.service_listeners: list[Callable[[Any], bool]] = []
        self.char_factories: list[Callable[[Any], bool]] = []

    def add_listener(self, listener: Callable[[Any], bool]) -> None:
        """Record a service listener registered by a platform."""
        self.service_listeners.append(listener)

    def add_char_factory(self, factory: Callable[[Any], bool]) -> None:
        """Record a characteristic factory registered by a platform."""
        self.char_factories.append(factory)

    def async_migrate_unique_id(self, *args: Any, **kwargs: Any) -> None:
        """No-op: there is no entity registry in these tests."""
        return


async def dispatch_platform(
    async_setup_entry: Callable[..., Any], conn: FakeHKDevice
) -> list[Any]:
    """Run a platform's async_setup_entry and drive it over the whole entity map.

    Returns every entity the platform actually added. Asserting on this is
    what catches a characteristic that is registered in one dispatch table but
    not the other, which produces zero entities silently.
    """
    hass = SimpleNamespace(data={KNOWN_DEVICES: {conn.unique_id: conn}})
    config_entry = SimpleNamespace(data={"AccessoryPairingID": conn.unique_id})
    added: list[Any] = []

    def async_add_entities(entities: Iterable[Any]) -> None:
        added.extend(entities)

    await async_setup_entry(hass, config_entry, async_add_entities)

    for accessory in conn.entity_map.accessories:
        for service in accessory.services:
            for listener in conn.service_listeners:
                listener(service)
            for char in service.characteristics:
                for factory in conn.char_factories:
                    factory(char)

    return added


@pytest.fixture
def ecobee_entity_map() -> Accessories:
    return load_entity_map("ecobee")


@pytest.fixture
def onelink_entity_map() -> Accessories:
    return load_entity_map("onelink")


@pytest.fixture
def yardian_entity_map() -> Accessories:
    return load_entity_map("yardian")


@pytest.fixture
def roku_entity_map() -> Accessories:
    return load_entity_map("roku")


@pytest.fixture
def fake_ecobee(ecobee_entity_map: Accessories) -> FakeHKDevice:
    return FakeHKDevice(ecobee_entity_map)


@pytest.fixture
def fake_onelink(onelink_entity_map: Accessories) -> FakeHKDevice:
    return FakeHKDevice(onelink_entity_map)


@pytest.fixture
def fake_yardian(yardian_entity_map: Accessories) -> FakeHKDevice:
    return FakeHKDevice(yardian_entity_map)


@pytest.fixture
def fake_roku(roku_entity_map: Accessories) -> FakeHKDevice:
    return FakeHKDevice(roku_entity_map)
