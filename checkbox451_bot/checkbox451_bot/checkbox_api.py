import asyncio
import os
from json import JSONDecodeError
from logging import getLogger

import aiohttp
import requests
from aiohttp import ClientResponse, ContentTypeError

log = getLogger(__name__)

debug = bool(os.environ.get("DEBUG"))
api_url = "https://{}api.checkbox.in.ua/".format("dev-" if debug else "")
api_url = os.environ.get("API_URL", api_url)
log.info(f"{api_url=}")


class CheckboxAPIException(Exception):
    pass


def endpoint(path: str):
    return os.path.join(api_url, "api/v1", path.lstrip("/"))


def _auth():
    login = os.environ["LOGIN"]
    password = os.environ["PASSWORD"]

    url = endpoint("/cashier/signin")
    r = requests.post(url, json=dict(login=login, password=password))
    r.raise_for_status()
    data = r.json()

    return f"{data['token_type']} {data['access_token']}"


_headers = {
    "X-Client-Name": "checkbox451",
    "X-Client-Version": "0.1",
    "Authorization": _auth(),
}
del _auth
_headers_license = {
    "X-License-Key": os.environ["LICENSE_KEY"],
    **_headers,
}


def get(session, path, **kwargs):
    url = endpoint(path)
    return session.get(url, headers=_headers, params=kwargs)


def post(session, path, lic=False, **kwargs):
    headers = _headers_license if lic else _headers
    url = endpoint(path)
    return session.post(url, headers=headers, json=kwargs)


def goods():
    url = endpoint("/goods")
    r = requests.get(url, headers=_headers)
    r.raise_for_status()
    j = r.json()
    return j["results"]


async def raise_for_status(response: ClientResponse):
    if response.status < 400:
        return response

    try:
        result = await response.json()
        message = result["message"]
        if detail := result.get("detail"):
            message = f"{message}: {detail}"
    except (ContentTypeError, JSONDecodeError, KeyError) as e:
        log.exception("Failed to parse the result")
        message = await response.text()

    log.error(message)
    raise CheckboxAPIException(message)


async def current_shift(session):
    async with get(session, "/cashier/shift") as response:
        await raise_for_status(response)
        result = await response.json()

    return result


async def new_shift(session):
    async with post(session, "/shifts", lic=True) as response:
        await raise_for_status(response)
        result = await response.json()

    return result


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
        await raise_for_status(response)
        receipt = await response.json()

    receipt_id = receipt["id"]
    for _ in range(10):
        async with get(session, f"/receipts/{receipt_id}") as response:
            try:
                receipt = await response.json()
            except JSONDecodeError:
                pass
            else:
                if receipt.get("status") == "DONE":
                    return receipt_id

        await asyncio.sleep(1)

    raise CheckboxAPIException("Невдалося створити чек")


async def get_receipt_text(session, receipt_id):
    async with get(session, f"/receipts/{receipt_id}/text", width=32) as resp:
        await raise_for_status(resp)
        receipt_text = await resp.text()

    return receipt_text


async def sell(good):
    async with aiohttp.ClientSession() as session:
        if not await current_shift(session):
            await new_shift(session)

        receipt_id = await create_receipt(session, good)
        receipt_text = await get_receipt_text(session, receipt_id)

        return receipt_id, receipt_text
