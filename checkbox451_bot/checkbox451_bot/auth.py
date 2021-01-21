import functools
import os
from logging import getLogger

from aiogram.types import Contact, Message
from sqlalchemy_utils import PhoneNumber

from . import db, kbd, msg

log = getLogger(__name__)

ADMIN = "ADMIN"
CASHIER = "CASHIER"
SUPERVISOR = "SUPERVISOR"

_admins = [
    PhoneNumber(phone_number, region="UA")
    for phone_number in os.environ.get(ADMIN, "").split(",")
    if phone_number
]
sign_mode = False


def require(handler):
    @functools.wraps(handler)
    async def wrapper(message: Message):
        session = db.Session()

        if session.query(db.User).get(message.chat.id):
            return await handler(message)

        await message.answer(msg.AUTH_REQUIRED, reply_markup=kbd.auth)

    return wrapper


def add_role(user: db.User, role_name: str):
    assert role_name in (
        ADMIN,
        CASHIER,
        SUPERVISOR,
    ), f"Unknown role: {role_name}"

    session = db.Session()
    role = session.query(db.Role).get(ADMIN) or db.Role(name=role_name)
    user.roles.append(role)
    log.info("%s is %s now", user.user_id, role.name)

    session.commit()


def sign_in(contact: Contact):
    session = db.Session()

    user = db.User(**contact.values)
    session.add(user)
    session.commit()

    if user.phone_number in _admins:
        add_role(user, ADMIN)

    return user.roles


def has_role(user_id, role_name):
    session = db.Session()
    user = (
        session.query(db.User)
        .filter(db.User.user_id == user_id, db.User.roles.any(name=role_name))
        .one_or_none()
    )

    return user
