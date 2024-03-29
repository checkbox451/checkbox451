from logging import getLogger

from aiogram.types import CallbackQuery, Message

from checkbox451_bot import auth, pos
from checkbox451_bot.bot import Bot
from checkbox451_bot.checkbox_api import receipt, shift
from checkbox451_bot.checkbox_api.helpers import aiohttp_session
from checkbox451_bot.handlers import helpers
from checkbox451_bot.kbd import kbd
from checkbox451_bot.kbd.buttons import btn_cancel, btn_receipt
from checkbox451_bot.shift_close import shift_close

log = getLogger(__name__)


def init(dispatcher):
    @dispatcher.message_handler(commands=["start"])
    @dispatcher.message_handler(lambda m: m.text == btn_cancel)
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    async def start(message: Message):
        await helpers.start(message.chat.id)

    @dispatcher.message_handler(regexp=helpers.goods_pattern)
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    @aiohttp_session
    async def sell(message: Message, *, session):
        await Bot().send_chat_action(message.chat.id, "upload_document")

        if (goods := helpers.text_to_goods(message.text)) is None:
            log.error("parse error: %s", message.text)
            raise ValueError("Не вдалося розібрати повідомлення")

        receipt_id = await receipt.sell(goods, session=session)

        try:
            receipt_url = await receipt.wait_receipt_sign(
                receipt_id,
                session=session,
            )
            receipt_image, receipt_text = await receipt.get_receipt_extra(
                receipt_id,
                session=session,
            )
        except Exception as e:
            await message.answer(
                "⚠️ Чек успішно створено, але виникла помилка його "
                "завантаження"
            )
            raise e

        await helpers.send_receipt(
            message.chat.id,
            receipt_id,
            receipt_image,
            receipt_url,
            receipt_text,
        )

        await start(message)

        await helpers.broadcast(
            message.chat.id,
            auth.SUPERVISOR,
            helpers.send_receipt,
            receipt_id,
            receipt_image,
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

    @dispatcher.message_handler(lambda m: m.text == btn_receipt)
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    async def create(message: Message):
        await message.answer("👇 Оберіть позицію", reply_markup=kbd.goods())

    @dispatcher.message_handler(commands=["report"])
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    @aiohttp_session
    async def report(message: Message, *, session):
        if (my_shift := await shift.current_shift(session=session)) is None:
            await message.answer("🔒 Зміна закрита")
        else:
            await helpers.send_report(message.answer, my_shift)

    @dispatcher.message_handler(commands=["close"])
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    @aiohttp_session
    async def close(message: Message, *, session):
        my_shift = await shift.current_shift(session=session)
        cash_profit = await shift_close(
            chat_id=message.chat.id,
            session=session,
        )
        if cash_profit is None:
            await message.answer("🙌 Зміну вже закрито")
        else:
            await message.answer("👌 Зміну закрито")
            await helpers.send_report(message.answer, my_shift)
