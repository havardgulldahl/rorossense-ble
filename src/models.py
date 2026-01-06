from dataclasses import dataclass
from enum import IntEnum
import struct


@dataclass(frozen=True)
class SaferaSensorData:
    """Class to represent parsed Safera sensor data."""

    # Fan & Light Control States
    fan_level: int  # 0-4
    fan_auto: bool
    light_level: int  # 0-3
    light_auto: bool

    # Environmental Sensors
    temp: float  # Celsius
    humidity: float  # Percentage
    co2: int  # ppm
    pm25: int  # µg/m³
    tvoc: int  # µg/m³
    aqi: int  # Index
    heat_index: float  # Celsius
    activity: int  # Percentage
    alarm_level: int  # Percentage

    # Binary Flags
    filter_greasy: bool
    activity_detected: bool

    @classmethod
    def from_bytes(cls, data: bytearray) -> "SaferaSensorData":
        """Parse the 69-byte payload into this dataclass."""
        # Fan Handling
        # 0=OFF, 30=L1, 60=L2, 90=L3, 120=BOOST
        fan_raw = data[60]
        fan_level = fan_raw // 30 if fan_raw in (0, 30, 60, 90, 120) else 0
        fan_auto = data[63] == 30

        # Light Handling
        # 0=OFF, 30=L1, 60=L2, 90=L3, 100=AUTO
        light_raw = data[53]
        light_auto = light_raw == 100
        if light_raw in (0, 30, 60, 90):
            light_level = light_raw // 30
        else:
            # If AUTO (100) or unknown, we don't strictly know the step from this byte alone
            # defaulting to 0 or keeping previous state logic is up to caller
            light_level = 0

        # Environmental
        # PM2.5 is guessed at offset 12 (filling gap between AQI at 10 and CO2 at 15)
        # Temp byte 31 seems unsigned based on prev logic, but 'b' (signed) is safer for temp
        temp_val = struct.unpack_from("b", data, 31)[0]

        return cls(
            temp=float(temp_val),
            humidity=int.from_bytes(data[4:6], "little") / 100.0,
            aqi=int.from_bytes(data[10:12], "little"),
            pm25=int.from_bytes(data[12:14], "little"),  # Placeholder/Guessed offset
            co2=int.from_bytes(data[15:17], "little"),
            tvoc=int.from_bytes(data[17:19], "little"),
            fan_level=fan_level,
            fan_auto=fan_auto,
            light_level=light_level,
            light_auto=light_auto,
            heat_index=int.from_bytes(data[33:35], "little") / 10.0,
            activity=data[51],
            alarm_level=data[62],
            filter_greasy=False,  # Unknown byte
            activity_detected=data[50] == 0x01,
        )


@dataclass(frozen=True)
class SaferaDeviceInfo:
    """Class to represent static device information."""

    manufacturer: str  # Manufacturer String, e.g., "Safera Oy"
    model: str  # Model String
    ble_name: str  # Bluetooth Device Name
    ble_address: str  # Bluetooth Address Bytes
    serial_number: str  # Serial Number String
    hardware_rev: str  # Hardware Revision String
    firmware_rev: str  # Firmware Revision String
    software_rev: str  # Software Revision String
    wifi_ssid: str  # WiFi SSID


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
