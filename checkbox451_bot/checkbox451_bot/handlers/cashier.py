import re
from logging import getLogger

from aiogram.types import CallbackQuery, Message

from checkbox451_bot import auth, checkbox_api, goods, kbd, msg
from checkbox451_bot.handlers import bot, helpers

log = getLogger(__name__)


def init(dispatcher):
    @dispatcher.message_handler(commands=["start"])
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    async def start(message: Message):
        await helpers.start(message)

    @dispatcher.message_handler(lambda m: m.text in goods.items)
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    async def sell(message: Message):
        await bot.send_chat_action(message.chat.id, "typing")

        good = goods.items[message.text]

        receipt_id = await checkbox_api.sell(good)

        try:
            receipt_url = await checkbox_api.wait_receipt_sign(receipt_id)
            receipt_qr, receipt_text = await checkbox_api.get_receipt_extra(
                receipt_id
            )
        except Exception as e:
            await message.answer(
                "Чек успішно створено",
                reply_markup=kbd.remove,
            )
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
        await callback_query.answer(msg.PRINTING)

    @dispatcher.message_handler(regexp=re.escape(msg.CREATE_RECEIPT))
    @auth.require(auth.CASHIER)
    @helpers.error_handler
    async def create(message: Message):
        await message.answer(msg.SELECT_GOOD, reply_markup=kbd.goods)
