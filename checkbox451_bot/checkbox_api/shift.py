import asyncio
from json.decoder import JSONDecodeError

from checkbox451_bot.checkbox_api.auth import sign_out
from checkbox451_bot.checkbox_api.exceptions import (
    CheckboxReceiptError,
    CheckboxShiftError,
)
from checkbox451_bot.checkbox_api.helpers import (
    aiohttp_session,
    get_retry,
    log,
    post,
    require_sign,
)


@aiohttp_session
async def current_shift(*, session):
    result = await get_retry(
        "/cashier/shift", session=session, exc=CheckboxShiftError
    )

    return result


@aiohttp_session
async def open_shift(*, session):
    opened_shift = await post(
        "/shifts", session=session, lic=True, exc=CheckboxShiftError
    )

    shift = opened_shift
    for _ in range(60):
        try:
            shift = await get_retry(
                "/cashier/shift", session=session, exc=CheckboxShiftError
            )
        except JSONDecodeError:
            pass
        else:
            if shift and shift["status"] == "OPENED":
                shift_id = shift["id"]
                log.info("shift: %s", shift_id)
                return shift_id

        await asyncio.sleep(1)

    if shift is None:
        log.warning("shift is missing: %s", opened_shift)

    log.error("shift error: %s", shift)
    raise CheckboxShiftError("Не вдалось підписати зміну")


@aiohttp_session
async def service_out(*, session):
    shift = await current_shift(session=session)

    if not shift:
        raise CheckboxShiftError("Зміна закрита")

    balance = shift["balance"]["balance"]
    if balance <= 0:
        return None

    payment = {
        "type": "CASH",
        "value": -balance,
        "label": "Готівка",
    }

    receipt = await post(
        "/receipts/service",
        session=session,
        exc=CheckboxReceiptError,
        payment=payment,
    )

    receipt_id = receipt["id"]
    log.info("service out: %s", receipt_id)

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
            if receipt["status"] == "DONE":
                return receipt_id

        await asyncio.sleep(1)

    log.error("service out signing error: %s", receipt)
    raise CheckboxReceiptError("Не вдалось підписати службову видачу")


@aiohttp_session
@require_sign
async def shift_close(*, session):
    await service_out(session=session)

    shift = await post(
        "/shifts/close", session=session, exc=CheckboxShiftError
    )

    shift_id = shift["id"]
    balance = shift["balance"]["service_out"] / 100

    for _ in range(60):
        try:
            shift = await get_retry(
                "/cashier/shift", session=session, exc=CheckboxShiftError
            )
        except JSONDecodeError:
            pass
        else:
            if shift is None:
                log.info("shift closed: %s", shift_id)
                sign_out()
                return balance

        await asyncio.sleep(1)

    log.error("shift close error: %s", shift)
    raise CheckboxShiftError("Не вдалось підписати закриття зміни")
