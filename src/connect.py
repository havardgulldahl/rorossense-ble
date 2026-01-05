import asyncio
import logging
import os
from bleak import BleakClient, BleakScanner

# Setter opp logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def explore_device(address):
    logger.info("Søker etter enhet: %s", address)
    device = await BleakScanner.find_device_by_address(
        address, timeout=10.0, cb={"use_bdaddr": True}
    )

    if not device:
        logger.error("Fant ikke enheten.")
        return

    async with BleakClient(device) as client:
        logger.info(f"Tilkoblet: {client.is_connected}")

        # Går gjennom alle tjenester (Services)
        for service in client.services:
            logger.info(f"\n" + "=" * 60)
            logger.info(f"SERVICE: {service.uuid} ({service.description})")
            logger.info("=" * 60)

            # Går gjennom alle egenskaper (Characteristics) i tjenesten
            for char in service.characteristics:
                logger.info(f"\n  [Characteristic] {char.uuid}")
                logger.info(f"    Beskrivelse: {char.description}")
                logger.info(f"    Handle: {char.handle}")
                logger.info(
                    f"    Egenskaper (Properties): {', '.join(char.properties)}"
                )

                # Hvis karakteristikken kan leses ("read"), prøver vi å hente verdien
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        # Viser verdien som Hex (for sensor-verdier) og som String (for navn/versjoner)
                        hex_val = value.hex(":")
                        try:
                            str_val = value.decode("utf-8")
                        except:
                            str_val = "<Kunne ikke tolkes som tekst>"

                        logger.info(f"    Nåværende verdi (Hex): {hex_val}")
                        logger.info(f"    Nåværende verdi (Str): {str_val}")
                    except Exception as e:
                        logger.warning(f"    Kunne ikke lese verdi: {e}")

                # Går gjennom alle beskrivelser (Descriptors) for denne karakteristikken
                for descriptor in char.descriptors:
                    logger.info(
                        f"    [Descriptor] {descriptor.uuid} (Handle: {descriptor.handle})"
                    )
                    try:
                        desc_value = await client.read_gatt_descriptor(
                            descriptor.handle
                        )
                        logger.info(f"      Verdi: {desc_value}")
                    except Exception as e:
                        logger.info(f"      Kunne ikke lese descriptor: {e}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    ADDRESS = os.getenv("ADDRESS")

    if ADDRESS:
        asyncio.run(explore_device(ADDRESS))
    else:
        logger.error("Fant ingen adresse i .env fila.")
