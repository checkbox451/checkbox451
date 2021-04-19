from aiogram.types import Message

from checkbox451_bot import auth, bot, db, kbd
from checkbox451_bot.checkbox_api import receipt, shift
from checkbox451_bot.checkbox_api.helpers import aiohttp_session
from checkbox451_bot.handlers import helpers
from checkbox451_bot.shift_close import shift_close


def init(dispatcher):
    @dispatcher.message_handler(commands=["users"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    async def users(message: Message):
        session = db.Session()
        users_repr = [str(u) for u in session.query(db.User)]
        text = "\n".join(users_repr)
        await message.answer(text)

    @dispatcher.message_handler(commands=["sign"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    async def sign(message: Message):
        if arg := message.get_args():
            mode = auth.SignMode.mode(arg)
            auth.SignMode.set(mode)
        else:
            mode = auth.SignMode.get()
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
            await bot.obj.send_message(
                user.user_id,
                "Бувай!",
                reply_markup=kbd.remove,
            )
        else:
            raise ValueError(f"no user: {user_id}")

    @dispatcher.message_handler(commands=["receipt"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    @aiohttp_session
    async def receipt_(message: Message, *, session):
        args = message.get_args().split()
        if len(args) > 0:
            if not (
                receipt_id := await receipt.search_receipt(
                    args[0],
                    session=session,
                )
            ):
                return
        else:
            return
        if len(args) == 2:
            recipient = args[1]
            if recipient.startswith("+"):
                session = db.Session()
                if (
                    user := session.query(db.User)
                    .filter(db.User.phone_number == recipient)
                    .scalar()
                ) :
                    user_id = user.user_id
                else:
                    return
            elif recipient.isnumeric():
                user_id = int(recipient)
            else:
                return
        else:
            user_id = message.chat.id

        receipt_data = await receipt.get_receipt_data(
            receipt_id,
            session=session,
        )
        receipt_qr, receipt_url, receipt_text = receipt_data
        await helpers.send_receipt(
            user_id,
            receipt_id,
            receipt_qr,
            receipt_url,
            receipt_text,
        )

    @dispatcher.message_handler(commands=["shift"])
    @auth.require(auth.ADMIN)
    @helpers.error_handler
    @aiohttp_session
    async def shift_(message: Message, *, session):
        if not (arg := message.get_args()):
            shift_balance = await shift.shift_balance(session=session)
            if shift_balance is None:
                await message.answer("Зміна закрита")
            else:
                await message.answer(f"Баланс: {shift_balance:.02f} грн")
        elif arg == "close":
            income = await shift_close(
                chat_id=message.chat.id,
                session=session,
            )
            if income is None:
                await message.answer("Зміну вже закрито")
            else:
                await message.answer(f"Зміну закрито. Дохід {income:.02f} грн")
