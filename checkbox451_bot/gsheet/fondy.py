import asyncio
import hashlib
import logging
from datetime import date, datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

import dateutil.parser
from aiohttp import ClientConnectorError, ClientSession
from aiohttp_retry import ExponentialRetry, RetryClient
from asyncache import cached
from cachetools import TTLCache
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


class FondyAPI:
    def __init__(self, company_id, private_key):
        self._company_id = str(company_id)
        self._private_key = private_key

    @staticmethod
    def _date():
        return str(datetime.now())

    @staticmethod
    def _headers(d: Dict[str, str] = None):
        d = d or {}
        return {
            "Content-Type": "application/json; charset=utf8",
            "User-Agent": __product__,
            **d,
        }

    def _signature(self, sig_date):
        sig = "|".join([self._private_key, self._company_id, sig_date])
        return hashlib.sha512(sig.encode()).hexdigest()

    @cached(TTLCache(1, 3600))
    async def token(self, *, client: RetryClient):
        url = "https://wallet.fondy.eu/authorizer/token/application/get"
        headers = self._headers()

        sig_date = self._date()
        data = dict(
            application_id=self._company_id,
            date=sig_date,
            signature=self._signature(sig_date),
        )

        async with client.post(url, headers=headers, json=data) as r:
            r.raise_for_status()
            response = await r.json()

        return response["token"]

    async def report(self, merchant_id, *, client: RetryClient):
        url = "https://portal.fondy.eu/api/extend/company/report/"

        token = await self.token(client=client)
        headers = self._headers({"Authorization": f"Token {token}"})

        start_date = date.today() - timedelta(days=7)
        start_time = datetime.combine(start_date, time.min)

        result = []

        on_page = 500
        page = 0
        rows_count = 1

        while rows_count > on_page * page:
            page += 1
            data = dict(
                on_page=on_page,
                page=page,
                filters=[
                    {
                        "s": "order_timestart",
                        "m": "from",
                        "v": str(start_time),
                    }
                ],
                merchant_id=merchant_id,
                report_id=745,
            )

            async with client.post(url, headers=headers, json=data) as r:
                r.raise_for_status()
                response = await r.json(content_type=None)

            keys = response["fields"]
            values_list = response["data"]
            result += [
                {k: v for k, v in zip(keys, values)} for values in values_list
            ]
            rows_count = response["rows_count"]

        return result


class OrderStatus(str, Enum):
    APPROVED = "approved"
    _ = "(ignored)"

    @classmethod
    def _missing_(cls, _):
        return cls._


class FondyTransaction(TransactionBase):
    id_key = "payment_id"

    order_status: OrderStatus

    @root_validator(pre=True)
    def values(cls, values):
        values["ts"] = dateutil.parser.parse(values["order_timestart"])
        values["code"] = values["name"] = values["order_id"]
        values["sum"] = values["actual_amount"]
        values["sender"] = values["sender_email"] or ""
        return values

    def check_receipt(self):
        return self.order_status == OrderStatus.APPROVED


class FondyTransactionProcessor(TransactionProcessorBase):
    transactions_file = Path("transactions-fondy.json")
    transaction_cls = FondyTransaction
    api: FondyAPI

    def __init__(self, *, logger: Any = log, polling_interval=15):
        polling_interval = Config().get(
            "fondy", "polling_interval", default=polling_interval
        )
        super().__init__(logger=logger, polling_interval=polling_interval)

        self.company_id = Config().get("fondy", "auth", "id")
        self.secret_key = Config().get("fondy", "auth", "secret_key")
        self.merchant_id = Config().get("fondy", "merchant_id")

    def pre_run_hook(self):
        super().pre_run_hook()

        if not self.company_id or not self.secret_key:
            log.warning("missing fondy auth credentials; ignoring...")
            return False
        elif not self.merchant_id:
            log.warning("missing fondy merchant id; ignoring...")
            return False

        self.api = FondyAPI(self.company_id, self.secret_key)

        fondy_polling_interval = self.polling_interval
        self.logger.info(f"{fondy_polling_interval=}")

        return True

    async def get_transactions(self) -> List[Dict[str, Any]]:
        retry_options = ExponentialRetry(exceptions={ClientConnectorError})
        async with ClientSession() as session:
            retry_client = RetryClient(session, retry_options=retry_options)
            return await self.api.report(self.merchant_id, client=retry_client)


async def main():
    async with Bot().session_close():
        await FondyTransactionProcessor(logger=Logger).run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
