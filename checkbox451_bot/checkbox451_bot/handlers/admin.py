from aiogram.types import Message

from checkbox451_bot import auth, checkbox_api, db, kbd
from checkbox451_bot.handlers import bot, helpers
from checkbox451_bot.handlers.helpers import start


def init(dispatcher):
    @dispatcher.message_handler(commands=["users"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    async def users(message: Message):
        session = db.Session()
        users_repr = [str(u) for u in session.query(db.User)]
        text = "\n".join(users_repr)
        await message.answer(text, reply_markup=kbd.remove)

    @dispatcher.message_handler(commands=["sign"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    async def sign(message: Message):
        mode = auth.SignMode.mode(message.get_args())
        auth.SignMode.set(mode)
        await message.answer(f"{message.get_command()} {mode.value}")

    @dispatcher.message_handler(commands=["role"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    async def role(message: Message):
        user_id, role_name = message.get_args().split()
        session = db.Session()
        if user := session.query(db.User).get(user_id):
            auth.add_role(user, role_name, session=session)
            await message.answer(str(user))
            if user.user_id != message.chat.id:
                await start(user.user_id)
        else:
            raise ValueError(f"no user: {user_id}")

    @dispatcher.message_handler(commands=["delete"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    async def delete(message: Message):
        user_id = message.get_args()
        session = db.Session()
        if user := session.query(db.User).get(user_id):
            session.delete(user)
            session.commit()
            await message.answer(f"deleted: {user_id}")
            await bot.send_message(
                user.user_id,
                "Бувай!",
                reply_markup=kbd.remove,
            )
        else:
            raise ValueError(f"no user: {user_id}")

    @dispatcher.message_handler(commands=["receipt"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    async def receipt(message: Message):
        receipt_id = message.get_args()
        receipt_data = await checkbox_api.get_receipt_data(receipt_id)
        receipt_qr, receipt_url, receipt_text = receipt_data
        await helpers.send_receipt(
            message.chat.id,
            receipt_id,
            receipt_qr,
            receipt_url,
            receipt_text,
        )
