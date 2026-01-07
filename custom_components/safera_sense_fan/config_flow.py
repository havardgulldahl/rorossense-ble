from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class KitchenFanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kitchen Fan BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        # This is called automatically by HA when your fan is nearby
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # You can filter by name if you know what it shows up as
        if "KitchenFan" not in (discovery_info.name or ""):
            return self.async_abort(reason="not_supported")

        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name or "Kitchen Fan", data={}
            )

        self._set_confirm_only()
        return self.async_show_form(step_id="bluetooth_confirm")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the manual user step (e.g., clicking 'Add Integration')."""
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._discovered_devices[address], data={}
            )

        # Look for nearby devices that haven't been configured yet
        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if address not in current_addresses and "KitchenFan" in (
                discovery_info.name or ""
            ):
                self._discovered_devices[address] = discovery_info.name or address

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("address"): vol.In(self._discovered_devices)}
            ),
        )
