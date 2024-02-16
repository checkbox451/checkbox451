import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from operator import itemgetter
from pathlib import Path
from typing import Any, Dict, List

import dateutil.parser
from pydantic import BaseModel
from sqlalchemy import update

from checkbox451_bot import auth, checkbox_api, goods
from checkbox451_bot.bot import Bot
from checkbox451_bot.checkbox_api.helpers import aiohttp_session
from checkbox451_bot.config import Config
from checkbox451_bot.db import Session, Transaction
from checkbox451_bot.gsheet import gsheet
from checkbox451_bot.handlers import helpers


class TransactionBase(BaseModel):
    id_key: str
    _orig: dict
    _id: str
    _type: str
    _db: Transaction = None

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
        self._id = str(self._orig[self.id_key])
        self._type = type(self).__name__.removesuffix("Transaction").lower()

    def __lt__(self, other: "TransactionBase"):
        return self.ts < other.ts

    def check_receipt(self):
        return True

    def check_income(self):
        return self.check_receipt()

    @property
    def orig(self):
        return self._orig

    def row(self):
        return [str(self.ts.date()), self.sum, self.sender]

    @property
    def id(self):
        return self._id

    @property
    def type(self):
        return self._type

    @property
    def db(self):
        return self._db

    def set_db(self, db):
        self._db = db


class TransactionProcessorBase(ABC):
    transactions_file: Path
    transaction_cls: TransactionBase

    def __init__(self, *, logger: Any, polling_interval=15):
        self.logger = logger
        self.polling_interval = polling_interval

    @abstractmethod
    async def get_transactions(self) -> List[Dict[str, Any]]:
        pass

    def write_transactions(self, transactions):
        with self.transactions_file.open("w") as w:
            json.dump(transactions, w)

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
    @aiohttp_session
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
    def parse_transaction(cls, curr, *, session):
        transactions = []
        for t in (cls.transaction_cls.parse_obj(c) for c in curr):
            if not (t_db := session.query(Transaction).get((t.type, t.id))):
                t_db = Transaction(type=t.type, id=t.id, ts=t.ts)
                session.add(t_db)
                session.commit()
            t.set_db(t_db)
            transactions.append(t)

        return sorted(transactions)

    @staticmethod
    def update_db(transaction, *, session, **kwargs):
        session.execute(
            update(Transaction).where(
                Transaction.type == transaction.type,
                Transaction.id == transaction.id,
            ),
            kwargs,
        )
        session.commit()

    async def process_transactions(self):
        try:
            current = await self.get_transactions()
        except Exception as err:
            self.logger.exception(err)
            return []

        self.write_transactions(current)

        with Session() as session:
            if transactions := self.parse_transaction(
                current, session=session
            ):
                for tr in transactions:
                    if tr.check_receipt() and not tr.db.receipt:
                        self.logger.info(tr.orig)

                        try:
                            await self.bot_notify(tr)
                        except Exception as err:
                            self.logger.exception(err)

                        try:
                            await self.create_receipt(tr)
                        except Exception as err:
                            self.logger.exception(err)
                        else:
                            self.update_db(tr, receipt=True, session=session)

                    if tr.check_income() and not tr.db.income:
                        try:
                            await self.store_transaction(tr)
                        except Exception as err:
                            self.logger.exception(err)
                        else:
                            self.update_db(tr, income=True, session=session)

            else:
                self.logger.debug("no new transactions")

    def pre_run_hook(self):
        return True

    async def run(self):
        if not self.pre_run_hook():
            return

        shift_close_time = Config().get("checkbox", "shift_close_time")

        def shift_check():
            if shift_close_time:
                return dateutil.parser.parse(shift_close_time) > datetime.now()
            return True

        while True:
            if shift_check():
                try:
                    await self.process_transactions()
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
