import asyncio
import json
import logging
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiohttp
import dateutil.parser
from pydantic import BaseModel, root_validator, validator

from checkbox451_bot import __product__, auth, gsheet
from checkbox451_bot.handlers import bot, helpers

URL = "https://acp.privatbank.ua/api/statements/transactions/interim"
sender_pat = re.compile(r"^.+,\s*(\S+\s+\S+\s+\S+)\s*$")

accounts = [
    acc for acc in os.environ.get("PRIVAT24_ACCOUNTS", "").split(",") if acc
]

privat24_api_id = os.environ["PRIVAT24_API_ID"]
privat24_api_token = os.environ["PRIVAT24_API_TOKEN"]
privat24_polling_interval = int(
    os.environ.get("PRIVAT24_POLLING_INTERVAL") or 15
)

transactions_file = Path(os.environ.get("DB_DIR", ".")) / "transactions.json"
worksheet_title = os.environ.get("GOOGLE_WORKSHEET_TITLE_CASHLESS")

log = logging.getLogger(__name__)


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
            values["sender"] = match.group(1).title()
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
    transactions = []

    exist_next_page = True
    next_page_id = ""
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
    await gsheet.append_row(row, worksheet_title)


async def bot_nofify(transaction):
    await helpers.broadcast(
        None,
        auth.SUPERVISOR,
        bot.obj.send_message,
        f"Безготівкове зарахування: {transaction.sum_e} грн"
        + (f"\nПлатник: {transaction.sender}" if transaction.sender else ""),
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
        for transaction in transactions:
            if transaction.trantype == TranType.CREDIT and (
                not accounts or transaction.aut_my_acc in accounts
            ):
                logger.info(transaction.orig)

                try:
                    await store_transaction(transaction)
                except Exception as err:
                    logger.exception(err)
                    return prev

                write_transactions(curr)

                try:
                    await bot_nofify(transaction)
                except Exception as err:
                    logger.exception(err)
    else:
        logger.debug("no new transactions")

    return curr


async def run(logger: Any = log):
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
    async with bot.session_close():
        await run(logger=Logger)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
