import asyncio
import logging
import re
from datetime import date, timedelta
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import dateutil.parser
from aiohttp import ClientSession
from pydantic import root_validator

from checkbox451_bot import __product__
from checkbox451_bot.bot import Bot
from checkbox451_bot.config import Config
from checkbox451_bot.gsheet.common import (
    Logger,
    TransactionBase,
    TransactionProcessorBase,
)

log = logging.getLogger(__name__)

URL = "https://acp.privatbank.ua/api/statements/transactions"
sender_pat = re.compile(
    r"^.+(?:,\s*|Переказ(?:и:)?\s+вiд\s+|Вiд\s+)(\S+\s+\S+(?:\s+\S+)?)\s*$"
)


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


class Privat24Transaction(TransactionBase):
    id_key = "TECHNICAL_TRANSACTION_ID"

    aut_my_acc: str
    trantype: TranType

    @root_validator(pre=True)
    def keys(cls, values):
        return {k.lower(): v for k, v in values.items()}

    @root_validator(pre=True)
    def values(cls, values):
        if match := sender_pat.match(values["osnd"]):
            values["sender"] = match.group(1)

        values["ts"] = dateutil.parser.parse(
            values["date_time_dat_od_tim_p"], dayfirst=True
        )

        name = Config().get("privat24", "good_name_default")
        sum_e = values["sum_e"]

        values["name"] = name
        values["sum"] = sum_e
        values["code"] = f"{name} {sum_e}"

        return values

    def check_receipt(self):
        return self.trantype == TranType.CREDIT and (
            not accounts() or self.aut_my_acc in accounts()
        )


class Privat24TransactionProcessor(TransactionProcessorBase):
    transactions_file = Path("transactions-privat24.json")
    transaction_cls = Privat24Transaction

    def __init__(self, *, logger: Any = log, polling_interval=15):
        polling_interval = Config().get(
            "privat24", "polling_interval", default=polling_interval
        )
        super().__init__(logger=logger, polling_interval=polling_interval)

        self.api_id = Config().get("privat24", "api", "id")
        self.api_token = Config().get("privat24", "api", "token")

    def pre_run_hook(self):
        old_file = Path("transactions.json")
        if old_file.exists() and not self.transactions_file.exists():
            old_file.rename(self.transactions_file)

        if not self.api_id or not self.api_token:
            log.warning("missing privat24 api credentials; ignoring...")
            return False

        privat24_polling_interval = self.polling_interval
        self.logger.info(f"{privat24_polling_interval=}")

        return True

    async def get_transactions(self) -> List[Dict[str, Any]]:
        transactions = []

        exist_next_page = True
        next_page_id = ""
        start_date = date.today() - timedelta(days=7)
        while exist_next_page:
            async with ClientSession() as session:
                async with session.get(
                    URL,
                    headers={
                        "id": self.api_id,
                        "token": self.api_token,
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


async def main():
    async with Bot().session_close():
        await Privat24TransactionProcessor(logger=Logger).run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
