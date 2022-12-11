from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from checkbox451_bot.goods import items

remove = ReplyKeyboardRemove()

auth = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    KeyboardButton("Авторизуватися", request_contact=True),
)

start = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    "Створити чек",
)

goods = ReplyKeyboardMarkup(
    resize_keyboard=True, one_time_keyboard=True, row_width=1
).add(*items())
