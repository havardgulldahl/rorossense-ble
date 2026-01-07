import logging
from datetime import timedelta
import asyncio

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.bluetooth import async_ble_device_from_address

from .const import DOMAIN
from client import SaferaSensorData, SaferaDeviceInfo, SaferaSenseClient

_LOGGER = logging.getLogger(__name__)


class FanCoordinator(DataUpdateCoordinator[SaferaSensorData]):
    """Class to manage fetching data from the Safera Fan via BLE."""

    def __init__(self, hass, ble_device):
        """Initialize the coordinator."""
        self.ble_device = ble_device
        self.client = SaferaSenseClient(ble_device)
        self.device_info: SaferaDeviceInfo | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"Kitchen Fan {ble_device.address}",
            # We poll every 60 seconds as a fallback,
            # but notifications will provide real-time data.
            update_interval=timedelta(seconds=60),
        )

    async def _async_setup(self):
        """Set up the notification listener. Called once during integration setup."""
        try:
            await self.client.connect()
            _LOGGER.info("Connected to Safera Fan at %s", self.ble_device.address)

            # Fetch and store static device info
            self.device_info = await self.client.fetch_device_info()
            _LOGGER.info("Fetched device info: %s", self.device_info)
        except Exception as err:
            _LOGGER.error("Failed to fetch device info: %s", err)
        try:
            # We tell the library: "When you get 69 bytes, call my _handle_bluetooth_data"
            await self.client.start_notifications(self._handle_bluetooth_data)
        except Exception as err:
            _LOGGER.error("Failed to start BLE notifications: %s", err)

    def _handle_bluetooth_data(self, data: bytearray):
        """Handle incoming BLE notification data."""
        parsed = SaferaSensorData.from_bytes(data)
        _LOGGER.debug("Received notification data: %s", parsed)
        # This is the magic line: it updates all sensors immediately
        self.async_set_updated_data(parsed)

    async def _async_update_data(self):
        """Fetch data via Polling (The Fallback)."""
        try:
            # If the connection dropped, this ensures we try to reconnect
            # and pull a fresh 69-byte blob manually.
            return await self.client.get_full_state()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Fan: {err}") from err
