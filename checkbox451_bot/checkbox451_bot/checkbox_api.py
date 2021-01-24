import asyncio
import os
from contextlib import asynccontextmanager
from json import JSONDecodeError
from logging import getLogger

import aiohttp
import cachetools.func
import requests
from aiohttp import ClientResponse, ClientResponseError, ClientTimeout

log = getLogger(__name__)

debug = bool(os.environ.get("DEBUG"))
api_url = "https://{}api.checkbox.in.ua/".format("dev-" if debug else "")
api_url = os.environ.get("API_URL", api_url)
log.info(f"{api_url=}")


class CheckboxAPIError(Exception):
    pass


class CheckboxReceiptError(CheckboxAPIError):
    pass


class CheckboxShiftError(CheckboxAPIError):
    pass


def endpoint(path: str):
    return os.path.join(api_url, "api/v1", path.lstrip("/"))


@cachetools.func.ttl_cache(ttl=86400)
def _auth():
    login = os.environ["LOGIN"]
    password = os.environ["PASSWORD"]

    url = endpoint("/cashier/signin")
    r = requests.post(url, json=dict(login=login, password=password))
    r.raise_for_status()
    data = r.json()

    return f"{data['token_type']} {data['access_token']}"


def _headers(lic=False):
    headers = {
        "X-Client-Name": "checkbox451",
        "X-Client-Version": "0.1",
        "Authorization": _auth(),
    }

    if lic:
        headers["X-License-Key"] = os.environ["LICENSE_KEY"]

    return headers


@asynccontextmanager
async def get(session, path, **kwargs):
    url = endpoint(path)

    err = None
    for attempt in range(6):
        try:
            async with session.get(
                url,
                headers=_headers(),
                params=kwargs,
                timeout=ClientTimeout(total=0.5 * 1.5 ** attempt),
            ) as response:
                yield response
        except Exception as e:
            err = e
            log.warning("retry attempt: %s", attempt + 1)
            continue
        else:
            return

    raise err


def post(session, path, lic=False, **kwargs):
    url = endpoint(path)
    return session.post(url, headers=_headers(lic), json=kwargs)


def goods():
    url = endpoint("/goods")
    r = requests.get(url, headers=_headers())
    r.raise_for_status()
    j = r.json()
    return j["results"]


async def raise_for_status(response: ClientResponse):
    if response.ok:
        return response

    try:
        result = await response.json()
        message = result["message"]
        detail = result["detail"]
        message = f"{message}: {detail}"
    except Exception:
        message = await response.text() or response.reason
        log.exception(message)
    else:
        log.error(message)

    response.raise_for_status()


async def current_shift(session):
    async with get(session, "/cashier/shift") as response:
        await raise_for_status(response)
        result = await response.json()

    return result


async def open_shift(session):
    async with post(session, "/shifts", lic=True) as response:
        try:
            await raise_for_status(response)
        except ClientResponseError:
            raise CheckboxShiftError("Не вдалось відкрити зміну")
        shift = await response.json()

    shift_id = shift["id"]

    for _ in range(10):
        async with get(session, "/cashier/shift") as response:
            try:
                shift = await response.json()
            except JSONDecodeError:
                pass
            else:
                if shift["status"] == "OPENED":
                    log.info("shift: %s", shift_id)
                    return shift_id

        await asyncio.sleep(1)

    log.error("shift error: %s", shift)
    raise CheckboxShiftError("Не вдалось підписати зміну")


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
    raise CheckboxReceiptError("Не вдалося підписати чек")


async def get_receipt_qrcode(session, receipt_id):
    async with get(session, f"/receipts/{receipt_id}/qrcode") as response:
        await raise_for_status(response)
        qrcode = await response.read()

    return qrcode


async def get_receipt_text(session, receipt_id):
    async with get(session, f"/receipts/{receipt_id}/text", width=32) as resp:
        await raise_for_status(resp)
        receipt_text = await resp.text()

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


async def shift_balance():
    async with aiohttp.ClientSession() as session:
        shift = await current_shift(session)

    if shift:
        return shift["balance"]["balance"] / 100


async def shift_close():
    async with aiohttp.ClientSession() as session:
        async with post(session, "/shifts/close") as response:
            await raise_for_status(response)
            shift = await response.json()

        shift_id = shift["id"]
        balance = shift["balance"]["balance"] / 100

        for _ in range(10):
            async with get(session, "/cashier/shift") as response:
                try:
                    shift = await response.json()
                except JSONDecodeError:
                    pass
                else:
                    if shift is None:
                        log.info("shift closed: %s", shift_id)
                        return balance

            await asyncio.sleep(1)

    log.error("shift close error: %s", shift)
    raise CheckboxShiftError("Не вдалось підписати закриття зміни")
