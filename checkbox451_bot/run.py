import asyncio
import time
from logging import getLogger

from requests import RequestException

log = getLogger(__name__)


def main():
    from checkbox451_bot import __version__ as version

    log.info(f"{version=}")

    from checkbox451_bot import (
        checkbox_api,
        goods,
        gsheet,
        handlers,
        shift_close,
    )

    while True:
        try:
            goods.items()
        except RequestException as e:
            log.error(e)
            time.sleep(60)
            continue
        break

    checkbox_api.receipt.get_receipt_params()

    loop = asyncio.get_event_loop()
    loop.create_task(gsheet.privat24.Privat24TransactionProcessor().run())
    loop.create_task(gsheet.fondy.FondyTransactionProcessor().run())
    loop.create_task(shift_close.scheduler())

    handlers.start_polling()


if __name__ == "__main__":
    main()
