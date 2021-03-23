import asyncio
from logging import getLogger

log = getLogger(__name__)


def main():
    from checkbox451_bot import __version__ as version

    log.info(f"{version=}")

    from checkbox451_bot import (
        auth,
        goods,
        handlers,
        kbd,
        pb2gsheet,
        shift_close,
    )

    auth.init()
    goods.init()
    kbd.init()

    loop = asyncio.get_event_loop()
    loop.create_task(pb2gsheet.run())
    loop.create_task(shift_close.scheduler())

    handlers.start_polling()


if __name__ == "__main__":
    main()
