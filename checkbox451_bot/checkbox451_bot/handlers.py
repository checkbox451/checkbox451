import functools
import os
import re
from io import BytesIO
from logging import getLogger

from aiogram import Bot, Dispatcher
from aiogram.contrib.middlewares.logging import LoggingMiddleware
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
dp.middleware.setup(LoggingMiddleware())


async def error(message, exception):
    log.error("error: %r", exception)
    await message.answer(
        f"<b>Помилка:</b> <code>{exception!s}</code>",
        parse_mode=ParseMode.HTML,
    )
    await start(message)


def error_handler(handler):
    @functools.wraps(handler)
    async def wrapper(message: Message):
        try:
            return await handler(message)
        except Exception as e:
            log.exception("exception!")
            return await error(message, e)

    return wrapper


async def broadcast(user_id, role_name, send_message, *args, **kwargs):
    session = db.Session()
    for user in session.query(db.Role).get(role_name).users:
        if user.user_id != user_id:
            await send_message(user.user_id, *args, **kwargs)


@dp.message_handler(commands=["start"])
@auth.require(auth.CASHIER)
@error_handler
async def start(message: Message):
    await message.answer(msg.START, reply_markup=kbd.start)


@dp.message_handler(content_types=["contact"])
@error_handler
async def contact(message: Message):
    if message.contact is not None:
        user = auth.sign_in(message.contact)
        if user and user.roles:
            return

        await message.answer(msg.ADMIN_APPROVE, reply_markup=kbd.remove)
        await broadcast(
            message.chat.id,
            auth.ADMIN,
            bot.send_message,
            f"new user: {user}",
        )


@dp.message_handler(regexp=re.escape(msg.CREATE_RECEIPT))
@auth.require(auth.CASHIER)
@error_handler
async def create(message: Message):
    await message.answer(msg.SELECT_GOOD, reply_markup=kbd.goods)


async def send_receipt(
    user_id,
    receipt_id,
    receipt_qr,
    receipt_url,
    receipt_text,
):
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            msg.PRINT,
            callback_data=f"print:{receipt_id}",
        )
    )

    await bot.send_photo(
        user_id,
        BytesIO(receipt_qr),
        caption=f"{receipt_url}\n\n<pre>{receipt_text}</pre>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


@dp.message_handler(regexp=f"({'|'.join(re.escape(good) for good in goods)})")
@auth.require(auth.CASHIER)
@error_handler
async def sell(message: Message):
    await bot.send_chat_action(message.chat.id, "typing")

    good = goods[message.text]

    try:
        receipt_id, receipt_url = await checkbox_api.sell(good)
    except (AssertionError, checkbox_api.CheckboxAPIException) as e:
        log.exception("failed to create a receipt")
        return await error(message, e)

    await message.answer("Чек успішно створено", reply_markup=kbd.remove)

    receipt_qr, receipt_text = await checkbox_api.get_receipt_extra(receipt_id)

    await send_receipt(
        message.chat.id,
        receipt_id,
        receipt_qr,
        receipt_url,
        receipt_text,
    )
    await start(message)
    await broadcast(
        message.chat.id,
        auth.SUPERVISOR,
        send_receipt,
        receipt_id,
        receipt_qr,
        receipt_url,
        receipt_text,
    )


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
    users_repr = [str(u) for u in session.query(db.User)]
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


@dp.message_handler(commands=["role"])
@auth.require(auth.ADMIN)
@error_handler
async def role(message: Message):
    user_id, role_name = message.get_args().split()
    session = db.Session()
    if user := session.query(db.User).get(user_id):
        auth.add_role(user, role_name, session=session)
        await message.answer(str(user))
        if user.user_id != message.chat.id:
            await bot.send_message(
                user.user_id,
                msg.START,
                reply_markup=kbd.start,
            )
    else:
        raise ValueError(f"no user: {user_id}")


@dp.message_handler(commands=["delete"])
@auth.require(auth.ADMIN)
@error_handler
async def delete(message: Message):
    user_id = message.get_args()
    session = db.Session()
    if user := session.query(db.User).get(user_id):
        session.delete(user)
        session.commit()
        await message.answer(f"deleted: {user_id}")
        await bot.send_message(user.user_id, msg.BYE, reply_markup=kbd.remove)
    else:
        raise ValueError(f"no user: {user_id}")


@dp.message_handler(commands=["receipt"])
@auth.require(auth.ADMIN)
@error_handler
async def receipt(message: Message):
    receipt_id = message.get_args()
    receipt_data = await checkbox_api.get_receipt_data(receipt_id)
    receipt_qr, receipt_url, receipt_text = receipt_data
    await send_receipt(
        message.chat.id,
        receipt_id,
        receipt_qr,
        receipt_url,
        receipt_text,
    )
