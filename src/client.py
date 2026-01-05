import asyncio
import logging
import os
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    # Handle 35: Command Pipe for sending control commands
    CHAR_COMMAND_ABBA = (
        "0000abba-1212-efde-1523-785fef13d123"  # Handle 35 (Command Pipe)
    )
    CHAR_COMMAND_BABE = "0000babe-1212-efde-1523-785fef13d123"
    CHAR_ABD2 = "0000abd2-1212-efde-1523-785fef13d123"
    CHAR_ABD3 = "0000abd3-1212-efde-1523-785fef13d123"

    def __init__(self, address):
        self.address = address
        self.client = None
        self.device = None

    async def connect(self):
        """Establish connection with the BLE device."""
        logger.info(f"Connecting to {self.address}...")
        self.device = await BleakScanner.find_device_by_address(
            self.address, timeout=10.0, cb={"use_bdaddr": True}
        )
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

        return {
            "manufacturer": raw_manu.decode("utf-8").strip(),
            "model": raw_model.decode("utf-8").strip(),
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

        logger.info(f"Starting live monitor on {self.CHAR_ABD2}...")
        await self.client.start_notify(self.CHAR_ABD2, self.notification_handler)
        logger.info(f"Starting live monitor on {self.CHAR_COMMAND_ABBA}...")
        await self.client.start_notify(
            self.CHAR_COMMAND_ABBA, self.notification_handler
        )

        print("Monitoring... Press Ctrl+C to stop.")
        try:
            while True:
                # Keep the loop alive while waiting for notifications
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.client.stop_notify(self.CHAR_SENSOR_DATA)
            await self.client.stop_notify(self.CHAR_COMMAND_ABBA)
            await self.client.stop_notify(self.CHAR_ABD2)
            logger.info("Monitoring stopped.")

    async def discover_uuids(self):
        """Prints all services and characteristics with their handles."""
        print(f"\n--- GATT Discovery for {self.address} ---")
        for service in self.client.services:
            print(f"\nService: {service.uuid} (Handle: {service.handle})")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}")
                print(f"    Handle: {char.handle} (Hex: {hex(char.handle)})")
                print(f"    Properties: {char.properties}")

    async def set_light_level(self, level: int):
        """
        Sets light level: 0 (Off), 1 (30), 2 (60), 3 (90)
        """
        # Map levels to the byte values found in the Wireshark log index 4
        intensity_map = {0: 0x00, 1: 0x1E, 2: 0x3C, 3: 0x5A}

        if level not in intensity_map:
            logger.error("Invalid level. Choose 0, 1, 2, or 3.")
            return

        intensity = intensity_map[level]

        # The exact 8-byte payload structure from your logs
        payload = bytearray([0x05, 0x20, 0x00, 0x00, intensity, 0x00, 0x00, 0x00])

        logger.info(
            f"Sending Command to {self.CHAR_COMMAND_BABE}: Level {level} ({intensity:#04x})"
        )

        # Use response=False to trigger Opcode 0x52 (Write Command)
        await self.client.write_gatt_char(
            self.CHAR_COMMAND_BABE, payload, response=False
        )

    #### WORK IN PROGRESS BELOW ####
    ### When methods are confirmed working, they will be moved above ###
    #### WORK IN PROGRESS BELOW ####

    def parse_payload(self, data: bytearray):
        """
        Parses the 68-byte payload into a human-readable dictionary.
        """
        if len(data) < 68:
            return None

        # 1. Temperature Calculation (Index 0-1)
        # Based on BLE standards, usually: (Byte0 + Byte1*256) / 100
        raw_temp = int.from_bytes(data[0:2], byteorder="little")
        temp_c = raw_temp / 100.0

        # 2. Humidity Calculation (Index 2-3)
        raw_hum = int.from_bytes(data[2:4], byteorder="little")
        humidity = raw_hum / 100.0

        voc_raw = int.from_bytes(data[4:6], byteorder="little")

        # 3. Fan Level (Index 60)
        # 0=0, 30=1, 60=2, 90=3, 120=4
        fan_raw = data[60]
        fan_level = fan_raw // 30

        # Light Dimming (Index 54)
        light_step = data[54]
        # Actual brightness value (0-32767)
        raw_brightness = int.from_bytes(data[55:57], byteorder="little")
        brightness_pct = (raw_brightness / 32767) * 100

        # 5. System Active Flag (Index 63)
        fan_running = data[63] == 0x64

        return {
            "temperature": f"{temp_c:.2f}°C",
            "humidity": f"{humidity:.2f}%",
            "air_quality_index (VOC)": voc_raw,
            "fan_level": fan_level,
            "fan_active": fan_running,
            "light_step_id": light_step,
            "brightness_actual": f"{brightness_pct:.1f}%",
            "mode": "AUTO (Boost)" if fan_level == 4 else "MANUAL/IDLE",
        }

    async def start_parsing_payload(self):
        """
        Starts monitoring and parsing the sensor payload in real-time.
        """
        logger.info("Starting payload parser...")

        def handler(characteristic: BleakGATTCharacteristic, data: bytearray):
            parsed = self.parse_payload(data)
            if parsed:
                print("\n[Parsed Sensor Data]")
                for k, v in parsed.items():
                    print(f"  {k}: {v}")
            else:
                print("Received incomplete payload.")

        await self.client.start_notify(self.CHAR_SENSOR_DATA, handler)

        print("Parsing... Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.client.stop_notify(self.CHAR_SENSOR_DATA)
            logger.info("Payload parsing stopped.")

    def check_light_status(
        self, characteristic: BleakGATTCharacteristic, data: bytearray
    ):
        # Check index 54 for the light toggle (0x5a as seen in your logs)
        if data[54] == 0x5A:
            print(f"\n[!!!] SUCCESS DETECTED AT BYTE 54!")
            self.success_combo = "Last sent command worked"


# --- Execution Logic ---


async def main():
    load_dotenv()
    address = os.getenv("ADDRESS")

    if not address:
        logger.error("No Bluetooth address found in .env file.")
        return

    sense = RoroshettaSenseClient(address)

    try:
        await sense.connect()

        # 1. Fetch and display device identity
        info = await sense.fetch_model_info()
        print(f"\n--- Device Info ---")
        print(f"Manufacturer: {info['manufacturer']}")
        print(f"Model:        {info['model']}")
        print(f"Device Name:  {info['ble_name']}")
        ssid = await sense.fetch_wifi_ssid()
        print(f"Current Wi-Fi: {ssid}")

        # Start the live stream of data
        # await sense.start_monitoring()

        # Start parsing the payload
        # await sense.start_parsing_payload()

        # discover UUIDs
        # await sense.discover_uuids()

        # Set light level (0-3)
        await sense.set_light_level(1)

        #  Fetch a one-time snapshot of the sensor data
        raw_sensor = await sense.fetch_raw_sensor_data()
        print(f"\nRaw Sensor Data (Hex):\n{raw_sensor.hex(':')}")
        print(f"Payload interpretation:")
        parsed = sense.parse_payload(raw_sensor)
        for k, v in parsed.items():
            print(f"  {k}: {v}")

    except KeyboardInterrupt:
        logger.info("User stopped the monitor.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await sense.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
