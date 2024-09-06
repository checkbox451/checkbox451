import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

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


@lru_cache(maxsize=1)
def accounts():
    return [acc for acc in Config().get("mono", "accounts", default=())]


class MonoAPI:
    BASE_URL = "https://api.monobank.ua/personal"

    def __init__(self, token: str):
        self.token = token
        self._session: ClientSession | None = None

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": __product__, "X-Token": self.token}

    async def __aenter__(self):
        self._session = ClientSession(headers=self._headers())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()

        self._session = None

    @staticmethod
    def _dt2ts(dt: datetime) -> int:
        return int(dt.timestamp())

    async def _get(self, path, params=None):
        params = params or {}

        stack = AsyncExitStack()

        if not self._session:
            await stack.enter_async_context(self)

        url = self.BASE_URL + path.format(**params)
        async with stack, self._session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def client_info(self):
        return await self._get("/client-info")

    async def account_ids(self) -> dict[str, str]:
        client_info = await self.client_info()
        return {
            account["iban"]: account["id"]
            for account in client_info["accounts"]
        }

    async def statements(
        self, account_id: str, from_dt: datetime = None, to_dt: datetime = None
    ):
        if from_dt is None:
            from_dt = datetime.now() - timedelta(days=7)

        if to_dt is None:
            to_dt = datetime.now()

        return await self._get(
            "/statement/{account}/{from}/{to}",
            {
                "account": account_id,
                "from": self._dt2ts(from_dt),
                "to": self._dt2ts(to_dt),
            },
        )


class MonoTransaction(TransactionBase):
    _id_key = "id"

    @root_validator(pre=True)
    def values(cls, values):
        values["ts"] = datetime.fromtimestamp(values["time"])
        values["sender"] = values.get("counterName", "")

        name = Config().get("mono", "good_name_default")
        amount = f'{values["amount"] / 100:.2f}'

        values["name"] = name
        values["sum"] = amount
        values["code"] = f"{name} {amount}"

        return values

    def check(self):
        return float(self.sum) > 0

    def check_receipt(self):
        return super().check_receipt() and Config().get(
            "mono", "receipt", default=False
        )


class MonoTransactionProcessor(TransactionProcessorBase):
    transaction_cls = MonoTransaction

    def __init__(self, *, logger: Any = log, polling_interval=15):
        polling_interval = Config().get(
            "mono", "polling_interval", default=polling_interval
        )
        super().__init__(logger=logger, polling_interval=polling_interval)

        self.api_token = Config().get("mono", "api", "token")

    def pre_run_hook(self):
        super().pre_run_hook()

        if not self.api_token:
            log.warning("missing mono api token; ignoring...")
            return False

        mono_polling_interval = self.polling_interval
        self.logger.info(f"{mono_polling_interval=}")

        return True

    async def get_transactions(self) -> list[dict[str, Any]]:
        transactions = []

        async with MonoAPI(self.api_token) as api:
            mono_accounts = await api.account_ids()
            for account in accounts():
                if account_id := mono_accounts.get(account):
                    statements = await api.statements(account_id)
                    transactions += statements

        return transactions


async def main():
    async with Bot().session_close():
        await MonoTransactionProcessor(logger=Logger).run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
