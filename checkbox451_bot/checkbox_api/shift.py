import asyncio
from json.decoder import JSONDecodeError

from aiohttp import ClientResponseError

from checkbox451_bot.checkbox_api.exceptions import (
    CheckboxReceiptError,
    CheckboxShiftError,
)
from checkbox451_bot.checkbox_api.helpers import (
    aiohttp_session,
    get,
    get_retry,
    log,
    post,
    raise_for_status,
    require_sign,
)


@aiohttp_session
async def current_shift(*, session):
    async with get("/cashier/shift", session=session) as response:
        await raise_for_status(response)
        result = await response.json()

    return result


@aiohttp_session
async def open_shift(*, session):
    async with post("/shifts", session=session, lic=True) as response:
        try:
            await raise_for_status(response)
        except ClientResponseError:
            raise CheckboxShiftError("Не вдалось відкрити зміну")
        shift = await response.json()

    shift_id = shift["id"]

    for _ in range(10):
        async with get("/cashier/shift", session=session) as response:
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


@aiohttp_session
async def service_out(*, session):
    shift = await current_shift(session=session)

    if not shift:
        raise CheckboxShiftError("Зміна закрита")

    balance = shift["balance"]["balance"]
    if balance <= 0:
        return

    payment = {
        "type": "CASH",
        "value": -balance,
        "label": "Готівка",
    }

    async with post(
        "/receipts/service",
        session=session,
        payment=payment,
    ) as response:
        try:
            await raise_for_status(response)
        except ClientResponseError:
            raise CheckboxReceiptError("Не вдалось здійснити службову видачу")

        receipt = await response.json()

    receipt_id = receipt["id"]
    log.info("service out: %s", receipt_id)

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
                    return receipt_id

        await asyncio.sleep(1)

    log.error("service out signing error: %s", receipt)
    raise CheckboxReceiptError("Не вдалось підписати службову видачу")


@aiohttp_session
async def shift_balance(*, session):
    shift = await current_shift(session=session)

    if shift:
        return shift["balance"]["balance"] / 100


@aiohttp_session
@require_sign
async def shift_close(*, session):
    await service_out(session=session)

    async with post("/shifts/close", session=session) as response:
        await raise_for_status(response)
        shift = await response.json()

    shift_id = shift["id"]
    balance = shift["balance"]["service_out"] / 100

    for _ in range(60):
        async with get("/cashier/shift", session=session) as response:
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
