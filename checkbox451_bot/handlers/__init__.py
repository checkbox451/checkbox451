from aiogram import Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor

from checkbox451_bot import bot
from checkbox451_bot.handlers import admin, auth, cashier, helpers


def start_polling():
    dispatcher = Dispatcher(bot.obj)
    dispatcher.middleware.setup(LoggingMiddleware())

    admin.init(dispatcher)
    auth.init(dispatcher)
    cashier.init(dispatcher)

    executor.start_polling(dispatcher, skip_updates=True)
