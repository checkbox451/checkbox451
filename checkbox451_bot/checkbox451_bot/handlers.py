import os
import re
from io import BytesIO
from logging import getLogger

from aiogram import Bot, Dispatcher
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
)

from . import auth, checkbox_api, kbd, msg
from .goods import goods

log = getLogger(__name__)

token = os.environ["TOKEN"]
bot = Bot(token)
dp = Dispatcher(bot)


async def error(message, exception):
    await message.answer(
        f"*Помилка:* `{exception!s}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kbd.start,
    )


@dp.message_handler(commands=["start"])
@auth.require
async def start(message: Message):
    await message.answer(msg.START, reply_markup=kbd.start)


@dp.message_handler(content_types=["contact"])
async def contact(message: Message):
    if message.contact is not None:
        if auth.sign_in(message.contact):
            await start(message)
        else:
            await message.answer(msg.DENIED, reply_markup=kbd.remove)


@dp.message_handler(regexp=msg.CREATE_RECEIPT)
@auth.require
async def create(message: Message):
    await message.answer(msg.SELECT_GOOD, reply_markup=kbd.goods)


@dp.message_handler(
    regexp="({})".format("|".join(re.escape(good) for good in goods))
)
@auth.require
async def sell(message: Message):
    good = goods[message.text]

    try:
        receipt_data = await checkbox_api.sell(good)
    except (AssertionError, checkbox_api.CheckboxAPIException) as e:
        return await error(message, e)

    receipt_id, receipt_qr, receipt_url, receipt_text = receipt_data

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            msg.PRINT,
            callback_data=f"print:{receipt_id}",
        )
    )

    await bot.send_photo(
        message.chat.id,
        BytesIO(receipt_qr),
        caption=f"{receipt_url}\n\n```{receipt_text}```",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )
    await start(message)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("print:"))
async def print_(callback_query: CallbackQuery):
    _, receipt_id = callback_query.data.split(":")
    log.info("print: %s", receipt_id)
    await callback_query.answer(msg.PRINTING)
