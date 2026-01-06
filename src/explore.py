import asyncio
import logging
import os
from bleak import BleakClient, BleakScanner

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def explore_device(address):
    logger.info("Scanning for device: %s", address)
    device = await BleakScanner.find_device_by_address(
        address, timeout=10.0, cb={"use_bdaddr": True}
    )

    if not device:
        logger.error("Device not found.")
        return

    async with BleakClient(device) as client:
        logger.info(f"Connected: {client.is_connected}")

        # Iterate through all Services
        for service in client.services:
            logger.info(f"\n" + "=" * 60)
            logger.info(f"SERVICE: {service.uuid} ({service.description})")
            logger.info("=" * 60)

            # Iterate through all Characteristics in the service
            for char in service.characteristics:
                logger.info(f"\n  [Characteristic] {char.uuid}")
                logger.info(f"    Description: {char.description}")
                logger.info(f"    Handle: {char.handle}")
                logger.info(f"    Properties: {', '.join(char.properties)}")

                # If the characteristic can be read, try to fetch the value
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        # Show value as Hex (for sensor values) and as String (for names/versions)
                        hex_val = value.hex(":")
                        try:
                            str_val = value.decode("utf-8")
                        except:
                            str_val = "<Could not interpret as text>"

                        logger.info(f"    Current value (Hex): {hex_val}")
                        logger.info(f"    Current value (Str): {str_val}")
                    except Exception as e:
                        logger.warning(f"    Could not read value: {e}")

                # Iterate through all Descriptors for this characteristic
                for descriptor in char.descriptors:
                    logger.info(
                        f"    [Descriptor] {descriptor.uuid} (Handle: {descriptor.handle})"
                    )
                    try:
                        desc_value = await client.read_gatt_descriptor(
                            descriptor.handle
                        )
                        logger.info(f"      Value: {desc_value}")
                    except Exception as e:
                        logger.info(f"      Could not read descriptor: {e}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    ADDRESS = os.getenv("ADDRESS")

    if ADDRESS:
        asyncio.run(explore_device(ADDRESS))
    else:
        logger.error("Found no address in .env file.")
