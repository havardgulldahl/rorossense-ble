"Code to connect to Røroshetta Sense Bluetooth api"

import asyncio
import os
from bleak import BleakClient

MODEL_NBR_UUID = "2A24"


async def main(address):
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")

        await client.pair()
        print("Paired")

        model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        print(f"Model Number: {model_number.decode()}")


if __name__ == "__main__":

    # read ADDRESS and UUID from .env file

    from dotenv import load_dotenv  # pip install python-dotenv

    load_dotenv()

    ADDRESS = os.getenv("ADDRESS")
    UUID = os.getenv("UUID")
    asyncio.run(main(ADDRESS))
