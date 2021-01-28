import functools
from io import BytesIO
from logging import getLogger
from typing import Union

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
)

from checkbox451_bot import auth, bot, db, kbd

log = getLogger(__name__)


async def start(user_id):
    await bot.obj.send_message(user_id, "Вітаю!", reply_markup=kbd.start)


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
            "Друкувати",
            callback_data=f"print:{receipt_id}",
        )
    )

    await bot.obj.send_photo(user_id, BytesIO(receipt_qr), caption=receipt_url)
    await bot.obj.send_message(
        user_id,
        f"<pre>{receipt_text}</pre>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


async def error(user_id, exception):
    await bot.obj.send_message(
        user_id,
        f"<b>Помилка:</b> <code>{exception}</code>",
        parse_mode=ParseMode.HTML,
    )


def error_handler(handler):
    @functools.wraps(handler)
    async def wrapper(message: Union[CallbackQuery, Message]):
        try:
            return await handler(message)
        except Exception as e:
            log.exception("handler error")
            if isinstance(message, CallbackQuery):
                await message.answer(f"Помилка: {e!s}", show_alert=True)
            else:
                await error(message.from_user.id, str(e))
                if auth.has_role(message.from_user.id, auth.CASHIER):
                    await start(message.from_user.id)
            await broadcast(message.from_user.id, auth.ADMIN, error, str(e))

    return wrapper
