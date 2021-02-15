import os

from aiogram import Bot

obj: Bot


def init():
    global obj

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    obj = Bot(token)
