import functools
from logging import getLogger

from aiogram.types import Message, ParseMode

from .helpers import start

log = getLogger(__name__)


async def error(message, exception):
    log.error("error: %r", exception)
    await message.answer(
        f"<b>Помилка:</b> <code>{exception!s}</code>",
        parse_mode=ParseMode.HTML,
    )
    await start(message)


def error_handler(handler):
    @functools.wraps(handler)
    async def wrapper(message: Message):
        try:
            return await handler(message)
        except Exception as e:
            log.exception("exception!")
            return await error(message, e)

    return wrapper
