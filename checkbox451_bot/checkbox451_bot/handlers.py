import functools
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

from . import auth, checkbox_api, db, kbd, msg
from .goods import goods

log = getLogger(__name__)

token = os.environ["TOKEN"]
bot = Bot(token)
dp = Dispatcher(bot)


async def error(message, exception):
    log.error("error: %r", exception)
    await message.answer(
        f"*Помилка:* `{exception!s}`",
        parse_mode=ParseMode.MARKDOWN,
    )
    await start(message)


def error_handler(handler):
    @functools.wraps(handler)
    async def wrapper(message: Message):
        try:
            return await handler(message)
        except Exception as e:
            return await error(message, e)

    return wrapper


@dp.message_handler(commands=["start"])
@auth.require(auth.CASHIER)
@error_handler
async def start(message: Message):
    await message.answer(msg.START, reply_markup=kbd.start)


@dp.message_handler(content_types=["contact"])
@error_handler
async def contact(message: Message):
    if message.contact is not None:
        if auth.sign_in(message.contact):
            return await start(message)
        await message.answer(msg.ADMIN_APPROVE, reply_markup=kbd.remove)


@dp.message_handler(regexp=re.escape(msg.CREATE_RECEIPT))
@auth.require(auth.CASHIER)
@error_handler
async def create(message: Message):
    await message.answer(msg.SELECT_GOOD, reply_markup=kbd.goods)


@dp.message_handler(regexp=f"({'|'.join(re.escape(good) for good in goods)})")
@auth.require(auth.CASHIER)
@error_handler
async def sell(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")

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
@auth.require(auth.CASHIER)
@error_handler
async def print_(callback_query: CallbackQuery):
    _, receipt_id = callback_query.data.split(":")
    log.info("print: %s", receipt_id)
    await callback_query.answer(msg.PRINTING)


@dp.message_handler(commands=["users"])
@auth.require(auth.ADMIN)
@error_handler
async def users(message: Message):
    session = db.Session()
    users_repr = [
        f"{u.user_id}: {u.phone_number.e164} ({u.full_name}) {u.roles}"
        for u in session.query(db.User)
    ]
    text = "\n".join(users_repr)
    await message.answer(text, reply_markup=kbd.remove)


@dp.message_handler(commands=["sign"])
@auth.require(auth.ADMIN)
@error_handler
async def sign(message: Message):
    args = message.get_args()
    if args == "on":
        auth.sign_mode = True
    elif args == "off":
        auth.sign_mode = False

    await message.answer(
        f"{message.get_command()} {'on' if auth.sign_mode else 'off'}"
    )
