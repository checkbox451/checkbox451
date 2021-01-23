from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from . import msg

remove = ReplyKeyboardRemove()

auth = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    KeyboardButton(msg.AUTHENTICATE, request_contact=True),
)

start = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    msg.CREATE_RECEIPT,
)

goods = None


def init():
    global goods
    from .goods import items

    goods = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True,
        row_width=1,
    ).add(*items)
