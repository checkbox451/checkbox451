from functools import lru_cache

from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from checkbox451_bot.goods import get_items
from checkbox451_bot.kbd.buttons import btn_auth, btn_cancel, btn_receipt

remove = ReplyKeyboardRemove()

auth = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    KeyboardButton(btn_auth, request_contact=True),
)
start = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1).add(btn_receipt)


@lru_cache(maxsize=1)
def goods():
    return ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True, row_width=1
    ).add(*get_items(), btn_cancel)
