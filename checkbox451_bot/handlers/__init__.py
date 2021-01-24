import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

bot: Bot


def start_polling():
    global bot

    token = os.environ["TOKEN"]
    bot = Bot(token)
    dispatcher = Dispatcher(bot)
    dispatcher.middleware.setup(LoggingMiddleware())

    from checkbox451_bot.handlers import admin, auth, cashier

    admin.init(dispatcher)
    auth.init(dispatcher)
    cashier.init(dispatcher)

    executor.start_polling(dispatcher, skip_updates=True)
