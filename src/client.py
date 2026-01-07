import argparse
import asyncio
import logging
import os
from collections.abc import Callable
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice

from bleak_retry_connector import (
    establish_connection,
)  # pip install bleak-retry-connector
from dotenv import load_dotenv  # pip install python-dotenv

from models import FanSpeed, LightLevel, SaferaSensorData, SaferaDeviceInfo

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SaferaSenseClient:
    """
    Client for interacting with Røroshetta Sense (manufactured by Safera Oy).
    This class handles connection and data retrieval from GATT characteristics.
    """

    # Service UUIDs
    DEVICE_INFO_SERVICE = "0000180a-0000-1000-8000-00805f9b34fb"
    SAFERA_MAIN_SERVICE = "0000f00d-1212-efde-1523-785fef13d123"

    # Characteristic UUIDs
    # Handle 32:  contains CO2, Temp, Humidity, and VOC, PR2.5, AQI etc
    CHAR_SENSOR_DATA = "0000beef-1212-efde-1523-785fef13d123"
    # Handle 55: Contains the SSID of the connected Wi-Fi network
    CHAR_WIFI_SSID = "0000abd1-1212-efde-1523-785fef13d123"
    # Handle 17: Standard Bluetooth Model Number
    CHAR_MODEL_NAME = "00002a24-0000-1000-8000-00805f9b34fb"
    # Handle 15: Standard Bluetooth Manufacturer Name
    CHAR_MANUFACTURER = "00002a29-0000-1000-8000-00805f9b34fb"
    # Handle 19: Standard Bluetooth Serial Number
    CHAR_SERIAL_NUMBER = "00002a25-0000-1000-8000-00805f9b34fb"
    # Handle 21: Standard Bluetooth Hardware Revision
    CHAR_HARDWARE_REV = "00002a27-0000-1000-8000-00805f9b34fb"
    # Handle 23: Standard Bluetooth Firmware
    CHAR_FIRMWARE_REV = "00002a26-0000-1000-8000-00805f9b34fb"
    # Handle 25: Standard Bluetooth Software Revision
    CHAR_SOFTWARE_REV = "00002a28-0000-1000-8000-00805f9b34fb"

    # Handle 35: Command Pipe for sending control commands
    CHAR_COMMAND_ABBA = (
        "0000abba-1212-efde-1523-785fef13d123"  # Handle 35 (Command Pipe)
    )
    CHAR_COMMAND_BABE = "0000babe-1212-efde-1523-785fef13d123"
    CHAR_ABD2 = "0000abd2-1212-efde-1523-785fef13d123"
    CHAR_ABD3 = "0000abd3-1212-efde-1523-785fef13d123"

    def __init__(self, device: BLEDevice):
        self.device = device
        self.client: BleakClient | None = None
        self._callback: Callable | None = None
        self.last_raw_data = None  # Storage for delta comparison
        # Memory to store last known states
        self.state = {"fan_level": "OFF", "light_level": "OFF", "brightness": 0}

    async def connect(self):
        """Establish connection with the BLE device."""
        logger.info(f"Connecting to {self.device.address}...")
        # Using establish_connection makes it HA-compatible
        # but also works fine standalone
        self.client = await establish_connection(
            BleakClient, self.device, self.device.address
        )
        await self.client.connect()
        logger.info(f"Connected successfully: {self.client.is_connected}")

    async def disconnect(self):
        """Close the connection with the BLE device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            logger.info("Disconnected from device.")

    async def fetch_device_info(self) -> SaferaDeviceInfo:
        """Fetch static hardware information dynamically from the device and return SaferaDeviceInfo."""
        raw_model = await self.client.read_gatt_char(self.CHAR_MODEL_NAME)
        raw_manu = await self.client.read_gatt_char(self.CHAR_MANUFACTURER)

        raw_serial = await self.client.read_gatt_char(self.CHAR_SERIAL_NUMBER)
        raw_hw_rev = await self.client.read_gatt_char(self.CHAR_HARDWARE_REV)
        raw_fw_rev = await self.client.read_gatt_char(self.CHAR_FIRMWARE_REV)
        raw_sw_rev = await self.client.read_gatt_char(self.CHAR_SOFTWARE_REV)
        raw_ssid_data = await self.client.read_gatt_char(self.CHAR_WIFI_SSID)

        _ssid_parts = [
            s.decode("utf-8", errors="ignore").strip()
            for s in raw_ssid_data.split(b"\x00")
            if s
        ]
        # TODO: figure out what the multiple strings are
        # logger.info(f"The SSID data, split at null bytes: {_ssid_strings}")
        # wifi_ssid, hostname, version_info = _ssid_strings

        return SaferaDeviceInfo(
            manufacturer=raw_manu.decode("utf-8").strip(),
            model=raw_model.decode("utf-8").strip(),
            ble_name=self.client.name,
            ble_address=self.device.address,
            serial_number=raw_serial.decode("utf-8").strip(),
            hardware_rev=raw_hw_rev.decode("utf-8").strip(),
            firmware_rev=raw_fw_rev.decode("utf-8").strip(),
            software_rev=raw_sw_rev.decode("utf-8").strip(),
            wifi_ssid=_ssid_parts[0] if _ssid_parts else "",
        )

    async def fetch_raw_sensor_data(self):
        """
        Read the 68-byte sensor data payload.
        This contains the air quality metrics in binary format.
        """
        data = await self.client.read_gatt_char(self.CHAR_SENSOR_DATA)
        return data

    def notification_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray
    ):
        """
        Callback function that triggers every time the sensor sends new data.
        """
        hex_data = data.hex(":")
        print(f"\n[Live Data] Handle {characteristic.handle} ({len(data)} bytes):")
        print(f"RAW: {hex_data}")

        # Tip for analysis: look for bytes that change when you interact with the sensor
        # e.g., blow on it to see CO2/Moisture change.

    async def start_monitoring(self):
        """
        Subscribes to notifications for the sensor characteristic.
        """
        logger.info(f"Starting live monitor on {self.CHAR_SENSOR_DATA}...")
        await self.client.start_notify(self.CHAR_SENSOR_DATA, self.notification_handler)

        # logger.info(f"Starting live monitor on {self.CHAR_ABD2}...")
        # await self.client.start_notify(self.CHAR_ABD2, self.notification_handler)
        # logger.info(f"Starting live monitor on {self.CHAR_COMMAND_ABBA}...")
        # await self.client.start_notify(
        # self.CHAR_COMMAND_ABBA, self.notification_handler
        # )

        print("Monitoring... Press Ctrl+C to stop.")
        try:
            while True:
                # Keep the loop alive while waiting for notifications
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.client.stop_notify(self.CHAR_SENSOR_DATA)
            # await self.client.stop_notify(self.CHAR_COMMAND_ABBA)
            # await self.client.stop_notify(self.CHAR_ABD2)
            logger.info("Monitoring stopped.")

    async def discover_uuids(self):
        """Prints all services and characteristics with their handles."""
        print(f"\n--- GATT Discovery for {self.client.address} ---")
        for service in self.client.services:
            print(
                f"\nService: {service.uuid} - {service.description} (Handle: {service.handle})"
            )
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid} - {char.description}")
                print(f"    Handle: {char.handle} (Hex: {hex(char.handle)})")
                print(f"    Properties: {char.properties}")

    async def set_light_level(self, level: LightLevel):
        """
        Sets light level: OFF, LEVEL_1, LEVEL_2, LEVEL_3
        """
        # Map levels to the byte values found in the Wireshark log index 4
        intensity_map = {
            LightLevel.OFF: 0x00,
            LightLevel.LEVEL_1: 0x1E,
            LightLevel.LEVEL_2: 0x3C,
            LightLevel.LEVEL_3: 0x5A,
        }

        if level not in intensity_map:
            logger.error("Invalid level. Choose OFF, LEVEL_1, LEVEL_2, or LEVEL_3.")
            return

        intensity = intensity_map[level]

        # The exact 8-byte payload structure from your logs
        payload = bytearray([0x05, 0x20, 0x00, 0x00, intensity, 0x00, 0x00, 0x00])

        logger.info(
            f"Sending Command to {self.CHAR_COMMAND_BABE}: Level {level.name} ({intensity:#04x})"
        )

        # Use response=False to trigger Opcode 0x52 (Write Command)
        await self.client.write_gatt_char(
            self.CHAR_COMMAND_BABE, payload, response=False
        )

    async def set_fan_speed(self, level: FanSpeed):
        """
        Sets fan speed with correct protocol headers for Boost and Auto.
        Accepts FanSpeed IntEnum, where AUTO is a bit flag (128).
        """
        is_auto = bool(level & FanSpeed.AUTO)
        # Strip the AUTO bit to get the requested speed level
        target_level = level & ~FanSpeed.AUTO

        if is_auto:
            # Auto mode: Service 04, Param 20, Value 02
            payload = bytearray([0x04, 0x20, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00])
            logger.info("Setting Fan to AUTO")

        elif target_level == FanSpeed.BOOST:
            # BOOST sequence requires two commands
            # 1. Set Speed to 120 (0x78) using standard fan service (01)
            speed_payload = bytearray([0x01, 0x20, 0x00, 0x00, 0x78, 0x00, 0x00, 0x00])
            # 2. Activate Boost mode using boost service (02)
            boost_payload = bytearray([0x02, 0x10, 0x00, 0x00, 0x78, 0x00, 0x00, 0x00])

            logger.info("Setting Fan to LEVEL 4 (Speed 120 + Boost Mode)")
            await self.client.write_gatt_char(
                self.CHAR_COMMAND_BABE, speed_payload, response=False
            )
            # Small delay is often needed for the device to process back-to-back writes
            await asyncio.sleep(0.1)
            payload = boost_payload

        else:
            # Normal levels (0-3): Service 01, Param 20
            # Map enum values to intensity bytes
            intensity_map = {
                FanSpeed.OFF: 0x00,
                FanSpeed.LEVEL_1: 0x1E,
                FanSpeed.LEVEL_2: 0x3C,
                FanSpeed.LEVEL_3: 0x5A,
            }
            if target_level not in intensity_map:
                logger.error(f"Invalid level {target_level}")
                return

            intensity = intensity_map[target_level]
            payload = bytearray([0x01, 0x20, 0x00, 0x00, intensity, 0x00, 0x00, 0x00])
            logger.info(f"Setting Fan level to {FanSpeed(target_level).name}")

        await self.client.write_gatt_char(
            self.CHAR_COMMAND_BABE, payload, response=False
        )

    #### WORK IN PROGRESS BELOW ####
    ### When methods are confirmed working, they will be moved above ###
    #### WORK IN PROGRESS BELOW ####

    async def start_parsing_payload(self):
        """
        Starts monitoring and parsing the sensor payload in real-time.
        """
        logger.info("Starting payload parser...")

        def handler(characteristic: BleakGATTCharacteristic, data: bytearray):
            print(f"\n\n[Raw Data] ({len(data)} bytes): {data.hex(':')}")
            parsed = SaferaSensorData.from_bytes(data)
            if parsed:
                print("[Parsed Sensor Data]")
                for k, v in parsed.__dict__.items():
                    print(f"  {k}: {v}")
            else:
                print("Received incomplete payload.")

        await self.client.start_notify(self.CHAR_SENSOR_DATA, handler)

        print("Parsing... Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            await self.client.stop_notify(self.CHAR_SENSOR_DATA)
            logger.info("Payload parsing stopped.")

    async def subscribe_to_sensor_data(self, callback: Callable):
        """Subscribe to the 69-byte sensor characteristic."""
        self._callback = callback
        # Use bleak to start notify on CHAR_SENSOR_DATA
        await self.client.start_notify(self.CHAR_SENSOR_DATA, self._subscribed_handler)

    def _subscribed_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray
    ):
        """This runs every time new data arrives from the sensor."""
        parsed_data = SaferaSensorData.from_bytes(data)
        if self._callback:
            self._callback(parsed_data)  # Pass parsed data to the user-defined callback


# --- Execution Logic ---


async def main():
    from dotenv import load_dotenv  # pip install python-dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(description="RørosHetta Sense BLE Client")
    parser.add_argument("--address", help="BLE Device Address (overrides .env)")

    # Action group
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--info", action="store_true", help="Fetch device info and Wi-Fi SSID"
    )
    group.add_argument("--monitor", action="store_true", help="Start raw monitoring")
    group.add_argument(
        "--parse", action="store_true", help="Start parsing payload live"
    )
    group.add_argument(
        "--discover", action="store_true", help="Discover GATT services and uuids"
    )
    group.add_argument(
        "--light",
        choices=["OFF", "1", "2", "3"],
        help="Set light level (OFF, 1, 2, 3)",
    )
    group.add_argument(
        "--fan",
        choices=["OFF", "1", "2", "3", "BOOST", "AUTO"],
        help="Set fan speed",
    )

    args = parser.parse_args()
    address = args.address or os.getenv("ADDRESS")

    if not address:
        logger.error(
            "No Bluetooth address found. Use --address or set ADDRESS in .env file."
        )
        return

    logger.info(f"Scanning for device {address}...")
    device = await BleakScanner.find_device_by_address(
        address, timeout=10.0, cb={"use_bdaddr": True}
    )
    if not device:
        logger.error(f"Device with address {address} not found.")
        return

    sense = SaferaSenseClient(device)

    try:
        await sense.connect()

        if args.info:
            # 1. Fetch and display device identity
            info = await sense.fetch_device_info()

            print("\n--- Device Information ---")
            print(f"Manufacturer: {info.manufacturer}")
            print(f"Model: {info.model}")
            print(f"BLE Name: {info.ble_name}")
            print(f"BLE Address: {info.ble_address}")
            print(f"Serial Number: {info.serial_number}")
            print(f"Hardware Revision: {info.hardware_rev}")
            print(f"Firmware Revision: {info.firmware_rev}")
            print(f"Software Revision: {info.software_rev}")
            print(f"Wi-Fi SSID: {info.wifi_ssid}")

        elif args.monitor:
            await sense.start_monitoring()

        elif args.parse:
            await sense.start_parsing_payload()

        elif args.discover:
            await sense.discover_uuids()

        elif args.light:
            level_map = {
                "OFF": LightLevel.OFF,
                "1": LightLevel.LEVEL_1,
                "2": LightLevel.LEVEL_2,
                "3": LightLevel.LEVEL_3,
            }
            await sense.set_light_level(level_map[args.light])

        elif args.fan:
            level_map = {
                "OFF": FanSpeed.OFF,
                "1": FanSpeed.LEVEL_1,
                "2": FanSpeed.LEVEL_2,
                "3": FanSpeed.LEVEL_3,
                "BOOST": FanSpeed.BOOST,
                "AUTO": FanSpeed.AUTO,
            }
            await sense.set_fan_speed(level_map[args.fan])

    except KeyboardInterrupt:
        logger.info("User stopped the monitor.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await sense.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
