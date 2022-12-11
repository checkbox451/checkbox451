import asyncio
import posixpath
from functools import lru_cache, wraps
from json import JSONDecodeError
from logging import getLogger
from typing import Type

import aiohttp
from aiohttp import ClientResponse, ClientSession, ClientTimeout

import checkbox451_bot
from checkbox451_bot.checkbox_api.auth import sign_in
from checkbox451_bot.checkbox_api.exceptions import (
    CheckboxAPIError,
    CheckboxSignError,
)
from checkbox451_bot.config import Config

log = getLogger(__name__)


def aiohttp_session(func):
    @wraps(func)
    async def wrapper(*args, session=None, **kwargs):
        if session:
            return await func(*args, session=session, **kwargs)

        async with aiohttp.ClientSession() as session:
            return await func(*args, session=session, **kwargs)

    return wrapper


def endpoint(path: str):
    return posixpath.join(api_url(), "api/v1", path.lstrip("/"))


def headers(*, auth=True, lic=False):
    _headers = {
        "X-Client-Name": checkbox451_bot.__appname__,
        "X-Client-Version": checkbox451_bot.__version__,
    }

    if auth:
        _headers["Authorization"] = sign_in()

    if lic:
        _headers["X-License-Key"] = Config().get(
            "checkbox", "license", required=True
        )

    return _headers


async def get_retry(
    path,
    *,
    session: ClientSession,
    loader="json",
    exc=CheckboxAPIError,
    **kwargs,
):
    url = endpoint(path)

    err = exc("Невідома помилка")
    response = None
    for attempt in range(6):
        try:
            async with session.get(
                url,
                headers=headers(),
                params=kwargs,
                timeout=ClientTimeout(total=0.5 * 1.5**attempt),
            ) as response:
                if response.status < 500:
                    return await check_response(
                        response, loader=loader, exc=exc
                    )
        except asyncio.TimeoutError as e:
            err = e
        log.warning("retry attempt: %s (%s)", attempt + 1, path)
        await asyncio.sleep(1)

    if response:
        await raise_on_error(response, exc)

    raise err


async def post(
    path,
    *,
    session: ClientSession,
    lic=False,
    exc=CheckboxAPIError,
    **kwargs,
):
    url = endpoint(path)
    async with session.post(
        url, headers=headers(lic=lic), json=kwargs
    ) as response:
        if response.ok:
            return await response.json()

        await raise_on_error(response, exc)


async def raise_on_error(
    response: ClientResponse, exc: Type[CheckboxAPIError]
):
    response.content.set_exception(None)

    try:
        result = await response.json()
    except Exception as e:
        raise exc(response.reason) from e

    message = result["message"]
    if detail := result.get("detail"):
        message += f": {detail}"

    raise exc(message)


async def check_response(
    response: ClientResponse,
    *,
    loader="json",
    exc: Type[CheckboxAPIError] = CheckboxAPIError,
):
    if response.ok:
        return await getattr(response, loader)()

    await raise_on_error(response, exc)


async def raise_for_status(response: ClientResponse):
    if response.ok:
        return response

    try:
        result = await response.json()
    except Exception:
        message = response.reason
        log.exception(message)
    else:
        message = result["message"]
        detail = result.get("detail")
        message = f"{message}" + f": {detail}" if detail else ""
        log.error(message)

    response.raise_for_status()


async def check_sign(*, session):
    try:
        result = await get_retry(
            "/cashier/check-signature", session=session, exc=CheckboxSignError
        )
    except JSONDecodeError:
        return False

    return result["online"]


def require_sign(func):
    @wraps(func)
    async def wrapper(*args, session, **kwargs):
        if await check_sign(session=session):
            return await func(*args, session=session, **kwargs)
        raise CheckboxSignError("Підпис недоступний")

    return wrapper


@lru_cache(maxsize=1)
def api_url():
    api_url = "https://api.checkbox.ua/"
    api_url = Config().get("checkbox", "api_url", default=api_url)

    log.info(f"{api_url=}")
    return api_url
