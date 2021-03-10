import asyncio
import functools
import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

import schedule

from checkbox451_bot import auth, bot, checkbox_api, gsheet
from checkbox451_bot.handlers import helpers

worksheet_title = os.environ.get("GOOGLE_WORKSHEET_TITLE")
shift_close_time = os.environ.get("SHIFT_CLOSE_TIME")

log = logging.getLogger(__name__)


async def error(msg):
    await helpers.broadcast(
        None,
        auth.ADMIN,
        helpers.error,
        msg,
    )


@asynccontextmanager
async def bot_session_close():
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

    try:
        income = await checkbox_api.shift.shift_close()
    except Exception as e:
        await error(str(e))
        logger.error(f"shift close failed: {e!s}")
        return

    today = date.today().isoformat()
    logger.info(f"{today}: shift closed: income {income:.02f}")

    if income:
        try:
            await gsheet.append_row([today, income], worksheet_title)
        except Exception as e:
            await error(str(e))
            logger.error(f"shift reporting failed: {e!s}")
            return

    await helpers.broadcast(
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


async def main():
    async with bot_session_close():
        await shift_close(logger=Logger)


if __name__ == "__main__":
    asyncio.run(main())
