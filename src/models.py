from dataclasses import dataclass
from enum import IntEnum


SENSOR_ERROR_FLAGS = {
    0x0001: "Temp Sensor",
    0x0002: "TOF Sensor",
    0x0004: "ADC Sensor",
    0x0008: "Gas Sensor A",
    0x0010: "Gas Sensor B",
    0x0020: "Particle Sensor",
    0x0040: "Orientation Sensor",
    0x0080: "Humidity Sensor",
    0x0100: "Orientation",
    0x0200: "Battery Low",
    0x0400: "Paired PCU missing",
    0x0800: "Processor Error",
    0x1000: "Sensor Lens Dirty",
    0x2000: "Battery Critically Low",
    0x4000: "External Memory",
    0x8000: "IO Expander",
}


@dataclass(frozen=True)
class SaferaSensorData:
    ambient_temperature: float
    surface_temperature: float
    humidity: float
    ambient_light: float
    mounting_height: int
    emf: int
    air_quality_index: int
    particle_index: float
    voc_uba: float
    co2_ppm: int
    tvoc_ppb: int
    miu_status: int
    voc_status: int
    heat_index: int
    connected_accessories: int
    battery_level: int
    seconds_since_ok_press: int
    alarm_status: int
    tilt_angle: int
    pitch_angle: int
    device_state: int
    sensor_errors: int
    device_clock: int
    pcu_errors: int
    activity_type: int
    alarm_level: int
    activity_level: int
    power_consumption: int
    blec_command: int
    pcu_lqi: int
    pcu_ed: int
    fan_speed_raw: int | None = None
    fan_speed_level: int | None = None
    fan_auto: bool | None = None
    light_brightness_raw: int | None = None
    light_level: int | None = None
    light_auto: bool | None = None

    @property
    def error_messages(self) -> list[str]:
        return [
            msg for mask, msg in SENSOR_ERROR_FLAGS.items() if self.sensor_errors & mask
        ]

    @classmethod
    def from_bytes(cls, payload: bytes | bytearray) -> "SaferaSensorData":
        if len(payload) < 54:
            raise ValueError("Sensor payload must be 54 bytes.")
        u16 = lambda offset: int.from_bytes(payload[offset : offset + 2], "little")
        s16 = lambda offset: int.from_bytes(
            payload[offset : offset + 2], "little", signed=True
        )
        return cls(
            ambient_temperature=(u16(0) * 0.01) - 50,
            surface_temperature=(u16(2) * 0.01) - 50,
            humidity=u16(4) / 100,
            ambient_light=u16(6) / 32,
            mounting_height=payload[8],
            emf=payload[9],
            air_quality_index=u16(10),
            particle_index=u16(12) / 5,
            voc_uba=payload[14] / 20,
            co2_ppm=u16(15),
            tvoc_ppb=u16(17),
            miu_status=int.from_bytes(payload[19:23], "little"),
            voc_status=payload[23],
            heat_index=payload[24] * 2,
            connected_accessories=payload[25],
            battery_level=payload[26],
            seconds_since_ok_press=payload[27],
            alarm_status=payload[28],
            tilt_angle=s16(29),
            pitch_angle=s16(31),
            device_state=payload[33],
            sensor_errors=u16(34),
            device_clock=int.from_bytes(payload[36:40], "little"),
            pcu_errors=u16(40),
            activity_type=payload[43],
            alarm_level=payload[44],
            activity_level=payload[45],
            power_consumption=u16(46),
            blec_command=payload[50],
            pcu_lqi=int.from_bytes(payload[51:52], "little", signed=True),
            pcu_ed=payload[52],
            fan_speed_raw=payload[60] if len(payload) > 60 else None,
            fan_speed_level=(
                payload[60] // 30
                if len(payload) > 60 and payload[60] in (0, 30, 60, 90, 120)
                else None
            ),
            fan_auto=payload[63] == 30 if len(payload) > 63 else None,
            light_brightness_raw=payload[53] if len(payload) > 53 else None,
            light_level=(
                payload[53] // 30
                if len(payload) > 53 and payload[53] in (0, 30, 60, 90)
                else None
            ),
            light_auto=(payload[53] == 100) if len(payload) > 53 else None,
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
