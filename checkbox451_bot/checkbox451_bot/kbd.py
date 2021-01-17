from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from . import msg
from .goods import goods as _goods

remove = ReplyKeyboardRemove()

auth = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    KeyboardButton(msg.AUTHENTICATE, request_contact=True),
)

start = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    msg.CREATE_RECEIPT,
)

goods = ReplyKeyboardMarkup(
    resize_keyboard=True,
    one_time_keyboard=True,
    row_width=1,
).add(*_goods)
