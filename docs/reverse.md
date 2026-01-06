# Safera Sense (RørosHetta) BLE Protocol

This document describes the reverse-engineered Bluetooth Low Energy (BLE) protocol for the Safera Sense smart cooking sensor (also known as RørosHetta Sense), Model `IFU10CR-PRO`.

## Connection Details

*   **Manufacturer**: Safera Oy
*   **Main Service UUID**: `0000f00d-1212-efde-1523-785fef13d123`

## Characteristics

All custom characteristics share the base suffix `-1212-efde-1523-785fef13d123`.

| Name | Short UUID | Handle | Permissions | Value Type | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Sensor Data** | `beef` | `0x20` | Notify, Read | Binary (~69 bytes) | Real-time telemetry (Air quality, Fan state, Lights). |
| **Control Stick** | `babe` | `0x29` | Read, Write | Binary (8 bytes) | Primary command pipe for setting Fan and Lights. |
| **Wi-Fi SSID** | `abd1` | `0x37` | Read, Notify | String (UTF-8) | Null-terminated string of the connected SSID. |
| **Command Pipe 2** | `abba` | `0x23` | Read, Write | Binary | Unknown usage, possibly older protocol version. |

## Control Protocol (`...babe`)

Commands are sent as **8-byte payloads**. The structure appears to be:
`[ Service_ID, Parameter_ID, 00, 00, Value, 00, 00, 00 ]`

### Fan Control

Standard fan levels map to step values: 0, 30, 60, 90, 120.

| Level | Byte Sequence (Hex) | Description |
| :--- | :--- | :--- |
| **OFF** | `01 20 00 00 00 00 00 00` | Stop fan |
| **1** | `01 20 00 00 1E 00 00 00` | Speed set to 30 |
| **2** | `01 20 00 00 3C 00 00 00` | Speed set to 60 |
| **3** | `01 20 00 00 5A 00 00 00` | Speed set to 90 |
| **AUTO** | `04 20 00 00 02 00 00 00` | Switch to Automatic Sensing Mode |

**Boost Mode (Level 4)** requires a specific sequence of two write commands:
1.  Set Speed to 120 (`0x78`): `01 20 00 00 78 00 00 00`
2.  Enable Boost Flag (`0x02`): `02 10 00 00 78 00 00 00`

### Light Control

| Level | Byte Sequence (Hex) | Description |
| :--- | :--- | :--- |
| **OFF** | `05 20 00 00 00 00 00 00` | Lights Off |
| **1** | `05 20 00 00 1E 00 00 00` | Dim (30) |
| **2** | `05 20 00 00 3C 00 00 00` | Medium (60) |
| **3** | `05 20 00 00 5A 00 00 00` | Bright (90) |

## Sensor Data Map (`...beef`)

The main notification payload is approx 69 bytes long. Multi-byte integers are **Little Endian**.

| Offset | Type | Name | Transformation / Notes |
| :--- | :--- | :--- | :--- |
| **4-5** | `uint16` | **Humidity** | `val / 100.0` (%) |
| **10-11** | `uint16` | **AQI** | Raw Air Quality Index |
| **15-16** | `uint16` | **eCO2** | ppm (Parts per million) |
| **17-18** | `uint16` | **tVOC** | µg/m³ (Volatile Organic Compounds) |
| **31** | `uint8` | **Temperature** | Raw integer in Celsius (°C) |
| **33-34** | `uint16` | **Heat Index** | `val / 10.0` |
| **50** | `bool` | **Presence** | `0x01` = Cook Detected |
| **51** | `uint8` | **Activity Lvl** | 0-255 Scale of movement/cooking activity |
| **53** | `uint8` | **Light State** | Returns set level (0, 30, 60, 90, 100=Auto) |
| **55-56** | `uint16` | **Brightness** | Ambient brightness sensor value |
| **60** | `uint8` | **Fan Speed** | Current speed (0, 30, 60, 90, 120) |
| **62** | `uint8` | **Alarm Lvl** | Percentage |
| **63** | `uint8` | **Fan Mode** | `30` indicates Auto Mode |
