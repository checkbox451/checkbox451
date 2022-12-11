import asyncio
import functools
import logging
from datetime import date
from typing import Any

import schedule

from checkbox451_bot import auth, checkbox_api, gsheet
from checkbox451_bot.bot import Bot
from checkbox451_bot.checkbox_api.helpers import aiohttp_session
from checkbox451_bot.config import Config
from checkbox451_bot.handlers import helpers

worksheet_title = Config().get("google", "worksheet", "title")
shift_close_time = Config().get("checkbox", "shift_close_time")

log = logging.getLogger(__name__)


async def error(msg):
    await helpers.broadcast(
        None,
        auth.ADMIN,
        helpers.error,
        msg,
    )


def sync(coro):
    @functools.wraps(coro)
    def wrapper(*args, **kwargs):
        asyncio.create_task(coro(*args, **kwargs))

    return wrapper


@aiohttp_session
async def shift_close(*, logger: Any = log, chat_id=None, session):
    shift = await checkbox_api.shift.current_shift(session=session)
    if shift is None:
        logger.info("shift is already closed")
        checkbox_api.auth.sign_out()
        return

    try:
        income = await checkbox_api.shift.shift_close(session=session)
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

    answer = functools.partial(
        helpers.broadcast,
        chat_id,
        auth.SUPERVISOR,
        Bot().send_message,
    )
    await helpers.send_report(answer, shift)

    return income


async def scheduler():
    if not shift_close_time:
        log.warning("missing shift close time; ignoring...")
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
    async with Bot().session_close():
        await shift_close(logger=Logger)


if __name__ == "__main__":
    asyncio.run(main())
