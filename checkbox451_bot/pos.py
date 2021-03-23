import asyncio
import os
from logging import getLogger
from typing import Optional

from escpos.config import Config
from escpos.escpos import Escpos

bottom = int(os.environ.get("PRINT_BOTTOM_MARGIN") or 4)
logo = os.environ.get("PRINT_LOGO_PATH")
logo_impl = os.environ.get("PRINT_LOGO_IMPL") or "bitImageRaster"

log = getLogger(__name__)


async def _printer() -> Optional[Escpos]:
    if not config:
        return

    loop = asyncio.get_event_loop()

    err = None
    for attempt in range(5):
        try:
            return await loop.run_in_executor(None, config.printer)
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


def init():
    pos_yaml = os.environ.get("PRINTER_CONFIG")

    if not pos_yaml:
        log.warning("missing printer config file; ignoring...")
        return

    printer_config = Config()
    printer_config.load(pos_yaml)

    return printer_config


config = init()
