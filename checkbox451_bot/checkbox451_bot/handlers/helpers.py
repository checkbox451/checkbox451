from io import BytesIO

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
)

from .. import db, kbd, msg


async def start(message: Message):
    await message.answer(msg.START, reply_markup=kbd.start)


async def broadcast(user_id, role_name, send_message, *args, **kwargs):
    session = db.Session()
    for user in session.query(db.Role).get(role_name).users:
        if user.user_id != user_id:
            await send_message(user.user_id, *args, **kwargs)


async def send_receipt(
    user_id,
    receipt_id,
    receipt_qr,
    receipt_url,
    receipt_text,
):
    from . import bot

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
