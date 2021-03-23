import asyncio
import os
from json.decoder import JSONDecodeError
from logging import getLogger

from aiohttp import ClientResponseError

from checkbox451_bot.checkbox_api.exceptions import CheckboxReceiptError
from checkbox451_bot.checkbox_api.helpers import (
    aiohttp_session,
    get,
    get_retry,
    post,
    raise_for_status,
    require_sign,
)
from checkbox451_bot.checkbox_api.shift import current_shift, open_shift

log = getLogger(__name__)

receipt_params = {}


@aiohttp_session
async def create_receipt(goods, *, session):
    payment = sum(good["price"] * good["quantity"] / 1000 for good in goods)
    receipt = {
        "goods": [
            {
                "good": good,
                "quantity": good.pop("quantity"),
            }
            for good in goods
        ],
        "payments": [
            {
                "value": payment,
            },
        ],
    }

    async with post("/receipts/sell", session=session, **receipt) as response:
        try:
            await raise_for_status(response)
        except ClientResponseError:
            raise CheckboxReceiptError("Не вдалось створити чек")

        receipt = await response.json()

    receipt_id = receipt["id"]
    log.info("receipt: %s", receipt_id)
    return receipt_id


@aiohttp_session
async def wait_receipt_sign(receipt_id, *, session):
    for _ in range(10):
        async with get_retry(
            f"/receipts/{receipt_id}",
            session=session,
        ) as response:
            try:
                receipt = await response.json()
            except JSONDecodeError:
                pass
            else:
                if receipt["status"] == "DONE":
                    return receipt["tax_url"]

        await asyncio.sleep(1)

    log.error("receipt signing error: %s", receipt)
    raise CheckboxReceiptError("Не вдалось підписати чек")


async def get_receipt_qrcode(receipt_id, *, session):
    async with get_retry(
        f"/receipts/{receipt_id}/qrcode",
        session=session,
    ) as response:
        await raise_for_status(response)
        qrcode = await response.read()

    return qrcode


async def get_receipt_text(receipt_id, *, session):
    async with get_retry(
        f"/receipts/{receipt_id}/text",
        session=session,
        **receipt_params,
    ) as response:
        await raise_for_status(response)
        receipt_text = await response.text()

    return receipt_text


@aiohttp_session
async def get_receipt_extra(receipt_id, *, session):
    receipt_qr = await get_receipt_qrcode(receipt_id, session=session)
    receipt_text = await get_receipt_text(receipt_id, session=session)

    return receipt_qr, receipt_text


@aiohttp_session
@require_sign
async def sell(goods, *, session):
    if any(good["price"] <= 0 for good in goods):
        raise ValueError("Невірна ціна")
    if any(good["quantity"] <= 0 for good in goods):
        raise ValueError("Невірна кількість")

    if not await current_shift(session=session):
        await open_shift(session=session)

    receipt_id = await create_receipt(goods, session=session)
    return receipt_id


@aiohttp_session
async def get_receipt_data(receipt_id, *, session):
    async with get(f"/receipts/{receipt_id}", session=session) as response:
        receipt_url = (await response.json())["tax_url"]
    receipt_qr = await get_receipt_qrcode(receipt_id, session=session)
    receipt_text = await get_receipt_text(receipt_id, session=session)

    return receipt_qr, receipt_url, receipt_text


@aiohttp_session
async def search_receipt(fiscal_code, *, session):
    async with get(
        "/receipts/search",
        session=session,
        fiscal_code=fiscal_code,
    ) as response:
        await raise_for_status(response)
        results = (await response.json())["results"]

    if results:
        return results[0]["id"]


def init():
    print_width = os.environ.get("PRINT_WIDTH")

    if print_width and print_width.isnumeric():
        receipt_params["width"] = int(print_width)

    log.info(f"{receipt_params=}")


init()
