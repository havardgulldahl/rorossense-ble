from __future__ import annotations
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FanCoordinator

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the fan platform from a config entry."""
    # Get the coordinator created in __init__.py
    coordinator: FanCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Add the fan entity to Home Assistant
    async_add_entities([KitchenFan(coordinator)])

class KitchenFan(CoordinatorEntity[FanCoordinator], FanEntity):
    """Representation of your Kitchen Fan."""

    def __init__(self, coordinator: FanCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        
        # Link to the device info (useful for the UI)
        self._attr_name = "Kitchen Fan"
        self._attr_unique_id = f"{coordinator.ble_device.address}_fan"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.ble_device.address)},
            "name": "Kitchen Fan BLE",
            "manufacturer": "Reverse Engineered",
        }

        # Define what the fan can do
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED | 
            FanEntityFeature.TURN_OFF | 
            FanEntityFeature.TURN_ON
        )
        
        # Tell HA your fan has specific steps (e.g., 3 speeds)
        # This makes the UI slider "snap" to 33%, 66%, 100%
        self._attr_speed_count = 3

    @property
    def is_on(self) -> bool:
        """Return true if fan is on (based on the library state)."""
        return self.coordinator.client.speed > 0

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        return self.coordinator.client.speed

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
        else:
            # Call your external library method
            await self.coordinator.client.set_speed(percentage)
        
        # Trigger an update so the UI reflects the change immediately
        self.async_write_ha_state()

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        # If no percentage is provided, default to 33% (Speed 1)
        speed = percentage or 33
        await self.coordinator.client.set_speed(speed)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self.coordinator.client.turn_off()
        self.async_write_ha_state()

