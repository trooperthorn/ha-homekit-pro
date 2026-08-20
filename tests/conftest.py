"""Shared test fixtures.

These tests exercise entity logic directly against real captured HAP data
(tests/fixtures/*_entity_map.json, extracted from live diagnostics pulls --
see docs/device-notes.md) using a minimal fake HKDevice stub, rather than
spinning up a full Home Assistant instance. This keeps them fast and keeps
the assertions grounded in what the real devices actually publish.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock

from aiohomekit.model import Accessories
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_entity_map(name: str) -> Accessories:
    """Load a captured entity-map fixture into a real aiohomekit Accessories object."""
    with (FIXTURES_DIR / f"{name}_entity_map.json").open() as f:
        return Accessories.from_list(json.load(f))


class FakeHKDevice:
    """Minimal stand-in for connection.HKDevice.

    Only implements what HomeKitEntity.async_setup()/available/
    async_put_characteristics() actually touch -- not a full connection.
    """

    def __init__(self, entity_map: Accessories, unique_id: str = "00:00:00:00:00:00") -> None:
        self.entity_map = entity_map
        self.unique_id = unique_id
        self.available = True
        self.put_characteristics = AsyncMock()


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
