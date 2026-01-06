import argparse
import asyncio
import logging
import os
from enum import IntEnum
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FanSpeed(IntEnum):
    OFF = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    BOOST = 4
    AUTO = 128


class LightLevel(IntEnum):
    OFF = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    AUTO = 98


class RoroshettaSenseClient:
    """
    Client for interacting with Røroshetta Sense (manufactured by Safera Oy).
    This class handles connection and data retrieval from GATT characteristics.
    """

    # Service UUIDs
    DEVICE_INFO_SERVICE = "0000180a-0000-1000-8000-00805f9b34fb"
    SAFERA_MAIN_SERVICE = "0000f00d-1212-efde-1523-785fef13d123"

    # Characteristic UUIDs
    # Handle 32: Likely contains CO2, Temp, Humidity, and VOC
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
        self.address = device.address
        self.client: BleakClient | None = None
        self.last_raw_data = None  # Storage for delta comparison
        # Memory to store last known states
        self.state = {"fan_level": "OFF", "light_level": "OFF", "brightness": 0}

    async def connect(self):
        """Establish connection with the BLE device."""
        logger.info(f"Connecting to {self.address}...")
        self.client = BleakClient(self.device)
        await self.client.connect()
        logger.info(f"Connected successfully: {self.client.is_connected}")

    async def disconnect(self):
        """Close the connection with the BLE device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            logger.info("Disconnected from device.")

    async def fetch_model_info(self):
        """Fetch static hardware information dynamically from the device."""
        raw_model = await self.client.read_gatt_char(self.CHAR_MODEL_NAME)
        raw_manu = await self.client.read_gatt_char(self.CHAR_MANUFACTURER)

        raw_serial = await self.client.read_gatt_char(self.CHAR_SERIAL_NUMBER)
        raw_hw_rev = await self.client.read_gatt_char(self.CHAR_HARDWARE_REV)
        raw_fw_rev = await self.client.read_gatt_char(self.CHAR_FIRMWARE_REV)
        raw_sw_rev = await self.client.read_gatt_char(self.CHAR_SOFTWARE_REV)

        return {
            "manufacturer": raw_manu.decode("utf-8").strip(),
            "model": raw_model.decode("utf-8").strip(),
            "serial_number": raw_serial.decode("utf-8").strip(),
            "hardware_revision": raw_hw_rev.decode("utf-8").strip(),
            "firmware_revision": raw_fw_rev.decode("utf-8").strip(),
            "software_revision": raw_sw_rev.decode("utf-8").strip(),
            "ble_name": self.client.name,
        }

    async def fetch_wifi_ssid(self):
        """
        Dynamically read the Wi-Fi SSID currently configured on the device.
        Splits at null bytes to handle fixed-length characteristic padding.
        """
        raw_data = await self.client.read_gatt_char(self.CHAR_WIFI_SSID)
        try:
            # Decode bytes and take the string until the first null byte
            decoded_ssid = raw_data.split(b"\x00")[0].decode("utf-8", errors="ignore")
            return decoded_ssid
        except Exception as e:
            logger.error(f"Failed to decode Wi-Fi SSID: {e}")
            return "Unknown"

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
        print(f"\n--- GATT Discovery for {self.address} ---")
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

    def parse_payload(self, data: bytearray):
        """
        Safera IFU10CR-PRO Final Logic.
        """
        if len(data) < 69:
            return None

        # 1. Environmental Sensors
        # Indices based on your app's verified 20°C/23% readings
        temp_c = data[31]  # Observed stable byte for temperature
        hum_pct = int.from_bytes(data[4:6], "little") / 100.0

        # 2. Air Quality Metrics (Verified offsets 10-18)
        aqi = int.from_bytes(data[10:12], "little")  # 0x1388 = 5000
        eco2 = int.from_bytes(data[15:17], "little")  # 0x0192 = 402 ppm
        tvoc = int.from_bytes(data[17:19], "little")  # Fluctuates around 40-60

        # 3. Fan Status (Verified Offsets 60 and 63)
        fan_step_raw = data[60]
        fan_mode_raw = data[63]

        # Determine Mode
        is_auto = fan_mode_raw == 30

        # Map Steps
        fan_steps = {
            0: FanSpeed.OFF,
            30: FanSpeed.LEVEL_1,
            60: FanSpeed.LEVEL_2,
            90: FanSpeed.LEVEL_3,
            120: FanSpeed.BOOST,
        }

        # Get readable name from enum if possible
        if fan_step_raw in fan_steps:
            enum_val = fan_steps[fan_step_raw]
            current_step = enum_val.name.replace("_", " ").title()
            if enum_val == FanSpeed.BOOST:
                current_step += " (Boost)"
        else:
            current_step = f"Unknown ({fan_step_raw})"

        fan_display = f"AUTO ({current_step})" if is_auto else current_step

        # 4. Light Status (Verified Offsets 53-56)
        light_step_raw = data[53]
        light_levels_map = {
            0: LightLevel.OFF,
            30: LightLevel.LEVEL_1,
            60: LightLevel.LEVEL_2,
            90: LightLevel.LEVEL_3,
            100: LightLevel.AUTO,
        }

        if light_step_raw in light_levels_map:
            enum_val = light_levels_map[light_step_raw]
            light_state = enum_val.name.replace("_", " ").title()
        else:
            light_state = f"Unknown ({light_step_raw})"

        brightness_val = int.from_bytes(data[55:57], "little")

        # 5. Safety Metrics
        alarm_level = data[62]
        heat_index = int.from_bytes(data[33:35], "little") / 10.0

        # . Presence Sensor
        # Byte 50: Presence Flag (0/1)
        # Byte 51: Activity Level Scale (0-255)
        presence = data[50] == 0x01
        activity_level = data[51]

        # Simple mapping for activity level
        if activity_level == 0:
            activity_label = "None"
        elif activity_level < 20:
            activity_label = "Low"
        elif activity_level < 60:
            activity_label = "Medium"
        else:
            activity_label = "High"

        return {
            "temperature": f"{temp_c:.1f}°C",
            "humidity": f"{hum_pct:.1f}%",
            "eCO2": f"{eco2} ppm",
            "tVOC": f"{tvoc} ug/m3",
            "AQI": aqi,
            "fan_status": fan_display,
            "light_status": light_state,
            "brightness": brightness_val,
            "heat_index": heat_index,
            "alarm_level": f"{alarm_level}%",
            "presence": "Detected" if presence else "Clear",
            "activity": f"{activity_label} ({activity_level})",
        }

    async def start_parsing_payload(self):
        """
        Starts monitoring and parsing the sensor payload in real-time.
        """
        logger.info("Starting payload parser...")

        def handler(characteristic: BleakGATTCharacteristic, data: bytearray):
            print(f"\n\n[Raw Data] ({len(data)} bytes): {data.hex(':')}")
            parsed = self.parse_payload(data)
            if parsed:
                print("[Parsed Sensor Data]")
                for k, v in parsed.items():
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


# --- Execution Logic ---


async def main():
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

    sense = RoroshettaSenseClient(device)

    try:
        await sense.connect()

        if args.info:
            # 1. Fetch and display device identity
            info = await sense.fetch_model_info()
            print(f"\n--- Device Info ---")
            print(f"Manufacturer: {info['manufacturer']}")
            print(f"Model:        {info['model']}")
            print(f"Device Name:  {info['ble_name']}")
            print(f"Serial No.:   {info['serial_number']}")
            print(f"Hardware Rev: {info['hardware_revision']}")
            print(f"Firmware Rev: {info['firmware_revision']}")
            print(f"Software Rev: v.{info['software_revision']}")
            ssid = await sense.fetch_wifi_ssid()
            print(f"Current Wi-Fi: {ssid}")

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
