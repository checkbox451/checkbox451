import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from operator import itemgetter
from pathlib import Path
from typing import Any, Dict, List

import dateutil.parser
from pydantic import BaseModel

from checkbox451_bot import auth, checkbox_api, goods
from checkbox451_bot.bot import Bot
from checkbox451_bot.checkbox_api.helpers import aiohttp_session
from checkbox451_bot.config import Config
from checkbox451_bot.gsheet import gsheet
from checkbox451_bot.handlers import helpers


class TransactionBase(BaseModel):
    _hash_key: str
    _orig: dict = None

    ts: datetime
    code: str
    name: str
    sender: str = ""
    sum: str

    class Config:
        underscore_attrs_are_private = True

    def __init__(self, **data):
        super().__init__(**data)
        self._orig = data

    def __hash__(self):
        return hash(self._orig[self._hash_key])

    def __lt__(self, other: "TransactionBase"):
        return self.ts < other.ts

    def check(self):
        return True

    @property
    def orig(self):
        return self._orig

    def row(self):
        return [str(self.ts.date()), self.sum, self.sender]


class TransactionProcessorBase(ABC):
    transactions_file: Path
    transaction_cls: TransactionBase

    def __init__(self, *, logger: Any, polling_interval=15):
        self.logger = logger
        self.polling_interval = polling_interval

    @abstractmethod
    async def get_transactions(self, *, session) -> List[Dict[str, Any]]:
        pass

    def write_transactions(self, transactions):
        with self.transactions_file.open("w") as w:
            json.dump(transactions, w)

    async def read_transactions(self, *, session):
        if not self.transactions_file.exists():
            try:
                transaction = await self.get_transactions(session=session)
            except Exception as err:
                self.logger.exception(err)
                return []

            self.write_transactions(transaction)
            return transaction

        with self.transactions_file.open() as r:
            return json.load(r)

    @staticmethod
    async def store_transaction(transaction: TransactionBase):
        row = transaction.row()
        worksheet_title = Config().get("google", "worksheet", "title_cashless")
        await gsheet.append_row(row, worksheet_title)

    @staticmethod
    async def bot_notify(transaction):
        await helpers.broadcast(
            None,
            auth.SUPERVISOR,
            Bot().send_message,
            f"💸 Безготівкове зарахування: {transaction.sum} грн"
            + (
                f"\n💁 Платник: {transaction.sender}"
                if transaction.sender
                else ""
            ),
        )

    @staticmethod
    def transaction_to_goods(transaction: TransactionBase):
        code = transaction.code
        name = transaction.name
        price = float(transaction.sum) * 100
        quantity = 1000

        goods_items = goods.get_items()
        if goods_items:
            for good in reversed(
                sorted(goods_items.values(), key=itemgetter("price"))
            ):
                quotient, reminder = divmod(price, good_price := good["price"])
                if reminder == 0:
                    code = good["code"]
                    name = good["name"]
                    price = good_price
                    quantity *= quotient
                    break

        return [
            {
                "code": code,
                "name": name,
                "price": price,
                "quantity": quantity,
            }
        ]

    @classmethod
    async def create_receipt(cls, transaction, *, session):
        if goods_ := cls.transaction_to_goods(transaction):
            try:
                receipt_id = await checkbox_api.receipt.sell(
                    goods_, cashless=True, session=session
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
                receipt_image,
                receipt_text,
            ) = await checkbox_api.receipt.get_receipt_extra(
                receipt_id,
                session=session,
            )
        except Exception as e:
            await helpers.broadcast(
                None,
                auth.SUPERVISOR,
                Bot().send_message,
                "Чек успішно створено",
            )
            raise e

        await helpers.broadcast(
            None,
            auth.SUPERVISOR,
            helpers.send_receipt,
            receipt_id,
            receipt_image,
            receipt_url,
            receipt_text,
        )

    @classmethod
    def new_transaction(cls, prev, curr):
        prev_set = {cls.transaction_cls.parse_obj(t) for t in prev}
        curr_set = {cls.transaction_cls.parse_obj(t) for t in curr}

        return sorted(curr_set - prev_set)

    async def process_transactions(self, prev, *, session):
        try:
            curr = await self.get_transactions(session=session)
        except Exception as err:
            self.logger.error(err)
            return prev

        if transactions := self.new_transaction(prev, curr):
            temp = prev[:]

            for transaction in transactions:
                if transaction.check():
                    self.logger.info(transaction.orig)

                    try:
                        await self.store_transaction(transaction)
                    except Exception as err:
                        self.logger.exception(err)
                        self.write_transactions(temp)
                        return temp

                    temp.append(transaction.orig)

                    try:
                        await self.bot_notify(transaction)
                    except Exception as err:
                        self.logger.exception(err)

                    try:
                        await self.create_receipt(transaction, session=session)
                    except Exception as err:
                        self.logger.exception(err)
                else:
                    temp.append(transaction.orig)
        else:
            self.logger.debug("no new transactions")

        self.write_transactions(curr)
        return curr

    def pre_run_hook(self):
        return True

    @aiohttp_session
    async def run(self, *, session):
        if not self.pre_run_hook():
            return

        prev = await self.read_transactions(session=session)

        shift_close_time = Config().get("checkbox", "shift_close_time")
        shift_check = (
            lambda: dateutil.parser.parse(shift_close_time) > datetime.now()
            if shift_close_time
            else lambda: True
        )

        while True:
            if shift_check():
                try:
                    prev = await self.process_transactions(
                        prev, session=session
                    )
                except Exception as err:
                    self.logger.exception(err)

            await asyncio.sleep(60 * self.polling_interval)


class Logger:
    @staticmethod
    def log_msg(msg):
        if isinstance(msg, Exception):
            msg = repr(msg)
        now = datetime.now().replace(microsecond=0)
        print(f"{now}: {msg}")

    debug = error = exception = info = log_msg
