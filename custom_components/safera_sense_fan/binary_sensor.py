from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FanCoordinator

BINARY_SENSOR_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="filter_greasy",
        name="Greasy Filter Warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key="activity_detected",
        name="Cooking Activity",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [KitchenBinarySensor(coordinator, desc) for desc in BINARY_SENSOR_TYPES]
    )

class KitchenBinarySensor(CoordinatorEntity[FanCoordinator], BinarySensorEntity):
    def __init__(self, coordinator, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.ble_device.address}_{description.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.ble_device.address)}}

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.coordinator.data.get(self.entity_description.key)
