import functools
import os

from aiogram.types import Contact, Message

from . import kbd, msg

_roles = {}
_users = {}


ADMIN = "ADMIN"
CASHIER = "CASHIER"
SUPERVISOR = "SUPERVISOR"


def _init():
    for role in (ADMIN, CASHIER, SUPERVISOR):
        _roles[role] = list(filter(None, os.environ.get(role, "").split(",")))


_init()
del _init

print(f"{_roles=}")


def require(handler):
    @functools.wraps(handler)
    async def wrapper(message: Message):
        if message.from_user.id in _users:
            await handler(message)
        else:
            await message.answer(msg.AUTH_REQUIRED, reply_markup=kbd.auth)

    return wrapper


def sign_in(contact: Contact):
    phone = contact.phone_number.lstrip("+")
    user_id = contact.user_id

    if user_roles := [r for r, phones in _roles.items() if phone in phones]:
        _users[user_id] = user_roles

    print(f"{contact=!s}, {user_roles=}")

    return user_roles
