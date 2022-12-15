import asyncio
import functools
import re
from io import BytesIO
from logging import getLogger
from typing import Union

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.exceptions import RetryAfter

from checkbox451_bot import auth, db
from checkbox451_bot.bot import Bot
from checkbox451_bot.kbd import kbd

log = getLogger(__name__)


async def start(user_id):
    await Bot().send_message(user_id, "👋 Вітаю!", reply_markup=kbd.start)


async def broadcast(user_id, role_name, send_message, *args, **kwargs):
    session = db.Session()
    role = session.query(db.Role).get(role_name)

    async def send(user):
        if user.user_id != user_id:
            for _ in range(10):
                try:
                    await send_message(user.user_id, *args, **kwargs)
                except RetryAfter as err:
                    log.exception(err)
                    await asyncio.sleep(err.timeout)
                else:
                    break

    await asyncio.gather(*[send(user) for user in role.users])


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

    await Bot().send_photo(user_id, BytesIO(receipt_qr), caption=receipt_url)
    await Bot().send_message(
        user_id,
        f"<pre>{receipt_text}</pre>",
        reply_markup=keyboard,
    )


async def error(user_id, exception):
    await Bot().send_message(
        user_id,
        f"<b>Помилка:</b> <code>{exception}</code>",
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


goods_pattern = re.compile(
    r"^\s*(.+?)\s+(\d+(?:[.,]\d{0,2})?)\s+грн"
    r"(?:\s+(\d+(?:[.,]\d{0,3})?))?\s*$",
    flags=re.MULTILINE,
)


def text_to_goods(text):
    if len(text.splitlines()) != len(items := goods_pattern.findall(text)):
        return

    goods = [
        {
            "name": (name := item[0]),
            "price": (price := int(float(item[1].replace(",", ".")) * 100)),
            "quantity": int(float(item[2].replace(",", ".") or 1) * 1000),
            "code": f"{name} {price / 100:.02f}",
        }
        for item in items
    ]

    return goods


def prepare_report(sales, returns, header, header_no_returns):
    sales /= 100
    returns /= 100
    proceeds = sales - returns

    if sales:
        if returns:
            return (
                f"{header}:\n<pre>"
                f"Одержано: {sales:>10.2f} грн\n"
                f"Повернуто:{returns:>10.2f} грн\n"
                f"Виручка:  {proceeds:>10.2f} грн"
                "</pre>"
            )
        return f"{header_no_returns}: {proceeds:.2f} грн"


async def send_report(answer, shift):
    cash_sales = shift["balance"]["cash_sales"]
    card_sales = shift["balance"]["card_sales"]
    cash_returns = shift["balance"]["cash_returns"]
    card_returns = shift["balance"]["card_returns"]

    if cash_report := prepare_report(
        cash_sales, cash_returns, "💵 Готівка", "💵 Готівкова виручка"
    ):
        await answer(cash_report)

    if card_report := prepare_report(
        card_sales, card_returns, "💳 Картка", "💳 Карткова виручка"
    ):
        await answer(card_report)

    if cash_report and card_report:
        total = cash_sales - cash_returns + card_sales - card_returns
        await answer(f"💰 Всього: {total / 100:.2f} грн")
