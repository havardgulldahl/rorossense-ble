# The Safera Stove Guard BTE Protocol

The Safera Stove Guard BTE protocol exposes the proprietary service
`0000f00d-1212-efde-1523-785fef13d123`, this is also how a safera BTE device
can be detected.

It also exposes the standard `0000180a-0000-1000-8000-00805f9b34fb` service
(Device Information), and the member-assigned
`0000fe59-0000-1000-8000-00805f9b34fb` (Nordic Secure DFU, Device Firmware
Updates). The DFU service will not be covered here. The standard Device
Information service typically looks like this:

* `00002a29` -> "_Safera Oy_" (Manufacturer Name)
* `00002a24` -> "_IFU10B-PRO_" (Model Number)
* `00002a25` -> "_xx00-0000-xx00-00xx_" (Serial Number)
* `00002a27` -> "_2.1.127.0_" (Hardware Revision)
* `00002a26` -> "_9_" (Firmware Revision)
* `00002a28` -> "_66_" (Software Revision)

## Hardware Revision

The Hardware Revision number is interpreted like this:
`<major>.<minor>.<capabilities>.<mech_variant>`.

In the app, this is shown as `<major>.<minor>`.

### Major hardware version

The major version number indicates the main hardware version of the device.

Here is a table indicating known major versions and their device
type/functionality:

| hwMajor | StoveGuard | CookerHood | HomeCookerHood | ProCookerHood | Hub | SmallRemote | AQSensor | SenseI | SenseB | Battery | Accelerometer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |  | ✓ |  |  |  |
| 2 | ✓ |  |  |  |  |  |  |  | ✓ | ✓ | ✓ |
| 3 | ✓ | ✓ | ✓ |  |  |  |  |  |  |  | ✓ |
| 4 |  |  |  |  |  | ✓ |  |  |  | ✓ |  |
| 5 |  | ✓ |  | ✓ |  |  |  |  |  |  | ✓ |
| 6 |  | ✓ |  | ✓ | ✓ |  |  |  |  |  | ✓ |
| 7 | ✓ | ✓ | ✓ |  |  |  |  |  |  |  | ✓ |
| 8 |  | ✓ |  | ✓ |  |  |  |  |  |  | ✓ |
| 9 |  | ✓ |  | ✓ | ✓ |  |  |  |  |  | ✓ |
| 10 | ✓ |  |  |  |  |  |  |  | ✓ | ✓ | ✓ |
| 12 |  |  |  |  |  |  | ✓ |  |  | ✓ | ✓ |

### Minor hardware version

The minor hardware version presumably indicates a minor revision of the
hardware.

### Hardware capabilities

The capabilities byte is a bitfield indicating which hardware capabilities are
present. The value has been observed to include 257, so it encodes more than a
byte of values.

The bits are interpreted according to this table:

| Bit number | Hex mask | Capability |
| --- | --- | --- |
| 0 | `0x0001` | VALID |
| 1 | `0x0002` | WIFI |
| 2 | `0x0004` | LPC_V1 (Supports TVOC and particles) |
| 3 | `0x0008` | Z_MOD (Supports TVOC sensor) |
| 4 | `0x0010` | TOF |
| 5 | `0x0020` | MIC |
| 6 | `0x0040` | EMF |
| 7 | `0x0080` | HOOD |
| 8 | `0x0100` | (unknown) |

### Mechanical variant

This seems to indicate a different look of the device, and is used in the app
to select different images of the device to present to the user.

## Exposed characteristics

The proprietary `f00d` service exposes the characteristics below.

Documented, fully or partially:
* `0000beef-1212-efde-1523-785fef13d123` ("beef"): SENSOR_REPORT (BLE: Read, Notify)
* `0000abcf-1212-efde-1523-785fef13d123` ("abcf"): EVENT_LOG (BLE: Read, Notify)
* `0000babe-1212-efde-1523-785fef13d123` ("babe"): DEVICE_COMMAND (BLE: Read, Write)
* `0000abdf-1212-efde-1523-785fef13d123` ("abdf"): DAY_STATISTICS (BLE: Read, Notify)
* `0000abd1-1212-efde-1523-785fef13d123` ("abd1"): CLOUD_WIFI_STATUS (BLE: Read, Notify)
* `0000abd2-1212-efde-1523-785fef13d123` ("abd2"): GDT_DATA (BLE: Read, Write, Notify)
* `0000abd3-1212-efde-1523-785fef13d123` ("abd3"): GDT_COMMAND (BLE: Read, Write)
* `0000abd4-1212-efde-1523-785fef13d123` ("abd4"): DCV_SENSOR_REPORT (BLE: Read, Notify)

Not yet documented:
* `0000abcd-1212-efde-1523-785fef13d123` ("abcd"): LOG (BLE: Read, Notify)
* `0000abce-1212-efde-1523-785fef13d123` ("abce"): VOC (BLE: Read, Notify)
* `0000dcba-1212-efde-1523-785fef13d123` ("dcba"): READ_SETTINGS (BLE: Read)
* `0000abba-1212-efde-1523-785fef13d123` ("abba"): WRITE_SETTINGS (BLE: Read, Write)
* `0000dcbb-1212-efde-1523-785fef13d123` ("dcbb"): READ_CONFIG_BANK (BLE: Read)

The Safera device can also be coupled with functionality for DCV (Demand
controlled ventilation), when it is integrated with a hood fan. The
DCV_SENSOR_REPORT characteristic is only present when this is the case.

**Note that all multi-byte values are in little-endian byte order, unless
otherwise noted.**

## Characteristic SENSOR_REPORT ("beef")

This is the main sensor data report characteristic, containing sensor data and
important real-time information. If subscribed to, it is notified periodically
(about every second) by the device.

### Record layout

The SENSOR_REPORT characteristic contains a fixed-size record of 54 bytes with
the following layout:

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 2 | `ambient_temperature` |
| 2 | 2 | `surface_temperature` |
| 4 | 2 | `humidity` |
| 6 | 2 | `ambient_light` |
| 8 | 1 | `mounting_height` |
| 9 | 1 | `emf` |
| 10 | 2 | `air_quality_index` |
| 12 | 2 | `particle_index` |
| 14 | 1 | `voc_uba` |
| 15 | 2 | `co2_ppm` |
| 17 | 2 | `tvoc_ppb` |
| 19 | 4 | `miu_status` |
| 23 | 1 | `voc_status` |
| 24 | 1 | `heat_index` |
| 25 | 1 | `connected_accessories` |
| 26 | 1 | `battery_level` |
| 27 | 1 | `seconds_since_ok_press` |
| 28 | 1 | `alarm_status` |
| 29 | 2 | `tilt_angle` |
| 31 | 2 | `pitch_angle` |
| 33 | 1 | `device_state` |
| 34 | 2 | `sensor_errors` |
| 36 | 4 | `device_clock` |
| 40 | 2 | `pcu_errors` |
| 42 | 1 | `unused_1` |
| 43 | 1 | `activity_type` |
| 44 | 1 | `alarm_level` |
| 45 | 1 | `activity_level` |
| 46 | 2 | `power_consumption` |
| 48 | 2 | `unused_2` |
| 50 | 1 | `blec_command` |
| 51 | 1 | `pcu_lqi` |
| 52 | 1 | `pcu_ed` |

### Field details

#### ambient_temperature
- **Size:** 16 bit unsigned
- **Unit:** °C
- **Conversion:** temp = (raw * 0.01) - 50
- **Description:** Ambient temperature.

#### surface_temperature
- **Size:** 16 bit unsigned
- **Unit:** °C
- **Conversion:** temp = (raw * 0.01) - 50
- **Description:** Surface temperature.

Shown as “heat index” in the Safe Cooking page of the app. (Note that this is
different from the "heat index" shown in the Smart Cooking page)

#### humidity
- **Size:** 16 bit unsigned
- **Unit:** %RH
- **Conversion:** humidity = raw / 100
- **Description:** Relative humidity.

#### ambient_light
- **Size:** 16 bit unsigned
- **Unit:** lux (presumed)
- **Conversion:** ambient_light = raw / 32
- **Description:** Ambient light level.

#### mounting_height
- **Size:** 8 bit unsigned
- **Unit:** cm
- **Description:** Mounting height of the sensor.

#### emf
- **Size:** 8 bit unsigned
- **Description:** EMF value (unit/scale unknown).

#### air_quality_index
- **Size:** 16 bit unsigned
- **Description:** Air quality index value.

Many different AQI scales exist. The exact scale used here is not specified,
but the documentation says:

* 0-50: Good
* 51-100: Acceptable
* 101-200: Somewhat polluted
* 201-300: Bad
* 301-400: Very bad
* 401-500: Serious

#### particle_index
- **Size:** 16 bit unsigned
- **Conversion:** particle_index = raw / 5
- **Description:** Particle index value (unit/scale unknown).

#### voc_uba
- **Size:** 8 bit unsigned
- **Unit:** UBA VOC index
- **Conversion:** voc_uba = raw / 20
- **Description:** UBA AQI index value (1-5), or 0 for no data.

#### co2_ppm
- **Size:** 16 bit unsigned
- **Unit:** ppm
- **Description:** CO₂ concentration.

#### tvoc_ppb
- **Size:** 16 bit unsigned
- **Unit:** ppb
- **Description:** Total VOC (Volatile Organic Compounds) concentration.

#### miu_status
- **Size:** 32 bit unsigned
- **Description:** Device status word, details unknown.

The first byte has always been observed to be `0xf8`, and the second byte
`0x00` or `0x01`, with the rest of the bytes being `0x00`. The meaning of this
is unknown.

#### voc_status
- **Size:** 8 bit unsigned
- **Description:** VOC status byte. Details unknown.

This byte has only been observed to be `0x00`. Presumably it indicates no errors
with VOC sensor.

#### heat_index
- **Size:** 8 bit unsigned
- **Conversion:** heat_index = raw * 2
- **Description:** An index indicating the heat level of the cooking pan.

The value as returned is the estimated pan temperature in °C. This value is
shown as "heat index" in the Smart Cooking page of the app. (Note that this is
different from the "heat index" shown in the Safe Cooking page).

#### connected_accessories
- **Size:** 8 bit unsigned
- **Description:** Bitmask indicating connected accessories.

Bit `0x01` indicates PCU connected. Remaining bits are unused as of now.

#### battery_level
- **Size:** 8 bit unsigned
- **Unit:** %
- **Description:** Battery level percentage.

#### seconds_since_ok_press
- **Size:** 8 bit unsigned
- **Unit:** seconds
- **Description:** Seconds since the OK button was last pressed.

If the value would be larger than 255 seconds, 255 (`0xff`) is reported.

#### alarm_status
- **Size:** 8 bit unsigned
- **Description:** Alarm status code or countdown timer.

This field is `0x01` during normal operation, and is `0x00` if the power has
been cut to the stove. If the alarm is sounded, the value will count down each
second from 118 to 104, once every second.

#### tilt_angle
- **Size:** 16 bit signed
- **Unit:** degrees
- **Description:** Forward tilt angle.

A negative value means the top tilts towards the user, and a positive value
means it tilts away.

#### pitch_angle
- **Size:** 16 bit signed
- **Unit:** degrees
- **Description:** Sideways tilt angle.

A negative value means the left side tilts down, and a positive value means the
right side tilts down.

#### device_state
- **Size:** 8 bit unsigned
- **Description:** Device state enum. See Device state below.

#### sensor_errors
- **Size:** 16 bit unsigned
- **Description:** Sensor error, as a bitfield. See Sensor errors below.

#### device_clock
- **Size:** 32 bit unsigned
- **Unit:** seconds
- **Description:** The current value of the internal device clock.

Times reported in the EVENT_LOG characteristic are given in timestamps of the
device clock, and this field can be used to correlate those timestamps to a
known time. The clock seems to start at 0 when the device is first powered on.

#### pcu_errors
- **Size:** 16 bit unsigned
- **Description:** PCU error, as a bitfield. See PCU errors below.

#### unused_1
- **Size:** 8 bit unsigned
- **Description:** Unused. Always observed to be `0x02`.

#### activity_type
- **Size:** 8 bit unsigned
- **Description:** Activity type.

Values observed include 0 (idle) and 2 (cooking).

#### alarm_level
- **Size:** 8 bit unsigned
- **Unit:** %
- **Description:** Alarm level.

While the app will cut this value at 100%, the value of this field can go above
100%. At 100% the alarm sounds.

#### activity_level
- **Size:** 8 bit unsigned
- **Unit:** %
- **Description:** Activity level.

#### power_consumption
- **Size:** 16 bit unsigned
- **Unit:** Watt
- **Description:** Power consumption of the stove.

#### unused_2
- **Size:** 16 bit unsigned
- **Description:** Unused. Always observed to be `0x0000`.

#### blec_command
- **Size:** 8 bit unsigned
- **Description:** BLE command byte. Always observed to be `0x01`.

#### pcu_lqi
- **Size:** 8 bit signed
- **Description:** PCU link quality indicator, always negative.

#### pcu_ed
- **Size:** 8 bit unsigned
- **Description:** PCU energy detect (an RSSI-like metric).

### Device state enum values

| Value | Meaning |
| --- | --- |
| `0x00` | NONE |
| `0x01` | START |
| `0x02` | IDLE |
| `0x03` | SELF_CHECK |
| `0x05` | PAIRING_RCL2 |
| `0x06` | PAIRING_BLE |
| `0x07` | POWEROFF_WARNING |
| `0x08` | POWEROFF |
| `0x09` | FIRE_WARNING |
| `0x0a` | FIRE |
| `0x0b` | LOCKED_WARNING |
| `0x0c` | LOCKED_POWEROFF |
| `0x0d` | LOCKOFF_POWER_CHECK |
| `0x0e` | LOCKOFF_POWER_CHECK_WARN |
| `0x0f` | CURRENT_CAL |
| `0x10` | REMOTE_MAINTENANCE |

### PCU errors bitfield values

| Bit number | Hex mask | Error message |
| --- | --- | --- |
| 0 | `0x0001` | Volt Meas |
| 1 | `0x0002` | Cur Meas |
| 2 | `0x0004` | Water Meas |
| 3 | `0x0008` | Processor |
| 4 | `0x0010` | Temp Sensor |
| 5 | `0x0020` | Power Supply |
| 6 | `0x0040` | Relay |
| 7 | `0x0080` | Overheat |
| 8 | `0x0100` | (unused) |
| 9 | `0x0200` | (unused) |
| 10 | `0x0400` | Overcurrent |

### Sensor errors bitfield values

| Bit number | Hex mask | Error message |
| --- | --- | --- |
| 0 | `0x0001` | Temp Sensor |
| 1 | `0x0002` | TOF Sensor |
| 2 | `0x0004` | ADC Sensor |
| 3 | `0x0008` | Gas Sensor A |
| 4 | `0x0010` | Gas Sensor B |
| 5 | `0x0020` | Particle Sensor |
| 6 | `0x0040` | Orientation Sensor |
| 7 | `0x0080` | Humidity Sensor |
| 8 | `0x0100` | Orientation |
| 9 | `0x0200` | Battery Low |
| 10 | `0x0400` | Paired PCU missing |
| 11 | `0x0800` | Processor Error |
| 12 | `0x1000` | Sensor Lens Dirty |
| 13 | `0x2000` | Battery Critically Low |
| 14 | `0x4000` | External Memory |
| 15 | `0x8000` | IO Expander |

## Characteristic EVENT_LOG ("abcf")

This characteristic contains a log of recent events recorded by the device. It
corresponds to the time line shown in the Smart Cooking page of the app. If
subscribed to, it is notified when new events are logged by the device.

### Record layout

Each EVENT_LOG payload begins with a 16-bit little-endian count, followed by
that many fixed-size event entries.

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 2 | `event_count` |
| 2 | 5 × `event_count` | `events[i]` |

Each `events[i]` entry (5 bytes) has:

| Offset (entry) | Size | Field |
| --- | --- | --- |
| 0 | 1 | `event_type` |
| 1 | 4 | `event_timestamp` |

### Field details

#### event_count
- **Size:** 16 bit unsigned
- **Description:** Number of event entries that follow.

#### events[i]
- **Size:** 5 bytes per entry
- **Description:** Repeating event entry; see subfields.

#### event_type
- **Size:** 8 bit signed
- **Description:** Event type code. See Event type enum values below.

#### event_timestamp
- **Size:** 32 bit unsigned
- **Unit:** seconds (device clock)
- **Description:** Timestamp from the device clock corresponding to the event.

### Event type enum values

| Value | Meaning |
| --- | --- |
| 1 | COOKING_START |
| 2 | HEATING_START |
| 3 | FRYING_START |
| 4 | BOILING_START |
| 5 | GENERAL_ACTION |
| 6 | STEAK_IN |
| 99 | INVESTIGATING |
| 100 | OK_BUTTON_PRESSED |
| 101 | AUX1_BUTTON_PRESSED |
| 102 | AUX2_BUTTON_PRESSED |
| 103 | MIU_STOVE_ALARM |
| 104 | MIU_STOVE_CUTOFF |
| 105 | MIU_EXTINGUISH_ALARM |
| 106 | MIU_EXTINGUISH_DONE |
| 107 | ALARM_RESUMED |
| -56 | CURRENT_FLOW_START |
| -55 | TEMPERATURE_RISE_START |
| -2 | CLOSED_ROUTINE |
| -1 | ROUTINE |

## Characteristic CLOUD_WIFI_STATUS ("abd1")

### Record layout (little endian)

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 32 | `ssid` |
| 32 | 1 | `rssi` |
| 33 | 1 | `mgr_state` |
| 34 | 1 | `mgr_state_value` |
| 35 | 1 | `wifi_connection_status` |
| 36 | 1 | `cloud_connection_status` |
| 37 | 1 | `last_command_status` |
| 39 | 4 | `last_cloud_timestamp` |
| 43 | 16 | `device_name` |
| 59 | 12 | `version` |
| 71 | 4 | `local_ip` |

### Field details

#### ssid
- **Size:** 32 bytes
- **Unit:** ASCII
- **Conversion:** ASCII, terminator `0x0a`, zero-padded
- **Description:** Wi-Fi SSID string with newline terminator, padded with zeros.

#### rssi
- **Size:** 8 bit signed
- **Unit:** dBm
- **Description:** Wi-Fi RSSI (e.g., `0xa4` → -92 dBm).

#### mgr_state
- **Size:** 8 bit unsigned
- **Description:** Wi-Fi manager state enum.

#### mgr_state_value
- **Size:** 8 bit unsigned
- **Description:** Wi-Fi manager state value/detail.

#### wifi_connection_status
- **Size:** 8 bit unsigned
- **Description:** Wi-Fi connection status enum.

#### cloud_connection_status
- **Size:** 8 bit unsigned
- **Description:** Cloud connection status enum.

#### last_command_status
- **Size:** 8 bit unsigned
- **Description:** Status/result of last Wi-Fi/cloud command.

#### last_cloud_timestamp
- **Size:** 32 bit unsigned
- **Unit:** seconds (Unix epoch)
- **Description:** Unix timestamp for last successful cloud communication.

#### device_name
- **Size:** 16 bytes
- **Unit:** ASCII
- **Conversion:** ASCII, zero-padded
- **Description:** Device name, zero-padded. A typical value is "Sense_AB12EF".

#### version
- **Size:** 12 bytes
- **Unit:** ASCII
- **Conversion:** ASCII, zero-padded
- **Description:** Some unknown version string, zero-padded.

Presumably this is the cloud API version. Only the value `1.1` has been
observed.

#### local_ip
- **Size:** 4 bytes
- **Unit:** IPv4 address
- **Conversion:** Little-endian IPv4 (e.g., `c0 a8 01 63` → `192.168.1.99`)
- **Description:** Local IP address of the device.

## Characteristic DEVICE_COMMAND ("babe")

### Record layout

The DEVICE_COMMAND characteristic contains a fixed-size record of 8 bytes with
the following layout:

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 4 | `command_code` |
| 4 | 4 | `command_param` |

Reading this characteristic returns the last command sent; writing -- the
normal usecase -- sends a new command with the given code and parameter.

### Command codes

| Code (hex) | Command | Notes |
| --- | --- | --- |
| `0x1000` | SET_DAY_STATISTICS_DAY | Param is day number starting at 0 |
| `0x1001` | FORGET_THIS_DEVICE | |
| `0x1002` | BT_KEEP_ALIVE | Param value is unknown, only `0x3c` has been observed |
| `0x1003` | FORCE_ALL_SENSORS_ON | Param value is unknown, only `0x3c` has been observed |
| `0x1004` | CLEAR_SMART_COOKING_EVENT_LIST | Param is always 0 |
| `0x1005` | SET_CLOCK_UNIX | Param is a Unix timestamp (32-bit unsigned integer) |
| `0x1006` | SENSOR_BOOST_MODE_1H | |
| `0x1007` | SET_PAN_TEMP_ALERT | |
| `0x1008` | SET_TIMED_POWER_OFF | |
| `0x1009` | SET_IMMEDIATE_POWER_OFF | Param is always 0 |
| `0x100a` | SET_TIMEZONE | Param is a timezone offset in seconds, e.g. 3600 for +1 hour |
| `0x100b` | SET_PCU_RADIO_CHANNEL | |
| `0x100c` | START_RCL_2_PAIRING | |
| `0x100d` | HA_8_SET_BITMASK | |
| `0x100e` | HA_8_CLEAR_BITMASK | |
| `0x100f` | SET_MIU_LOCK | |
| `0x1010` | OPEN_MIU_LOCK | |
| `0x1011` | HA_8_WRITE_BITMASK | |
| `0x1012` | FORCE_PCU_NODE_INFO_REFRESH | |
| `0x1013` | REQUEST_FAST_BLE_MODE | Param value is unknown, only `0xb4` has been observed |
| `0x1014` | SET_MIU_RCL2_TX_POWER | |
| `0x1015` | SET_MIU_BLE_TX_POWER | |
| `0x1016` | SET_MIU_WIFI_TX_POWER | |
| `0x1017` | SET_PCU_RCL2_TX_POWER | |
| `0x1018` | IDENTIFY_DEVICE | |
| `0x1019` | HUB_IDENTIFY_NODE | |
| `0x101a` | HUB_DELETE_NODE | |
| `0x101b` | CONFIG_READ_BANK | Param selects config bank to read, only 2 has been observed. It should be followed by READ_CONFIG_BANK ("dcbb") |
| `0x101c` | PCU_CUR_CAL_START | |
| `0x101d` | PCU_CUR_CAL_SELECT_OVEN | |
| `0x101e` | PCU_CUR_CAL_SELECT_STOVE | |
| `0x101f` | PCU_CUR_CAL_STOP | |
| `0x1020` | CHILD_LOCK_ACTIVATE_IF_ENABLED | |
| `0x1021` | STOVE_GUARD_TIMERS_CLEAR | |
| `0x1022` | LTA_CLEAR_RESET | |
| `0x1023` | ZMOD_DISABLE | |
| `0x1024` | ZMOD_ENABLE | |
| `0x1025` | REQUEST_LOG_DESC | |
| `0x1026` | REQUEST_FACTORY_RESET | |
| `0x1027` | DAYLOG_SENT_TO_CLOUD | |
| `0x1028` | LPC_RESET | |
| `0x1029` | EXT_FLASH_RESET | |
| `0x102a` | EXCELITAS_RESET | |
| `0x102b` | RCL2_SEEK_CHANNEL | |
| `0x2001` | SET_HOOD_MOTOR_SPEED_STEP | |
| `0x2002` | SET_HOOD_MOTOR1_SPEED_RAW | |
| `0x2003` | SET_HOOD_MOTOR2_SPEED_RAW | |
| `0x2004` | SET_HOOD_MOTOR_AUTO_MODE | |
| `0x2005` | SET_HOOD_LIGHT_PRESET | |
| `0x2006` | SET_HOOD_LIGHT_BRIGHTNESS | |
| `0x2007` | SET_HOOD_LIGHT_TEMPERATURE | |
| `0x2008` | SET_HOOD_LIGHT_AUTO_MODE | |
| `0x2009` | SET_HOOD_FILTER_CHANGED | |
| `0x200a` | SET_HOOD_LOCK | |
| `0x200b` | OPEN_HOOD_LOCK | |

## Characteristic GDT_COMMAND ("abd3")

### Record layout

The GDT_COMMAND characteristic contains a fixed-size record of 8 bytes with the
following layout:

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 4 | `gdt_command_code` |
| 4 | 4-6 (?) | `gdt_command_param` |

Reading this characteristic returns the last GDT command sent; writing -- the
normal usecase -- sends a new GDT command with the given code and parameter.

Some GDT commands needs additiona arguments, like SET_DEVICE_NAME. In this
case, the device name is first sent using SEND_GDT_DATA ("abd2"), followed by
the actual command in GDT_COMMAND ("abd3").

Some GDT commands return data, these are then returned after the command is
received in the GDT_DATA ("abd2") characteristic.

GDT likely refers to Google Android Data Transport API.

### GDT Command codes

| Code (hex) | GDT Command | Notes |
| --- | --- | --- |
| `0x00000000` | START_WIFI_SCAN |
| `0x00000001` | STOP_WIFI_SCAN |
| `0x00000002` | SET_WIFI_CREDENTIALS |
| `0x00000003` | SET_DAY_STATISTICS_DAY_2 | Param is day number starting at 0 |
| `0x00000004` | SEND_HA8_GROUP |
| `0x00000005` | SEND_WIFI_CLOUD_TEST |
| `0x00000006` | PCU_INFO | Param is always `0x00000000` |
| `0x00000007` | RAW_PCU_REQ | Param is always `0x00000000` |
| `0x00000008` | SET_DEVICE_NAME |
| `0x00000009` | GET_HUB_NODE_NAMES | Param is always `0x00000000` |

It is not clear how or if the GDT command SET_DAY_STATISTICS_DAY_2 differs from
the device command SET_DAY_STATISTICS_DAY.

## Characteristic DAY_STATISTICS ("abdf")

### Record layout

The DAY_STATISTICS characteristic contains a fixed-size record of 16 bytes with
the following layout:

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 2 | `day_count` |
| 2 | 2 | `temp_ambient_mean` |
| 4 | 2 | `rh_mean` |
| 6 | 2 | `aqi_final_mean` |
| 8 | 2 | `eco2_mean` |
| 10 | 2 | `tvoc_mean` |
| 12 | 2 | `particle_index_mean` |
| 14 | 1 | `alarm_count` |
| 15 | 1 | `cooking_count` |

All values are unsigned. The day to return is selected using the
SET_DAY_STATISTICS_DAY command in DEVICE_COMMAND ("babe").

#### temp_ambient_mean
- **Unit:** °C
- **Conversion:** temp = (raw * 0.01) - 50
- **Description:** Average ambient temperature. A value of 0 indicates no data.

#### rh_mean
- **Unit:** %RH
- **Conversion:** humidity = raw / 100. A value of 0 indicates no data.

## Characteristic DCV_SENSOR_REPORT ("abd4")

### Record layout

Each DCV_SENSOR_REPORT payload begins with a 4 byte header including an
entry_count number, followed by that many fixed-size DCV sensor report entries.

| Offset | Size | Field |
| --- | --- | --- |
| 0 | 1 | `data_version` |
| 1 | 1 | `entry_count` |
| 2 | 2 | `dcv_flags` |
| 4 | 15 × `entry_count` | `dcv_entries[i]` |

Each `dcv_entries[i]` entry (15 bytes) has:

| Offset (entry) | Size | Field |
| --- | --- | --- |
| 0 | 1 | `hub_side_lqi` |
| 1 | 1 | `hub_side_ed` |
| 2 | 1 | `vent_control_final` |
| 3 | 1 | `vent_control_auto` |
| 4 | 1 | `motor_1_speed` |
| 5 | 1 | `stove_guard_alarm` |
| 6 | 1 | `aqi` |
| 7 | 1 | `activity` |
| 8 | 1 | `rht_comfort_level` |
| 9 | 2 | `status_flags` |
| 11 | 2 | `error_flags` |
| 13 | 1 | `sensor_side_lqi` |
| 14 | 1 | `sensor_side_ed` |

### Field details

#### data_version
- **Size:** 8 bit unsigned
- **Description:** Data version. Currently always `0x01`.

#### entry_count
- **Size:** 8 bit unsigned
- **Description:** Number of DCV sensor report entries that follow.

#### dcv_flags
- **Size:** 16 bit unsigned
- Description:** DCV flags bitfield.

The only known flag is bit 0 (`0x0001`), which indicates that multiple DCV
nodes are connected. The client should call the GDT command
`GET_HUB_NODE_NAMES` to get more information about these nodes.

#### dcv_entries[i]
- **Size:** 1 bytes per entry
- **Description:** Repeating event entry; see subfields.

#### hub_side_lqi
- **Size:** 8 bit signed
- **Description:** Hub side link quality indicator, always negative.

#### hub_side_ed
- **Size:** 8 bit unsigned
- **Description:** Hub side energy detect (an RSSI-like metric).

#### vent_control_final
- **Size:** 8 bit unsigned
- **Description:** Vent control, details unknown.

#### vent_control_auto
- **Size:** 8 bit unsigned
- **Description:** Vent control, details unknown.

#### motor_1_speed
- **Size:** 8 bit unsigned
- **Description:** Motor 1 speed value.

#### stove_guard_alarm
- **Size:** 8 bit unsigned
- **Description:** Stove guard alarm status.

#### aqi
- **Size:** 8 bit unsigned
- **Description:** Air quality index value.

#### activity
- **Size:** 8 bit unsigned
- **Description:** Activity level.

#### rht_comfort_level
- **Size:** 8 bit unsigned
- **Description:** RHT (Relative Humidity and Temperature) comfort level.

#### status_flags
- **Size:** 16 bit unsigned
- **Description:** Status flags bitfield.

The only known flag is bit 0 (`0x0001`), which seem to indicate that this DCV
is active or enabled.

#### error_flags
- **Size:** 16 bit unsigned
- **Description:** Error flags bitfield. Details unknown.

## Tooling support

The following command line options are available for the `ble-serial` tool:

* `--advertisement` now shows the complete list of advertisement data fields.
* `--event-log` now listens to EVENT_LOG notifications until you press Ctrl+C, printing entries as they arrive.
