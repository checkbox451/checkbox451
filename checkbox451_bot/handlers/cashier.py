from logging import getLogger

from aiogram.types import CallbackQuery, Message

from checkbox451_bot import auth, bot, kbd, pos
from checkbox451_bot.checkbox_api import receipt, shift
from checkbox451_bot.checkbox_api.helpers import aiohttp_session
from checkbox451_bot.handlers import helpers
from checkbox451_bot.shift_close import shift_close

log = getLogger(__name__)


def init(dispatcher):
    @dispatcher.message_handler(commands=["start"])
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    async def start(message: Message):
        await helpers.start(message.chat.id)

    @dispatcher.message_handler(regexp=helpers.goods_pattern)
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    @aiohttp_session
    async def sell(message: Message, *, session):
        await bot.obj.send_chat_action(message.chat.id, "upload_document")

        if (goods := helpers.text_to_goods(message.text)) is None:
            log.error("parse error: %s", message.text)
            raise ValueError("Не вдалося розібрати повідомлення")

        receipt_id = await receipt.sell(goods, session=session)

        try:
            receipt_url = await receipt.wait_receipt_sign(
                receipt_id,
                session=session,
            )
            receipt_qr, receipt_text = await receipt.get_receipt_extra(
                receipt_id,
                session=session,
            )
        except Exception as e:
            await message.answer("Чек успішно створено")
            raise e

        await helpers.send_receipt(
            message.chat.id,
            receipt_id,
            receipt_qr,
            receipt_url,
            receipt_text,
        )

        await start(message)

        await helpers.broadcast(
            message.chat.id,
            auth.SUPERVISOR,
            helpers.send_receipt,
            receipt_id,
            receipt_qr,
            receipt_url,
            receipt_text,
        )

    @dispatcher.callback_query_handler(
        lambda c: c.data and c.data.startswith("print:")
    )
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    async def print_receipt(callback_query: CallbackQuery):
        _, receipt_id = callback_query.data.split(":")

        log.info("print: %s", receipt_id)
        await pos.print_receipt(callback_query.message.text)
        return await callback_query.answer("Друкую…")

    start_btn = (
        btn if isinstance(btn := kbd.start.keyboard[0][0], str) else btn.text
    )

    @dispatcher.message_handler(lambda m: m.text == start_btn)
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    async def create(message: Message):
        await message.answer("Оберіть позицію", reply_markup=kbd.goods)

    @dispatcher.message_handler(commands=["shift"])
    @auth.require(auth.CASHIER)
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
                await message.answer(
                    "Зміну закрито"
                    + (f"\nДохід {income:.02f} грн" if income else "")
                )
