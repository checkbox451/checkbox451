import asyncio
import functools
import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

import pygsheets
import schedule

from checkbox451_bot import auth, bot, checkbox_api, handlers

service_account_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
spreadsheet_key = os.environ.get("GOOGLE_SPREADSHEET_KEY")
worksheet_title = os.environ.get("GOOGLE_WORKSHEET_TITLE")
shift_close_time = os.environ.get("SHIFT_CLOSE_TIME")

log = logging.getLogger(__name__)


async def error(msg):
    await handlers.helpers.broadcast(
        None,
        auth.ADMIN,
        handlers.helpers.error,
        msg,
    )


@asynccontextmanager
async def bot_init():
    bot.init()
    try:
        yield
    finally:
        await bot.obj.session.close()


def sync(coro):
    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        asyncio.create_task(coro(*args, **kwargs))

    return wrapper


async def shift_close(logger: Any = log):
    if await checkbox_api.shift.shift_balance() is None:
        logger.info("shift is already closed")
        return

    async with bot_init():
        try:
            income = await checkbox_api.shift.shift_close()
        except Exception as e:
            await error(str(e))
            logger.error(f"shift close failed: {e!s}")
            return

        today = date.today().isoformat()
        logger.info(f"{today}: shift closed: income {income:.02f}")

        if income and service_account_file:
            try:
                client = pygsheets.authorize(
                    service_account_file=service_account_file
                )
                spreadsheet = client.open_by_key(spreadsheet_key)
                wks = spreadsheet.worksheet_by_title(worksheet_title)
                wks.append_table([[today, income]])
            except Exception as e:
                await error(str(e))
                logger.error(f"shift reporting failed: {e!s}")
                return

        await handlers.helpers.broadcast(
            None,
            auth.SUPERVISOR,
            bot.obj.send_message,
            f"Дохід {income:.02f} грн",
        )


async def scheduler():
    if not shift_close_time:
        return

    schedule.every().day.at(shift_close_time).do(sync(shift_close))
    log.info(f"{shift_close_time=}")

    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


class Logger:
    error = print
    info = print


if __name__ == "__main__":
    asyncio.run(shift_close(logger=Logger))
