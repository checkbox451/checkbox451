import asyncio
import json
import logging
import re
from datetime import date, datetime, timedelta
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

import aiohttp
import dateutil.parser
from pydantic import BaseModel, root_validator, validator

from checkbox451_bot import __product__, auth, checkbox_api, gsheet
from checkbox451_bot.bot import Bot
from checkbox451_bot.checkbox_api.helpers import aiohttp_session
from checkbox451_bot.config import Config
from checkbox451_bot.handlers import helpers

log = logging.getLogger(__name__)

URL = "https://acp.privatbank.ua/api/statements/transactions"
sender_pat = re.compile(
    r"^.+(?:,\s*|Переказ\s+вiд\s+|Вiд\s+)(\S+\s+\S+(?:\s+\S+)?)\s*$"
)
transactions_file = Path("transactions.json")


@lru_cache(maxsize=1)
def accounts():
    return [
        acc for acc in Config().get("privat24", "accounts", default=()) if acc
    ]


class TranType(str, Enum):
    CREDIT = "C"
    _ = "(ignored)"

    @classmethod
    def _missing_(cls, _):
        return TranType._


class Transaction(BaseModel):
    _orig: dict = None
    aut_my_acc: str
    dat_od: str
    date_time_dat_od_tim_p: datetime
    sender: str = ""
    sum_e: str
    trantype: TranType

    class Config:
        underscore_attrs_are_private = True

    def __init__(self, **data):
        super().__init__(**data)
        self._orig = data

    @property
    def orig(self):
        return self._orig

    @root_validator(pre=True)
    def keys_lower(cls, values):
        return {k.lower(): v for k, v in values.items()}

    @root_validator(pre=True)
    def validate_sender(cls, values):
        if match := sender_pat.match(values["osnd"]):
            values["sender"] = match.group(1)
        return values

    @validator("dat_od", pre=True)
    def validate_dat_od(cls, value):
        return str(dateutil.parser.parse(value, dayfirst=True).date())

    @validator("date_time_dat_od_tim_p", pre=True)
    def validate_date_time_dat_od_tim_p(cls, value):
        return dateutil.parser.parse(value, dayfirst=True)

    def __lt__(self, other: "Transaction"):
        return self.date_time_dat_od_tim_p < other.date_time_dat_od_tim_p


async def get_transactions():
    privat24_api_id = Config().get("privat24", "api", "id")
    privat24_api_token = Config().get("privat24", "api", "token")

    transactions = []

    exist_next_page = True
    next_page_id = ""
    start_date = date.today() - timedelta(days=7)
    async with aiohttp.ClientSession() as session:
        while exist_next_page:
            async with session.get(
                URL,
                headers={
                    "id": privat24_api_id,
                    "token": privat24_api_token,
                    "User-Agent": __product__,
                    "Content-Type": "application/json; charset=utf8",
                },
                params={
                    "startDate": start_date.strftime("%d-%m-%Y"),
                    "followId": next_page_id,
                },
            ) as response:
                response.raise_for_status()
                result = await response.json()

            transactions += result["transactions"]

            if exist_next_page := result["exist_next_page"]:
                next_page_id = result["next_page_id"]

    return transactions


def write_transactions(transactions):
    with transactions_file.open("w") as w:
        json.dump(transactions, w)


async def read_transactions(logger):
    if not transactions_file.exists():
        try:
            transaction = await get_transactions()
        except Exception as err:
            logger.exception(err)
            return []

        write_transactions(transaction)
        return transaction

    with transactions_file.open() as r:
        return json.load(r)


async def store_transaction(transaction: Transaction):
    row = [transaction.dat_od, transaction.sum_e, transaction.sender]
    worksheet_title = Config().get("google", "worksheet", "title_cashless")
    await gsheet.append_row(row, worksheet_title)


async def bot_nofify(transaction):
    await helpers.broadcast(
        None,
        auth.SUPERVISOR,
        Bot().send_message,
        f"Безготівкове зарахування: {transaction.sum_e} грн"
        + (f"\nПлатник: {transaction.sender}" if transaction.sender else ""),
    )


def transaction_to_goods(transaction):
    if name := Config().get("privat24", "good_name_default"):
        return [
            {
                "code": f"{name} {transaction.sum_e}",
                "name": name,
                "price": float(transaction.sum_e) * 100,
                "quantity": 1000,
            }
        ]


@aiohttp_session
async def create_receipt(transaction, *, session):
    if goods := transaction_to_goods(transaction):
        try:
            receipt_id = await checkbox_api.receipt.sell(
                goods, cashless=True, session=session
            )
        except Exception as e:
            await helpers.broadcast(
                None,
                auth.SUPERVISOR,
                Bot().send_message,
                "Помилка створення чеку!",
            )
            raise e
    else:
        return

    try:
        receipt_url = await checkbox_api.receipt.wait_receipt_sign(
            receipt_id,
            session=session,
        )
        (
            receipt_qr,
            receipt_text,
        ) = await checkbox_api.receipt.get_receipt_extra(
            receipt_id,
            session=session,
        )
    except Exception as e:
        await helpers.broadcast(
            None, auth.SUPERVISOR, Bot().send_message, "Чек успішно створено"
        )
        raise e

    await helpers.broadcast(
        None,
        auth.SUPERVISOR,
        helpers.send_receipt,
        receipt_id,
        receipt_qr,
        receipt_url,
        receipt_text,
    )


def new_transaction(prev, curr):
    prev_set = {frozenset(t.items()) for t in prev}
    curr_set = {frozenset(t.items()) for t in curr}

    return sorted(Transaction.parse_obj(i) for i in curr_set - prev_set)


async def process_transactions(prev, logger):
    try:
        curr = await get_transactions()
    except Exception as err:
        logger.error(err)
        return prev

    if transactions := new_transaction(prev, curr):
        temp = prev[:]

        for transaction in transactions:
            if transaction.trantype == TranType.CREDIT and (
                not accounts() or transaction.aut_my_acc in accounts()
            ):
                logger.info(transaction.orig)

                try:
                    await store_transaction(transaction)
                except Exception as err:
                    logger.exception(err)
                    write_transactions(temp)
                    return temp

                temp.append(transaction.orig)

                try:
                    await bot_nofify(transaction)
                except Exception as err:
                    logger.exception(err)

                try:
                    await create_receipt(transaction)
                except Exception as err:
                    logger.exception(err)
            else:
                temp.append(transaction.orig)
    else:
        logger.debug("no new transactions")

    write_transactions(curr)
    return curr


async def run(logger: Any = log):
    privat24_api_id = Config().get("privat24", "api", "id")
    privat24_api_token = Config().get("privat24", "api", "token")
    privat24_polling_interval = Config().get(
        "privat24", "polling_interval", default=15
    )

    if not privat24_api_id or not privat24_api_token:
        log.warning("missing privat24 api credentials; ignoring...")
        return

    logger.info(f"{privat24_polling_interval=}")

    prev = await read_transactions(logger)

    while True:
        try:
            prev = await process_transactions(prev, logger)
        except Exception as err:
            logger.exception(err)
        await asyncio.sleep(60 * privat24_polling_interval)


class Logger:
    @staticmethod
    def log_msg(msg):
        if isinstance(msg, Exception):
            msg = repr(msg)
        now = datetime.now().replace(microsecond=0)
        print(f"{now}: {msg}")

    debug = error = exception = info = log_msg


async def main():
    async with Bot().session_close():
        await run(logger=Logger)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
