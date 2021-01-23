import functools
from io import BytesIO
from logging import getLogger

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
)

from checkbox451_bot import db, kbd, msg
from checkbox451_bot.handlers import bot

log = getLogger(__name__)


async def start(message: Message):
    await message.answer(msg.START, reply_markup=kbd.start)


async def broadcast(user_id, role_name, send_message, *args, **kwargs):
    session = db.Session()
    role = session.query(db.Role).get(role_name)
    if role:
        for user in role.users:
            if user.user_id != user_id:
                await send_message(user.user_id, *args, **kwargs)


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


async def error(message, exception):
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
            log.exception("handler error")
            return await error(message, e)

    return wrapper
