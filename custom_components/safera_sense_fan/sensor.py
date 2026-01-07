from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import DOMAIN
from .coordinator import FanCoordinator

# Define the sensor types and their metadata
SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="temp",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="co2",
        name="eCO2",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="pm25",
        name="PM2.5",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="aqi",
        name="Air Quality Index",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.AQI,
    ),
    SensorEntityDescription(
        key="tvoc",
        name="tVOC",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="activity",
        name="Activity Scale",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="heat_index",
        name="Heat Index",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="alarm_level",
        name="Alarm Level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="wifi_ssid",
        name="WiFi SSID",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensors from a config entry."""
    coordinator: FanCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Create an entity for every sensor described in SENSOR_TYPES
    entities = [
        KitchenFanSensor(coordinator, description) for description in SENSOR_TYPES
    ]

    async_add_entities(entities)


class KitchenFanSensor(CoordinatorEntity[FanCoordinator], SensorEntity):
    """Representation of a Safera Sensor."""

    def __init__(
        self, coordinator: FanCoordinator, description: SensorEntityDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        # Unique ID based on the MAC address and the sensor key
        self._attr_unique_id = f"{coordinator.ble_device.address}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information from the SaferaDeviceInfo dataclass."""
        # We assume your coordinator has a property 'device_info' which is an
        # instance of your SaferaDeviceInfo dataclass.
        info = self.coordinator.device_info

        return DeviceInfo(
            identifiers={(DOMAIN, info.ble_address)},
            name=info.ble_name,
            manufacturer=info.manufacturer,
            model=info.model,
            sw_version=info.software_rev,
            hw_version=info.hardware_rev,
            serial_number=info.serial_number,
        )

    @property
    def native_value(self) -> float | int | str | None:
        """Return the value from either dynamic sensor data or static device info."""

        # 1. Check the dynamic sensor data (Temp, CO2, etc)
        if self.coordinator.data and hasattr(
            self.coordinator.data, self.entity_description.key
        ):
            return getattr(self.coordinator.data, self.entity_description.key)

        # 2. Check the static device info (WiFi SSID, Serial, etc)
        if self.coordinator.device_info and hasattr(
            self.coordinator.device_info, self.entity_description.key
        ):
            return getattr(self.coordinator.device_info, self.entity_description.key)

        return None
