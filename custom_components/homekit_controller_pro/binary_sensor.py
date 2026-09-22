"""Support for HomeKit binary sensors."""

from dataclasses import dataclass
from typing import override

from aiohomekit.model.characteristics import Characteristic, CharacteristicsTypes
from aiohomekit.model.services import Service, ServicesTypes

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from . import KNOWN_DEVICES
from .connection import HKDevice
from .entity import CharacteristicEntity, HomeKitEntity
from .utils import folded_name


@dataclass(frozen=True)
class HomeKitBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a HomeKit binary sensor."""

    on_value: int | bool = 1


class HomeKitMotionSensor(HomeKitEntity, BinarySensorEntity):
    """Representation of a Homekit motion sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    @override
    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity is tracking."""
        return [CharacteristicsTypes.MOTION_DETECTED]

    @property
    @override
    def is_on(self) -> bool:
        """Has motion been detected."""
        return self.service.value(CharacteristicsTypes.MOTION_DETECTED) is True


class HomeKitContactSensor(HomeKitEntity, BinarySensorEntity):
    """Representation of a Homekit contact sensor."""

    _attr_device_class = BinarySensorDeviceClass.OPENING

    @override
    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity is tracking."""
        return [CharacteristicsTypes.CONTACT_STATE]

    @property
    @override
    def is_on(self) -> bool:
        """Return true if the binary sensor is on/open."""
        return self.service.value(CharacteristicsTypes.CONTACT_STATE) == 1


class HomeKitSmokeSensor(HomeKitEntity, BinarySensorEntity):
    """Representation of a Homekit smoke sensor."""

    _attr_device_class = BinarySensorDeviceClass.SMOKE

    @override
    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity is tracking."""
        return [CharacteristicsTypes.SMOKE_DETECTED]

    @property
    @override
    def is_on(self) -> bool:
        """Return true if smoke is currently detected."""
        return self.service.value(CharacteristicsTypes.SMOKE_DETECTED) == 1


class HomeKitCarbonMonoxideSensor(HomeKitEntity, BinarySensorEntity):
    """Representation of a Homekit BO sensor."""

    _attr_device_class = BinarySensorDeviceClass.CO

    @override
    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity is tracking."""
        return [CharacteristicsTypes.CARBON_MONOXIDE_DETECTED]

    @property
    @override
    def is_on(self) -> bool:
        """Return true if CO is currently detected."""
        return self.service.value(CharacteristicsTypes.CARBON_MONOXIDE_DETECTED) == 1


class HomeKitOccupancySensor(HomeKitEntity, BinarySensorEntity):
    """Representation of a Homekit occupancy sensor."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    @override
    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity is tracking."""
        return [CharacteristicsTypes.OCCUPANCY_DETECTED]

    @property
    @override
    def is_on(self) -> bool:
        """Return true if occupancy is currently detected."""
        return self.service.value(CharacteristicsTypes.OCCUPANCY_DETECTED) == 1


class HomeKitLeakSensor(HomeKitEntity, BinarySensorEntity):
    """Representation of a Homekit leak sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOISTURE

    @override
    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity is tracking."""
        return [CharacteristicsTypes.LEAK_DETECTED]

    @property
    @override
    def is_on(self) -> bool:
        """Return true if a leak is detected from the binary sensor."""
        return self.service.value(CharacteristicsTypes.LEAK_DETECTED) == 1


class HomeKitBatteryLowSensor(HomeKitEntity, BinarySensorEntity):
    """Representation of a Homekit battery low sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @override
    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity is tracking."""
        return [CharacteristicsTypes.STATUS_LO_BATT]

    @property
    @override
    def name(self) -> str:
        """Return the name of the sensor."""
        if name := self.accessory.name:
            return f"{name} Low Battery"
        return "Low Battery"

    @property
    @override
    def is_on(self) -> bool:
        """Return true if low battery is detected from the binary sensor."""
        return self.service.value(CharacteristicsTypes.STATUS_LO_BATT) == 1


ENTITY_TYPES = {
    ServicesTypes.MOTION_SENSOR: HomeKitMotionSensor,
    ServicesTypes.CONTACT_SENSOR: HomeKitContactSensor,
    ServicesTypes.SMOKE_SENSOR: HomeKitSmokeSensor,
    ServicesTypes.CARBON_MONOXIDE_SENSOR: HomeKitCarbonMonoxideSensor,
    ServicesTypes.OCCUPANCY_SENSOR: HomeKitOccupancySensor,
    ServicesTypes.LEAK_SENSOR: HomeKitLeakSensor,
    ServicesTypes.BATTERY_SERVICE: HomeKitBatteryLowSensor,
}

# Only create the entity if it has the required characteristic
REQUIRED_CHAR_BY_TYPE = {
    ServicesTypes.BATTERY_SERVICE: CharacteristicsTypes.STATUS_LO_BATT,
}
# Reject the service as another platform can represent it better
# if it has a specific characteristic
REJECT_CHAR_BY_TYPE = {
    ServicesTypes.BATTERY_SERVICE: CharacteristicsTypes.BATTERY_LEVEL,
}

CHARACTERISTIC_BINARY_SENSORS: dict[str, HomeKitBinarySensorEntityDescription] = {
    CharacteristicsTypes.STATUS_LO_BATT: HomeKitBinarySensorEntityDescription(
        key=CharacteristicsTypes.STATUS_LO_BATT,
        name="Low Battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CharacteristicsTypes.STATUS_FAULT: HomeKitBinarySensorEntityDescription(
        key=CharacteristicsTypes.STATUS_FAULT,
        name="Problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    CharacteristicsTypes.VENDOR_ECOBEE_AUX_HEAT_ACTIVE: (
        HomeKitBinarySensorEntityDescription(
            key=CharacteristicsTypes.VENDOR_ECOBEE_AUX_HEAT_ACTIVE,
            name="Aux Heat Active",
            device_class=BinarySensorDeviceClass.RUNNING,
        )
    ),
    CharacteristicsTypes.STATUS_ACTIVE: HomeKitBinarySensorEntityDescription(
        key=CharacteristicsTypes.STATUS_ACTIVE,
        name="Status Active",
        translation_key="status_active",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        on_value=True,
    ),
}


class CharacteristicBinarySensor(CharacteristicEntity, BinarySensorEntity):
    """Representation of a HomeKit binary sensor backed by a single characteristic."""

    entity_description: HomeKitBinarySensorEntityDescription

    def __init__(
        self,
        conn: HKDevice,
        info: ConfigType,
        char: Characteristic,
        description: HomeKitBinarySensorEntityDescription,
    ) -> None:
        """Initialise a HomeKit characteristic binary sensor."""
        self.entity_description = description
        super().__init__(conn, info, char)

    @property
    @override
    def name(self) -> str:
        """Return the name of the sensor."""
        if name := self.accessory.name:
            return f"{name} {self.entity_description.name}"
        return f"{self.entity_description.name}"

    @override
    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity is tracking."""
        return [self._char.type]

    @property
    @override
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._char.value == self.entity_description.on_value


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up HomeKit binary sensors."""
    hkid: str = config_entry.data["AccessoryPairingID"]
    conn: HKDevice = hass.data[KNOWN_DEVICES][hkid]

    @callback
    def async_add_service(service: Service) -> bool:
        if not (entity_class := ENTITY_TYPES.get(service.type)):
            return False
        if (
            required_char := REQUIRED_CHAR_BY_TYPE.get(service.type)
        ) and not service.has(required_char):
            return False
        if (reject_char := REJECT_CHAR_BY_TYPE.get(service.type)) and service.has(
            reject_char
        ):
            return False
        info = {"aid": service.accessory.aid, "iid": service.iid}
        entity: HomeKitEntity = entity_class(conn, info)
        conn.async_migrate_unique_id(
            entity.old_unique_id, entity.unique_id, Platform.BINARY_SENSOR
        )
        async_add_entities([entity])
        return True

    conn.add_listener(async_add_service)

    @callback
    def async_add_characteristic(char: Characteristic) -> bool:
        if char.type == CharacteristicsTypes.STATUS_LO_BATT:
            if not _is_chosen_low_battery_characteristic(char):
                return False
        elif char.service.type == ServicesTypes.BATTERY_SERVICE:
            return False

        if not (description := CHARACTERISTIC_BINARY_SENSORS.get(char.type)):
            return False

        if char.type == CharacteristicsTypes.STATUS_ACTIVE and not (
            _is_earliest_service_for_characteristic(char)
        ):
            return False

        info = {"aid": char.service.accessory.aid, "iid": char.service.iid}
        entity = CharacteristicBinarySensor(conn, info, char, description)
        conn.async_migrate_unique_id(
            entity.old_unique_id, entity.unique_id, Platform.BINARY_SENSOR
        )
        async_add_entities([entity])
        return True

    conn.add_char_factory(async_add_characteristic)


def _is_chosen_low_battery_characteristic(char: Characteristic) -> bool:
    """Check if this is the one STATUS_LO_BATT characteristic to create an entity for.

    Exactly one low battery entity is created per accessory: the accessory's
    own BATTERY_SERVICE copy when it exposes STATUS_LO_BATT, otherwise the
    earliest remaining service that exposes it. The BATTERY_SERVICE's copy is
    skipped here when the service-level HomeKitBatteryLowSensor already
    represents it (that happens when the battery service has no BATTERY_LEVEL
    characteristic); this characteristic-level path only needs to take over
    when a BATTERY_LEVEL characteristic is also present on the battery
    service, which previously caused the accessory to end up with zero low
    battery entities at all (see docs/decisions.md, 2026-09-22).
    """
    accessory = char.service.accessory
    battery_service = accessory.services.first(
        service_type=ServicesTypes.BATTERY_SERVICE
    )

    if battery_service is not None and battery_service.has(
        CharacteristicsTypes.STATUS_LO_BATT
    ):
        if not battery_service.has(CharacteristicsTypes.BATTERY_LEVEL):
            return False
        return char.service is battery_service

    return not _has_earlier_duplicate_characteristic(char)


def _has_earlier_duplicate_characteristic(char: Characteristic) -> bool:
    """Check if the accessory already exposed an earlier copy of this characteristic.

    Unscoped characteristics (no distinguishing service label or service name)
    are treated as accessory-level duplicates; only the earliest by service
    iid becomes an entity. Used as the STATUS_LO_BATT fallback when the
    accessory has no BATTERY_SERVICE copy to prefer (see
    _is_chosen_low_battery_characteristic).
    """
    source_key = _duplicate_source_key(char.service)
    return any(
        service.iid < char.service.iid
        and service.has(char.type)
        and _duplicate_source_key(service) == source_key
        for service in char.service.accessory.services
    )


def _is_earliest_service_for_characteristic(char: Characteristic) -> bool:
    """Check if this characteristic's service is the earliest one exposing it.

    Unlike low battery, STATUS_ACTIVE's Motion/Occupancy/Temperature copies on
    the same remote sensor carry distinct per-service names (for example
    "Great Room Motion" vs "Great Room Temperature"), so the name-based
    source key used for low battery would treat them as separate sources and
    fail to deduplicate. STATUS_ACTIVE means the same thing on every copy
    ("this sensor is currently reporting valid data"), so dedup here is
    simply by service iid, with no source-key distinction: only the
    characteristic on the lowest-iid service becomes an entity.
    """
    return not any(
        service.iid < char.service.iid and service.has(char.type)
        for service in char.service.accessory.services
    )


def _has_earlier_status_active_characteristic(char: Characteristic) -> bool:
    """Inverse of _is_earliest_service_for_characteristic, kept as an alias.

    Some callers phrase the STATUS_ACTIVE dedup check as "is there an earlier
    copy" rather than "is this the earliest copy"; both forms are equivalent
    and kept so either reads naturally at the call site.
    """
    return not _is_earliest_service_for_characteristic(char)


def _duplicate_source_key(service: Service) -> str | None:
    """Return the duplicate-detection source key for the service."""
    if (
        service_label_index := service.value(CharacteristicsTypes.SERVICE_LABEL_INDEX)
    ) is not None:
        return f"label:{service.type}:{service_label_index}"

    service_name = service.value(CharacteristicsTypes.NAME)
    if service_name is not None and folded_name(str(service_name)) != folded_name(
        service.accessory.name
    ):
        return f"name:{folded_name(str(service_name))}"
    return None
