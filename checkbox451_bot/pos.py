import asyncio
import os
from logging import getLogger
from typing import Optional

from escpos.config import Config
from escpos.escpos import Escpos

config = os.environ.get("PRINTER_CONFIG")
bottom = int(os.environ.get("PRINT_BOTTOM_MARGIN") or 4)
logo = os.environ.get("PRINT_LOGO_PATH")
logo_impl = os.environ.get("PRINT_LOGO_IMPL", "bitImageRaster")

log = getLogger(__name__)


async def _printer() -> Optional[Escpos]:
    if not config:
        return

    c = Config()
    c.load(config)

    loop = asyncio.get_event_loop()

    err = None
    for attempt in range(5):
        try:
            return await loop.run_in_executor(None, c.printer)
        except Exception as e:
            err = e
            log.warning("printer retry attempt: %s", attempt + 1)

        await asyncio.sleep(1)

    raise err


async def _print_receipt(printer, text):
    if logo:
        printer.image(logo, impl=logo_impl)

    printer.text(text + "\n" * bottom)


async def print_receipt(text):
    if not (printer := await _printer()):
        return

    asyncio.create_task(_print_receipt(printer, text))
