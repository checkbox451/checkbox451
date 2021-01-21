import functools
import os
from logging import getLogger

from aiogram.types import Contact, Message
from sqlalchemy.orm import Session
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


def require(role_name):
    def decorator(handler):
        @functools.wraps(handler)
        async def wrapper(message: Message):
            if has_role(message.chat.id, role_name):
                return await handler(message)

            await message.answer(msg.AUTH_REQUIRED, reply_markup=kbd.auth)

        return wrapper

    return decorator


def add_user(contact: Contact, *, session: Session):
    if user := session.query(db.User).get(contact.user_id):
        pass
    else:
        user = db.User(**contact.values)
        session.add(user)
        session.commit()
        log.info("new user: %s", contact)

    return user


def get_role(role_name: str, *, session: Session):
    if role := session.query(db.Role).get(role_name):
        pass
    else:
        role = db.Role(name=role_name)
        session.add(role)

    return role


def add_role(user: db.User, role_name: str, *, session: Session = None):
    assert role_name in (
        ADMIN,
        CASHIER,
        SUPERVISOR,
    ), f"Unknown role: {role_name}"

    session = session or db.Session()
    role = get_role(role_name, session=session)

    user.roles.append(role)
    log.info("%s is %s now", user.user_id, role.name)

    session.commit()


def sign_in(contact: Contact):
    session = db.Session()

    if sign_mode or not get_role(ADMIN, session=session).users:
        user = add_user(contact, session=session)

        if user.phone_number in _admins:
            add_role(user, ADMIN, session=session)

        return user.roles


def has_role(user_id, role_name):
    session = db.Session()
    user = (
        session.query(db.User)
        .filter(db.User.user_id == user_id, db.User.roles.any(name=role_name))
        .one_or_none()
    )

    return user
