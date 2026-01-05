import asyncio
import logging
import os
from bleak import BleakClient, BleakScanner
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

        # 2. Fetch Wi-Fi SSID dynamically (no longer hardcoded)
        ssid = await sense.fetch_wifi_ssid()
        print(f"Current Wi-Fi: {ssid}")

        # 3. Fetch a one-time snapshot of the sensor data
        raw_sensor = await sense.fetch_raw_sensor_data()
        print(f"\nRaw Sensor Data (Hex):\n{raw_sensor.hex(':')}")
        print(f"Payload Length: {len(raw_sensor)} bytes")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await sense.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
