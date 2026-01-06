from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KitchenFanLight(coordinator)])

class KitchenFanLight(CoordinatorEntity, LightEntity):
    _attr_has_entity_name = True
    _attr_name = "Fan Light"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.ble_device.address}_light"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.ble_device.address)}}

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("light_level", 0) > 0

    @property
    def brightness(self) -> int:
        # Map 0-3 to 0-255
        level = self.coordinator.data.get("light_level", 0)
        return int((level / 3) * 255)

    async def async_turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            # Map 0-255 back to 0-3
            level = round((kwargs[ATTR_BRIGHTNESS] / 255) * 3)
            await self.coordinator.client.set_light_level(max(1, level))
        else:
            await self.coordinator.client.set_light_level(1) # Default to low
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.client.set_light_level(0)
        await self.coordinator.async_request_refresh()
