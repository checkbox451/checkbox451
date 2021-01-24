from aiogram.types import Message

from checkbox451_bot import auth, checkbox_api, db, kbd
from checkbox451_bot.handlers import bot, helpers


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
            if (
                auth.has_role(user.user_id, auth.CASHIER)
                and user.user_id != message.chat.id
            ):
                await helpers.start(user.user_id)
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

    @dispatcher.message_handler(commands=["shift"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    async def shift(message: Message):
        if not (arg := message.get_args()):
            shift_balance = await checkbox_api.shift_balance()
            if shift_balance is None:
                await message.answer("Зміна закрита", reply_markup=kbd.remove)
            else:
                await message.answer(
                    f"Баланс: {shift_balance}",
                    reply_markup=kbd.remove,
                )
        elif arg == "close":
            shift_balance = await checkbox_api.shift_close()
            await message.answer(
                f"Зміну закрито. У касі {shift_balance} грн",
                reply_markup=kbd.remove,
            )
