"""Tests for presenting an unreachable media player as off.

A television that is switched off leaves the network entirely, so over
HomeKit it is indistinguishable from an accessory that has failed. The
default unavailable state reads as a broken integration rather than a TV
someone turned off, which is misleading for the two Roku accessories in
tests/fixtures/roku_entity_map.json.

The option is deliberately scoped to media players. These tests pin that
scoping, because applying the same treatment to a sensor would hide a
genuinely dead sensor behind a plausible looking state, which is the exact
failure the STATUS_ACTIVE work exists to surface.
"""

from types import SimpleNamespace

from aiohomekit.model.services import ServicesTypes
import pytest

from custom_components.homekit_controller_pro.const import (
    OPTION_UNREACHABLE_MEDIA_PLAYER_AS_OFF,
)
from custom_components.homekit_controller_pro.media_player import HomeKitTelevision
from custom_components.homekit_controller_pro.sensor import HomeKitBatterySensor
from homeassistant.components.media_player import MediaPlayerState

from .conftest import FakeHKDevice


def _television(conn: FakeHKDevice) -> HomeKitTelevision:
    """Build the television entity for the first Television service found."""
    for accessory in conn.entity_map.accessories:
        for service in accessory.services:
            if service.type == ServicesTypes.TELEVISION:
                return HomeKitTelevision(
                    conn, {"aid": accessory.aid, "iid": service.iid}
                )
    pytest.fail("no Television service in the roku fixture")


def _with_options(conn: FakeHKDevice, **options: bool) -> FakeHKDevice:
    """Attach a config entry carrying the given options to the fake device."""
    conn.config_entry = SimpleNamespace(options=dict(options))
    return conn


def test_reachable_television_is_unaffected_by_the_option(
    fake_roku: FakeHKDevice,
) -> None:
    """With the accessory reachable the option changes nothing."""
    conn = _with_options(fake_roku, **{OPTION_UNREACHABLE_MEDIA_PLAYER_AS_OFF: True})
    conn.available = True
    television = _television(conn)

    assert television.available is True
    assert television.state is not MediaPlayerState.OFF


def test_unreachable_television_is_unavailable_by_default(
    fake_roku: FakeHKDevice,
) -> None:
    """Default behaviour is unchanged: unreachable means unavailable."""
    conn = _with_options(fake_roku)
    conn.available = False
    television = _television(conn)

    assert television.available is False


def test_unreachable_television_reports_off_when_enabled(
    fake_roku: FakeHKDevice,
) -> None:
    """The option makes an unreachable television present as off, not failed."""
    conn = _with_options(fake_roku, **{OPTION_UNREACHABLE_MEDIA_PLAYER_AS_OFF: True})
    conn.available = False
    television = _television(conn)

    assert television.available is True
    assert television.state is MediaPlayerState.OFF


def test_option_does_not_apply_to_sensors(fake_ecobee: FakeHKDevice) -> None:
    """Scoping guard: an unreachable sensor still reports unavailable.

    Rear Bedroom is the accessory that died unnoticed. If this ever starts
    passing as available with the option on, the option has leaked out of the
    media player platform and is hiding dead sensors again.
    """
    conn = _with_options(fake_ecobee, **{OPTION_UNREACHABLE_MEDIA_PLAYER_AS_OFF: True})
    conn.available = False
    sensor = HomeKitBatterySensor(conn, {"aid": 4295591051, "iid": 192})

    assert sensor.available is False
