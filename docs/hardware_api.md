# Hardware API Documentation

Extracted by `src/client.py` - discover_uuids() 

## Device Information

| Property | Value |
| :--- | :--- |
| **Manufacturer** | Safera Oy |
| **Model** | IFU10CR-PRO |
| **Device Name** | Røroshetta |
| **Current Wi-Fi** | ***** |

---

## GATT Profile

**Device Address:** `D4:6A:C8:XX:XX:XX`

### Service: Device Information
**UUID:** `0000180a-0000-1000-8000-00805f9b34fb` (Handle: 14)

| Characteristic | UUID | Handle (Dec/Hex) | Properties |
| :--- | :--- | :--- | :--- |
| Manufacturer Name String | `00002a29-0000-1000-8000-00805f9b34fb` | 15 (`0xf`) | `read` |
| Model Number String | `00002a24-0000-1000-8000-00805f9b34fb` | 17 (`0x11`) | `read` |
| Serial Number String | `00002a25-0000-1000-8000-00805f9b34fb` | 19 (`0x13`) | `read` |
| Hardware Revision String | `00002a27-0000-1000-8000-00805f9b34fb` | 21 (`0x15`) | `read` |
| Firmware Revision String | `00002a26-0000-1000-8000-00805f9b34fb` | 23 (`0x17`) | `read` |
| Software Revision String | `00002a28-0000-1000-8000-00805f9b34fb` | 25 (`0x19`) | `read` |

### Service: Nordic Semiconductor ASA (DFU)
**UUID:** `0000fe59-0000-1000-8000-00805f9b34fb` (Handle: 27)

| Characteristic | UUID | Handle (Dec/Hex) | Properties |
| :--- | :--- | :--- | :--- |
| Buttonless DFU | `8ec90003-f315-4f60-9fb8-838830daea50` | 28 (`0x1c`) | `indicate`, `write` |

### Service: Safera Custom (Main Service)
**UUID:** `0000f00d-1212-efde-1523-785fef13d123` (Handle: 31)

| Characteristic | UUID | Handle (Dec/Hex) | Properties |
| :--- | :--- | :--- | :--- |
| Sensor Data (Unknown) | `0000beef-1212-efde-1523-785fef13d123` | 32 (`0x20`) | `read`, `notify` |
| Control Pipe (Unknown) | `0000abba-1212-efde-1523-785fef13d123` | 35 (`0x23`) | `read`, `write`, `write-without-response` |
| Unknown | `0000dcba-1212-efde-1523-785fef13d123` | 37 (`0x25`) | `read` |
| Unknown | `0000dcbb-1212-efde-1523-785fef13d123` | 39 (`0x27`) | `read` |
| Command Pipe (Unknown) | `0000babe-1212-efde-1523-785fef13d123` | 41 (`0x29`) | `read`, `write`, `write-without-response` |
| Unknown | `0000abcd-1212-efde-1523-785fef13d123` | 43 (`0x2b`) | `read`, `notify` |
| Unknown | `0000abce-1212-efde-1523-785fef13d123` | 46 (`0x2e`) | `read`, `notify` |
| Unknown | `0000abcf-1212-efde-1523-785fef13d123` | 49 (`0x31`) | `read`, `notify` |
| Unknown | `0000abdf-1212-efde-1523-785fef13d123` | 52 (`0x34`) | `read`, `notify` |
| Start/End Setup (Unknown) | `0000abd1-1212-efde-1523-785fef13d123` | 55 (`0x37`) | `read`, `notify` |
| Unknown | `0000abd3-1212-efde-1523-785fef13d123` | 58 (`0x3a`) | `read`, `write`, `write-without-response` |
| Unknown | `0000abd2-1212-efde-1523-785fef13d123` | 60 (`0x3c`) | `read`, `write`, `notify`, `write-without-response` |
