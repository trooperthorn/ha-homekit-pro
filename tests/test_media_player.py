"""Tests for HomeKitTelevision's new volume/mute support, against real Roku data."""

from custom_components.homekit_controller_pro.media_player import HomeKitTelevision
from homeassistant.components.media_player import MediaPlayerEntityFeature

from .conftest import FakeHKDevice


def test_speaker_service_found_via_linked_lookup(fake_roku: FakeHKDevice) -> None:
    """The Television service links to a Speaker service, not an InputSource."""
    entity = HomeKitTelevision(fake_roku, {"aid": 1, "iid": 48})

    speaker = entity._speaker_service  # noqa: SLF001 -- testing the lookup itself
    assert speaker is not None
    assert speaker.type == "00000113-0000-1000-8000-0026BB765291"  # SPEAKER


def test_volume_level_reads_real_roku_value(fake_roku: FakeHKDevice) -> None:
    """Volume characteristic is 0-100 over HAP; HA wants 0..1."""
    entity = HomeKitTelevision(fake_roku, {"aid": 1, "iid": 48})

    assert entity.volume_level == 1.0  # captured value was 100


def test_is_volume_muted_reads_real_roku_value(fake_roku: FakeHKDevice) -> None:
    entity = HomeKitTelevision(fake_roku, {"aid": 1, "iid": 48})

    assert entity.is_volume_muted is False  # captured value was False


def test_supported_features_includes_volume(fake_roku: FakeHKDevice) -> None:
    """This Roku publishes Volume+Mute, so HA should now advertise both feature bits."""
    entity = HomeKitTelevision(fake_roku, {"aid": 1, "iid": 48})

    features = entity.supported_features
    assert features & MediaPlayerEntityFeature.VOLUME_SET
    assert features & MediaPlayerEntityFeature.VOLUME_MUTE


async def test_set_volume_level_writes_to_speaker_service(fake_roku: FakeHKDevice) -> None:
    """Setting volume should write the 0-100 value to the Speaker service's Volume iid."""
    entity = HomeKitTelevision(fake_roku, {"aid": 1, "iid": 48})

    await entity.async_set_volume_level(0.42)

    fake_roku.put_characteristics.assert_awaited_once()
    (payload,) = fake_roku.put_characteristics.call_args[0]
    assert payload == [(1, 84, 42)]  # (aid, VOLUME iid, rounded 0-100 value)


async def test_mute_volume_writes_to_speaker_service(fake_roku: FakeHKDevice) -> None:
    entity = HomeKitTelevision(fake_roku, {"aid": 1, "iid": 48})

    await entity.async_mute_volume(True)

    (payload,) = fake_roku.put_characteristics.call_args[0]
    assert payload == [(1, 82, True)]  # (aid, MUTE iid, value)


def test_source_degrades_gracefully_without_input_source_service(
    fake_roku: FakeHKDevice,
) -> None:
    """No INPUT_SOURCE service is linked in this snapshot -- source must not crash."""
    entity = HomeKitTelevision(fake_roku, {"aid": 1, "iid": 48})

    assert entity.source is None
    assert entity.source_list == []
