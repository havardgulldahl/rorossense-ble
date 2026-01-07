"""The Kitchen Fan BLE integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components import bluetooth

from .const import DOMAIN
from .coordinator import FanCoordinator

# Specify which platforms we want to load (fan.py, sensor.py, etc.)
PLATFORMS: list[Platform] = [Platform.FAN, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kitchen Fan BLE from a config entry."""
    # Find the BLE device based on the MAC address stored during config flow
    address = entry.unique_id
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address, connectable=True
    )

    if not ble_device:
        raise ConfigEntryNotReady(f"Could not find device with address {address}")

    # Initialize the coordinator
    coordinator = FanCoordinator(hass, ble_device)

    # Store the coordinator so platforms (like fan.py) can access it
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
