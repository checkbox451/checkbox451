import os
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.types import ParseMode

obj: Bot


def init():
    global obj
    obj = Bot(os.environ["TELEGRAM_BOT_TOKEN"], parse_mode=ParseMode.HTML)


@asynccontextmanager
async def session_close():
    init()
    try:
        yield
    finally:
        await (await obj.get_session()).close()
