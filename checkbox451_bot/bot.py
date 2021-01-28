import os

from aiogram import Bot

obj: Bot


def init():
    global obj

    token = os.environ["TOKEN"]
    obj = Bot(token)
