import asyncio
from functools import lru_cache
from json.decoder import JSONDecodeError
from logging import getLogger

from checkbox451_bot.checkbox_api.exceptions import CheckboxReceiptError
from checkbox451_bot.checkbox_api.helpers import (
    aiohttp_session,
    get_retry,
    post,
    require_sign,
)
from checkbox451_bot.checkbox_api.shift import current_shift, open_shift
from checkbox451_bot.config import Config

log = getLogger(__name__)


@aiohttp_session
async def create_receipt(goods, cashless=False, *, session):
    payment = sum(good["price"] * good["quantity"] / 1000 for good in goods)
    data = {
        "goods": [
            {
                "good": good,
                "quantity": good.pop("quantity"),
            }
            for good in goods
        ],
        "payments": [
            {
                "type": "CASHLESS" if cashless else "CASH",
                "value": payment,
            },
        ],
    }

    receipt = await post(
        "/receipts/sell", session=session, exc=CheckboxReceiptError, **data
    )

    receipt_id = receipt["id"]
    log.info("receipt: %s", receipt_id)
    return receipt_id


@aiohttp_session
async def wait_receipt_sign(receipt_id, *, session):
    receipt = receipt_id
    for _ in range(10):
        try:
            receipt = await get_retry(
                f"/receipts/{receipt_id}",
                session=session,
                exc=CheckboxReceiptError,
            )
        except JSONDecodeError:
            pass
        else:
            if receipt["status"] in {"DONE", "SIGNED"}:
                return receipt["tax_url"]

        await asyncio.sleep(1)

    log.error("receipt signing error: %s", receipt)
    raise CheckboxReceiptError("Не вдалось підписати чек")


async def get_receipt_png(receipt_id, *, session):
    png = await get_retry(
        f"/receipts/{receipt_id}/png",
        session=session,
        loader="read",
        exc=CheckboxReceiptError,
    )

    return png


async def get_receipt_qrcode(receipt_id, *, session):
    qrcode = await get_retry(
        f"/receipts/{receipt_id}/qrcode",
        session=session,
        loader="read",
        exc=CheckboxReceiptError,
    )

    return qrcode


async def get_receipt_text(receipt_id, *, session):
    receipt_text = await get_retry(
        f"/receipts/{receipt_id}/text",
        session=session,
        loader="text",
        exc=CheckboxReceiptError,
        **get_receipt_params(),
    )

    return receipt_text


@aiohttp_session
async def get_receipt_extra(receipt_id, *, session):
    if Config().get("receipt_as_image"):
        receipt_image = await get_receipt_png(receipt_id, session=session)
        receipt_text = None
    else:
        receipt_image = await get_receipt_qrcode(receipt_id, session=session)
        receipt_text = await get_receipt_text(receipt_id, session=session)

    return receipt_image, receipt_text


@aiohttp_session
@require_sign
async def sell(goods, cashless=False, *, session):
    if any(good["price"] <= 0 for good in goods):
        raise ValueError("Невірна ціна")
    if any(good["quantity"] <= 0 for good in goods):
        raise ValueError("Невірна кількість")

    if not await current_shift(session=session):
        await open_shift(session=session)

    receipt_id = await create_receipt(
        goods, cashless=cashless, session=session
    )
    return receipt_id


@aiohttp_session
async def get_receipt_data(receipt_id, *, session):
    receipt_url = await get_retry(
        f"/receipts/{receipt_id}", session=session, exc=CheckboxReceiptError
    )
    receipt_image, receipt_text = await get_receipt_extra(
        receipt_id, session=session
    )

    return receipt_image, receipt_url, receipt_text


@aiohttp_session
async def search_receipt(fiscal_code, *, session):
    results = (
        await get_retry(
            "/receipts/search", session=session, fiscal_code=fiscal_code
        )
    )["results"]

    if results:
        return results[0]["id"]


@lru_cache(maxsize=1)
def get_receipt_params():
    receipt_params = {}
    if print_width := Config().get("print", "width"):
        receipt_params["width"] = print_width

    log.info(f"{receipt_params=}")
    return receipt_params
