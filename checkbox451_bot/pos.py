import asyncio
import os

from escpos.config import Config
from escpos.escpos import Escpos

config = os.environ.get("PRINTER_CONFIG")
bottom = int(os.environ.get("PRINT_BOTTOM_MARGIN") or 4)
logo = os.environ.get("PRINT_LOGO_PATH")
logo_impl = os.environ.get("PRINT_LOGO_IMPL", "bitImageRaster")


def print_receipt(text):
    if not config:
        return

    c = Config()
    c.load(config)

    printer: Escpos = c.printer()

    if logo:
        printer.image(logo, impl=logo_impl)

    printer.text(text + "\n" * bottom)


async def print_receipt_async(text):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, print_receipt, text)
