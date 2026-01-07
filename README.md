# RørosSense a.k.a Safera Sense BLE 

This project is a attempt to reverse-engineer and liberate the Bluetooth Low Energy (BLE) protocol used by the **Safera Sense** smart cooking sensor (as found in **RørosHetta** kitchen fans).

## What is this?

This repo contains the findings from sniffing, poking, and prodding the `IFU10CR-PRO` device. I have tried to document the protocol as best as I can.

The repo also contains a `custom_component` intended for Home Assistant integration. **WIP!**


## What's Reversed?

We have successfully mapped out the proprietary GATT services (the ones hiding behind the UUID `...f00d-...`). Here is the high-level menu:

*   **Telemetry**: Real-time reading of **Humidity**, **eCO2** (Carbon Dioxide equivalents), **tVOC** (Volatile Organic Compounds), and raw **Air Quality Index** (AQI).
*   **Cooking Intelligence**: We found the flags for "Presence Detected" and specific "Stove Activity Levels".
*   **Control**:
    *   **Fan**: Set speeds 1-3, activate **Boost (Level 4)**, or toggle **Auto Mode**.
    *   **Lights**: Dim or brighten the hood lights.
*   **Device info**: Read the connected model name, SSID, SSID client name as well as hardware and software versions.  


Does not work yet:

*   **Temperature**
*   **PM2.5**
*   **Alarm level**
*   **Filter change needed**

> For the nitty-gritty byte-level details, check out [docs/reverse.md](docs/reverse.md).

## The Client (`client.py`)

The `src/client.py` is a Python class leveraging `bleak` to talk to the device. It handles the weird byte-swapping, connection logic, and notification parsing for you.

### Requirements

```bash
pip install bleak python-dotenv
```

### Usage Examples

First, find your device's BLE MAC address. Then you can use the client like this:

#### 1. Reading Sensor Data (Live Stream)

```python
import asyncio
from src.client import RoroshettaSenseClient

async def monitor_hood():
    # Replace with your actual BLE address
    client = RoroshettaSenseClient("D4:6A:C8:XX:XX:XX")
    await client.connect()
    
    print("Sniffing the stew...")
    # This starts a loop that prints parsed data 
    # e.g., "eCO2: 402 ppm", "Presence: Detected"
    await client.start_parsing_payload() 

asyncio.run(monitor_hood())
```

#### 2. Controlling Fan & Lights

```python
import asyncio
from src.client import RoroshettaSenseClient

async def chef_mode():
    client = RoroshettaSenseClient("D4:6A:C8:XX:XX:XX")
    await client.connect()

    print("Lights!")
    await client.set_light_level(3) # Max brightness (0-3)

    print("Things are getting steamy, engage Boost!")
    await client.set_fan_speed(level=4) 
    
    # Or let the sensor decide
    # await client.set_fan_speed(level=0, auto=True)

    await client.disconnect()

asyncio.run(chef_mode())
```

## Disclaimer

This is an unofficial project, not affiliated with Safera or RørosHetta. Use this code at your own risk—don't burn your dinner (or your fancy sensor).
