from aiogram.types import Message

from .. import auth, kbd, msg
from . import bot, error, helpers


def init(dispatcher):
    @dispatcher.message_handler(content_types=["contact"])
    @error.error_handler
    async def contact(message: Message):
        if message.contact is not None:
            user = auth.sign_in(message.contact)
            if user and user.roles:
                return

            await message.answer(msg.ADMIN_APPROVE, reply_markup=kbd.remove)
            await helpers.broadcast(
                message.chat.id,
                auth.ADMIN,
                bot.send_message,
                f"new user: {user}",
            )
