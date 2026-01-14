import argparse
import asyncio
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice

from bleak_retry_connector import (
    establish_connection,
)  # pip install bleak-retry-connector

from models import FanSpeed, LightLevel, SaferaSensorData, SaferaDeviceInfo

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


EVENT_TYPE_NAMES: dict[int, str] = {
    1: "COOKING_START",
    2: "HEATING_START",
    3: "FRYING_START",
    4: "BOILING_START",
    5: "GENERAL_ACTION",
    6: "STEAK_IN",
    99: "INVESTIGATING",
    100: "OK_BUTTON_PRESSED",
    101: "AUX1_BUTTON_PRESSED",
    102: "AUX2_BUTTON_PRESSED",
    103: "MIU_STOVE_ALARM",
    104: "MIU_STOVE_CUTOFF",
    105: "MIU_EXTINGUISH_ALARM",
    106: "MIU_EXTINGUISH_DONE",
    107: "ALARM_RESUMED",
    -56: "CURRENT_FLOW_START",
    -55: "TEMPERATURE_RISE_START",
    -2: "CLOSED_ROUTINE",
    -1: "ROUTINE",
}


@dataclass
class WiFiStatus:
    ssid: str
    rssi: int
    manager_state: int
    manager_state_value: int
    wifi_status: int
    cloud_status: int
    last_command_status: int
    last_cloud_timestamp: int
    device_name: str
    version: str
    local_ip: str


@dataclass
class EventLogEntry:
    event_type: int
    event_name: str
    timestamp: int


@dataclass
class DayStatistics:
    day_count: int
    temp_ambient_mean: float | None
    rh_mean: float | None
    aqi_final_mean: int | None
    eco2_mean: int | None
    tvoc_mean: int | None
    particle_index_mean: int | None
    alarm_count: int
    cooking_count: int

    @classmethod
    def from_bytes(cls, payload: bytes) -> "DayStatistics":
        if len(payload) < 16:
            raise ValueError("DAY_STATISTICS payload truncated.")
        day_count = int.from_bytes(payload[0:2], "little")
        temp_raw = int.from_bytes(payload[2:4], "little")
        rh_raw = int.from_bytes(payload[4:6], "little")
        aqi_raw = int.from_bytes(payload[6:8], "little")
        eco2_raw = int.from_bytes(payload[8:10], "little")
        tvoc_raw = int.from_bytes(payload[10:12], "little")
        particle_raw = int.from_bytes(payload[12:14], "little")
        return cls(
            day_count=day_count,
            temp_ambient_mean=None if temp_raw == 0 else (temp_raw * 0.01) - 50,
            rh_mean=None if rh_raw == 0 else rh_raw / 100,
            aqi_final_mean=None if aqi_raw == 0 else aqi_raw,
            eco2_mean=None if eco2_raw == 0 else eco2_raw,
            tvoc_mean=None if tvoc_raw == 0 else tvoc_raw,
            particle_index_mean=None if particle_raw == 0 else particle_raw,
            alarm_count=payload[14],
            cooking_count=payload[15],
        )


@dataclass
class DcvEntry:
    hub_side_lqi: int
    hub_side_ed: int
    vent_control_final: int
    vent_control_auto: int
    motor_1_speed: int
    stove_guard_alarm: int
    aqi: int
    activity: int
    rht_comfort_level: int
    status_flags: int
    error_flags: int
    sensor_side_lqi: int
    sensor_side_ed: int

    @classmethod
    def from_bytes(cls, payload: bytes) -> "DcvEntry":
        if len(payload) < 15:
            raise ValueError("DCV entry truncated.")
        return cls(
            hub_side_lqi=int.from_bytes(payload[0:1], "little", signed=True),
            hub_side_ed=payload[1],
            vent_control_final=payload[2],
            vent_control_auto=payload[3],
            motor_1_speed=payload[4],
            stove_guard_alarm=payload[5],
            aqi=payload[6],
            activity=payload[7],
            rht_comfort_level=payload[8],
            status_flags=int.from_bytes(payload[9:11], "little"),
            error_flags=int.from_bytes(payload[11:13], "little"),
            sensor_side_lqi=int.from_bytes(payload[13:14], "little", signed=True),
            sensor_side_ed=payload[14],
        )


@dataclass
class DcvReport:
    data_version: int
    entry_count: int
    flags: int
    entries: list["DcvEntry"]

    @classmethod
    def from_bytes(cls, payload: bytes) -> "DcvReport":
        if len(payload) < 4:
            raise ValueError("DCV report truncated.")
        data_version = payload[0]
        entry_count = payload[1]
        flags = int.from_bytes(payload[2:4], "little")
        entries: list[DcvEntry] = []
        offset = 4
        for _ in range(entry_count):
            chunk = payload[offset : offset + 15]
            if len(chunk) < 15:
                break
            entries.append(DcvEntry.from_bytes(chunk))
            offset += 15
        return cls(
            data_version=data_version,
            entry_count=entry_count,
            flags=flags,
            entries=entries,
        )


class DeviceCommand(IntEnum):
    SET_DAY_STATISTICS_DAY = 0x1000


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
    CHAR_EVENT_LOG = "0000abcf-1212-efde-1523-785fef13d123"
    CHAR_DAY_STATISTICS = "0000abdf-1212-efde-1523-785fef13d123"
    CHAR_DCV_SENSOR_REPORT = "0000abd4-1212-efde-1523-785fef13d123"

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

    def _ensure_client(self) -> BleakClient:
        if not self.client or not self.client.is_connected:
            raise RuntimeError("BLE client is not connected.")
        return self.client

    async def send_device_command(self, command: DeviceCommand | int, param: int):
        client = self._ensure_client()
        payload = int(command).to_bytes(4, "little", signed=False) + (
            param & 0xFFFFFFFF
        ).to_bytes(4, "little", signed=False)
        await client.write_gatt_char(self.CHAR_COMMAND_BABE, payload, response=False)

    async def fetch_cloud_wifi_status(self) -> WiFiStatus:
        client = self._ensure_client()
        raw = await client.read_gatt_char(self.CHAR_WIFI_SSID)
        if len(raw) < 75:
            raise ValueError("Unexpected Wi-Fi status payload size.")
        ssid = (
            raw[0:32].split(b"\x00", 1)[0].decode("utf-8", errors="ignore").rstrip("\n")
        )
        device_name = raw[43:59].split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
        version = raw[59:71].split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
        local_ip_bytes = raw[71:75]
        local_ip = ".".join(
            str(b) for b in reversed(local_ip_bytes)
        )  # documented as little-endian
        return WiFiStatus(
            ssid=ssid,
            rssi=int.from_bytes(raw[32:33], "little", signed=True),
            manager_state=raw[33],
            manager_state_value=raw[34],
            wifi_status=raw[35],
            cloud_status=raw[36],
            last_command_status=raw[37],
            last_cloud_timestamp=int.from_bytes(raw[39:43], "little"),
            device_name=device_name,
            version=version,
            local_ip=local_ip,
        )

    async def fetch_device_info(self) -> SaferaDeviceInfo:
        client = self._ensure_client()
        raw_model = await client.read_gatt_char(self.CHAR_MODEL_NAME)
        raw_manu = await client.read_gatt_char(self.CHAR_MANUFACTURER)

        raw_serial = await client.read_gatt_char(self.CHAR_SERIAL_NUMBER)
        raw_hw_rev = await client.read_gatt_char(self.CHAR_HARDWARE_REV)
        raw_fw_rev = await client.read_gatt_char(self.CHAR_FIRMWARE_REV)
        raw_sw_rev = await client.read_gatt_char(self.CHAR_SOFTWARE_REV)
        wifi_status = await self.fetch_cloud_wifi_status()
        return SaferaDeviceInfo(
            manufacturer=raw_manu.decode("utf-8").strip(),
            model=raw_model.decode("utf-8").strip(),
            ble_name=self.client.name,
            ble_address=self.device.address,
            serial_number=raw_serial.decode("utf-8").strip(),
            hardware_rev=raw_hw_rev.decode("utf-8").strip(),
            firmware_rev=raw_fw_rev.decode("utf-8").strip(),
            software_rev=raw_sw_rev.decode("utf-8").strip(),
            wifi_ssid=wifi_status.ssid,
        )

    async def fetch_raw_sensor_data(self):
        """
        Read the 54-byte sensor data payload.
        This contains the air quality metrics in binary format.
        """
        client = self._ensure_client()
        return await client.read_gatt_char(self.CHAR_SENSOR_DATA)

    async def fetch_sensor_snapshot(self) -> SaferaSensorData:
        """Return the current SENSOR_REPORT parsed into SaferaSensorData."""
        return SaferaSensorData.from_bytes(await self.fetch_raw_sensor_data())

    def _parse_event_log_payload(self, raw: bytes) -> list["EventLogEntry"]:
        entries: list[EventLogEntry] = []
        if len(raw) < 2:
            logger.debug("Event log payload too short: %s", raw.hex(":"))
            return entries
        event_count = int.from_bytes(raw[0:2], "little")
        logger.debug(
            "Event log payload len=%s, event_count=%s, raw=%s",
            len(raw),
            event_count,
            raw.hex(":"),
        )
        offset = 2
        for _ in range(event_count):
            chunk = raw[offset : offset + 5]
            if len(chunk) < 5:
                logger.debug(
                    "Truncated event chunk at offset %s (payload len %s).",
                    offset,
                    len(raw),
                )
                break
            event_type = int.from_bytes(chunk[0:1], "little", signed=True)
            timestamp = int.from_bytes(chunk[1:5], "little")
            entries.append(
                EventLogEntry(
                    event_type=event_type,
                    event_name=EVENT_TYPE_NAMES.get(event_type, "UNKNOWN"),
                    timestamp=timestamp,
                )
            )
            offset += 5
        return entries

    async def fetch_event_log(self) -> list[EventLogEntry]:
        client = self._ensure_client()
        raw = await client.read_gatt_char(self.CHAR_EVENT_LOG)
        return self._parse_event_log_payload(raw)

    async def stream_event_log(self):
        client = self._ensure_client()

        def handler(_: BleakGATTCharacteristic, data: bytearray):
            entries = self._parse_event_log_payload(data)
            if not entries:
                logger.debug("Event log notification carried no entries.")
                return
            print(f"\n--- Event Log ({len(entries)} new) ---")
            for entry in entries:
                print(
                    f"{entry.timestamp:>10} - {entry.event_name} ({entry.event_type})"
                )

        await client.start_notify(self.CHAR_EVENT_LOG, handler)
        print("Listening for EVENT_LOG notifications. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await client.stop_notify(self.CHAR_EVENT_LOG)
            logger.info("Event log stream stopped.")

    async def fetch_day_statistics(self, day_index: int) -> DayStatistics:
        if day_index < 0:
            raise ValueError("Day index must be zero or positive.")
        await self.send_device_command(DeviceCommand.SET_DAY_STATISTICS_DAY, day_index)
        await asyncio.sleep(0.2)
        client = self._ensure_client()
        payload = await client.read_gatt_char(self.CHAR_DAY_STATISTICS)
        return DayStatistics.from_bytes(payload)

    async def fetch_dcv_report(self) -> DcvReport | None:
        client = self._ensure_client()
        try:
            payload = await client.read_gatt_char(self.CHAR_DCV_SENSOR_REPORT)
        except Exception as exc:
            logger.debug("DCV sensor report unavailable: %s", exc)
            return None
        if not payload:
            return None
        return DcvReport.from_bytes(payload)

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
            try:
                parsed = SaferaSensorData.from_bytes(data)
            except ValueError as exc:
                print(f"Unable to parse payload: {exc}")
                return
            print("[Parsed Sensor Data]")
            for k, v in parsed.__dict__.items():
                print(f"  {k}: {v}")

            if parsed.sensor_errors:
                print(f"\n  [!] SENSOR ERRORS DETECTED ({parsed.sensor_errors:#06x}):")
                for err in parsed.error_messages:
                    print(f"   - {err}")

        await self.client.start_notify(self.CHAR_SENSOR_DATA, handler)

        print("Parsing... Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            await self.client.stop_notify(self.CHAR_SENSOR_DATA)
            logger.info("Payload parsing stopped.")

    async def subscribe_to_sensor_data(self, callback: Callable):
        """Subscribe to the 54-byte sensor characteristic."""
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
    group.add_argument(
        "--wifi-status",
        action="store_true",
        help="Fetch Wi-Fi/cloud status block",
    )
    group.add_argument(
        "--event-log",
        action="store_true",
        help="Fetch recent event log entries",
    )
    group.add_argument(
        "--day-stats",
        type=int,
        metavar="DAY",
        help="Fetch aggregated day statistics (0 = today)",
    )
    group.add_argument(
        "--dcv",
        action="store_true",
        help="Fetch DCV sensor report if present",
    )
    group.add_argument(
        "--fan-status",
        action="store_true",
        help="Read current hood fan level",
    )
    group.add_argument(
        "--light-status",
        action="store_true",
        help="Read current hood light level",
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

        elif args.wifi_status:
            status = await sense.fetch_cloud_wifi_status()
            print("\n--- Wi-Fi / Cloud Status ---")
            print(f"SSID: {status.ssid} (RSSI {status.rssi} dBm)")
            print(f"Mgr state: {status.manager_state} / {status.manager_state_value}")
            print(
                f"Wi-Fi status: {status.wifi_status} | Cloud status: {status.cloud_status}"
            )
            print(
                f"Last command status: {status.last_command_status} @ {status.last_cloud_timestamp}"
            )
            print(f"Device name: {status.device_name} | Version: {status.version}")
            print(f"Local IP (LE): {status.local_ip}")

        elif args.monitor:
            await sense.start_monitoring()

        elif args.parse:
            await sense.start_parsing_payload()

        elif args.discover:
            await sense.discover_uuids()

        elif args.event_log:
            await sense.stream_event_log()
        elif args.day_stats is not None:
            stats = await sense.fetch_day_statistics(args.day_stats)
            print("\n--- Day Statistics ---")
            print(f"Day index: {args.day_stats} (count: {stats.day_count})")
            print(
                f"Ambient mean: {stats.temp_ambient_mean if stats.temp_ambient_mean is not None else 'n/a'} °C"
            )
            print(
                f"Humidity mean: {stats.rh_mean if stats.rh_mean is not None else 'n/a'} %"
            )
            print(
                f"AQI: {stats.aqi_final_mean or 'n/a'} | eCO₂: {stats.eco2_mean or 'n/a'} | TVOC: {stats.tvoc_mean or 'n/a'}"
            )
            print(
                f"Particles: {stats.particle_index_mean or 'n/a'} | Alarms: {stats.alarm_count} | Cooking: {stats.cooking_count}"
            )
        elif args.dcv:
            report = await sense.fetch_dcv_report()
            if not report or not report.entries:
                print("No DCV data available.")
            else:
                print(
                    f"\n--- DCV Report (v{report.data_version}, flags {report.flags:#06x}) ---"
                )
                for idx, entry in enumerate(report.entries, 1):
                    print(
                        f"Node {idx}: motor {entry.motor_1_speed}, alarm {entry.stove_guard_alarm}, "
                        f"activity {entry.activity}, status {entry.status_flags:#06x}, errors {entry.error_flags:#06x}"
                    )
        elif args.fan_status:
            snapshot = await sense.fetch_sensor_snapshot()
            if snapshot.fan_speed_raw is None:
                print("Fan speed data unavailable.")
            else:
                print("\n--- Fan Status ---")
                print(f"Raw value: {snapshot.fan_speed_raw}")
                if snapshot.fan_speed_level is not None:
                    print(f"Level: {snapshot.fan_speed_level}")
                if snapshot.fan_auto is not None:
                    print(f"AUTO mode: {'ON' if snapshot.fan_auto else 'OFF'}")
        elif args.light_status:
            snapshot = await sense.fetch_sensor_snapshot()
            if snapshot.light_brightness_raw is None:
                print("Light status unavailable.")
            else:
                print("\n--- Light Status ---")
                print(f"Raw value: {snapshot.light_brightness_raw}")
                if snapshot.light_level is not None:
                    print(f"Level: {snapshot.light_level}")
                if snapshot.light_auto is not None:
                    print(f"AUTO mode: {'ON' if snapshot.light_auto else 'OFF'}")
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
