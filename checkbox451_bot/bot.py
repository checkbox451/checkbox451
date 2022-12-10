from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.types import ParseMode

from checkbox451_bot.config import Config

obj: Bot


def init():
    global obj
    obj = Bot(
        Config().get("telegram_bot", "token", required=True),
        parse_mode=ParseMode.HTML,
    )


@asynccontextmanager
async def session_close():
    init()
    try:
        yield
    finally:
        await (await obj.get_session()).close()
