from aiogram.types import Message

from checkbox451_bot import auth, kbd
from checkbox451_bot.bot import Bot
from checkbox451_bot.handlers import helpers


def init(dispatcher):
    @dispatcher.message_handler(content_types=["contact"])
    @helpers.error_handler
    async def contact(message: Message):
        if message.contact is not None:
            if user := auth.sign_in(message.contact):
                if user.roles:
                    return await message.answer(
                        f"Ролі: {user.roles}",
                        reply_markup=kbd.remove,
                    )

                await message.answer(
                    "Адміністратор має підтвердити",
                    reply_markup=kbd.remove,
                )
                await helpers.broadcast(
                    message.chat.id,
                    auth.ADMIN,
                    Bot().send_message,
                    f"new user: {user}",
                )
