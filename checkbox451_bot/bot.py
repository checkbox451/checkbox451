import os
from contextlib import asynccontextmanager

from aiogram import Bot

obj: Bot


def init():
    global obj
    obj = Bot(os.environ["TELEGRAM_BOT_TOKEN"])


@asynccontextmanager
async def session_close():
    try:
        yield
    finally:
        await obj.session.close()
