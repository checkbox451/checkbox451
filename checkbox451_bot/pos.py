import asyncio
from logging import getLogger
from pathlib import Path
from typing import Optional

from escpos.config import Config as EscposConfig
from escpos.escpos import Escpos

from checkbox451_bot.config import Config

log = getLogger(__name__)


class PrinterConfig(EscposConfig):
    def __repr__(self):
        args = ", ".join(f"{k}={v!r}" for k, v in self._printer_config.items())
        return f"{self._printer_name}({args})"

    def close_printer(self):
        if self._printer:
            try:
                self._printer.close()
            except Exception:
                log.exception("printer close error")

            self._printer = None


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
    try:
        if logo := Config().get("print", "logo", "path"):
            logo_impl = Config().get(
                "print", "logo", "impl", default="bitImageRaster"
            )
            printer.image(logo, impl=logo_impl)

        bottom = Config().get("print", "bottom_margin", default=4)
        printer.text(text + "\n" * bottom)
    finally:
        config.close_printer()


async def print_receipt(text):
    if not (printer := await _printer()):
        return

    asyncio.create_task(_print_receipt(printer, text))


def init():
    pos_yaml = Path("pos.yaml")

    if not pos_yaml.exists():
        log.warning("missing printer config file; ignoring...")
        return

    printer_config = PrinterConfig()
    printer_config.load(pos_yaml)

    log.info(f"{printer_config=}")

    return printer_config


config = init()
