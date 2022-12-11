from contextlib import asynccontextmanager
from functools import lru_cache

from aiogram import Bot as TelegramBot
from aiogram.types import ParseMode

from checkbox451_bot.config import Config


@lru_cache(maxsize=1)
class Bot(TelegramBot):
    def __init__(self):
        super().__init__(
            Config().get("telegram_bot", "token", required=True),
            parse_mode=ParseMode.HTML,
        )

    @asynccontextmanager
    async def session_close(self):
        try:
            yield
        finally:
            await (await self.get_session()).close()
