import asyncio
from json.decoder import JSONDecodeError

import aiohttp
from aiohttp import ClientResponseError

from checkbox451_bot.checkbox_api.helpers import (
    CheckboxReceiptError,
    get,
    get_retry,
    log,
    post,
    raise_for_status,
    receipt_params,
)
from checkbox451_bot.checkbox_api.shift import current_shift, open_shift


async def create_receipt(session, good):
    receipt = {
        "goods": [
            {
                "good": good,
                "quantity": 1000,
            },
        ],
        "payments": [
            {
                "value": good["price"],
            },
        ],
    }

    async with post(session, "/receipts/sell", **receipt) as response:
        try:
            await raise_for_status(response)
        except ClientResponseError:
            raise CheckboxReceiptError("Не вдалось створити чек")

        receipt = await response.json()

    receipt_id = receipt["id"]
    log.info("receipt: %s", receipt_id)
    return receipt_id


async def wait_receipt_sign(receipt_id):
    async with aiohttp.ClientSession() as session:
        for _ in range(10):
            async with get(session, f"/receipts/{receipt_id}") as response:
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


async def get_receipt_qrcode(session, receipt_id):
    async with get_retry(
        session,
        f"/receipts/{receipt_id}/qrcode",
    ) as response:
        await raise_for_status(response)
        qrcode = await response.read()

    return qrcode


async def get_receipt_text(session, receipt_id):
    async with get_retry(
        session,
        f"/receipts/{receipt_id}/text",
        **receipt_params,
    ) as response:
        await raise_for_status(response)
        receipt_text = await response.text()

    return receipt_text


async def get_receipt_extra(receipt_id):
    async with aiohttp.ClientSession() as session:
        receipt_qr = await get_receipt_qrcode(session, receipt_id)
        receipt_text = await get_receipt_text(session, receipt_id)

    return receipt_qr, receipt_text


async def sell(good):
    if good["price"] <= 0:
        raise ValueError("Невірна ціна")

    async with aiohttp.ClientSession() as session:
        if not await current_shift(session):
            await open_shift(session)

        receipt_id = await create_receipt(session, good)
        return receipt_id


async def get_receipt_data(receipt_id):
    async with aiohttp.ClientSession() as session:
        async with get(session, f"/receipts/{receipt_id}") as response:
            receipt_url = (await response.json())["tax_url"]
        receipt_qr = await get_receipt_qrcode(session, receipt_id)
        receipt_text = await get_receipt_text(session, receipt_id)

    return receipt_qr, receipt_url, receipt_text


async def search_receipt(fiscal_code):
    async with aiohttp.ClientSession() as session:
        async with get(
            session,
            "/receipts/search",
            fiscal_code=fiscal_code,
        ) as response:
            await raise_for_status(response)
            results = (await response.json())["results"]

    if results:
        return results[0]["id"]
