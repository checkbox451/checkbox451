from logging import getLogger
from typing import TYPE_CHECKING

from aiogram.types import Contact
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    create_engine,
    false,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy_utils import PhoneNumberType

if TYPE_CHECKING:
    pass

log = getLogger(__name__)

Base = declarative_base()

association_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.user_id")),
    Column("role_name", String, ForeignKey("roles.name")),
)


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    phone_number = Column(PhoneNumberType(region="UA"))
    first_name = Column(String(255))
    last_name = Column(String(255))
    roles = relationship(
        "Role",
        secondary=association_table,
        back_populates="users",
    )

    full_name = Contact.full_name

    def __str__(self):
        return (
            f"{self.user_id}: {self.phone_number.e164} "
            f"({self.full_name}) {self.roles}"
        )


class Role(Base):
    __tablename__ = "roles"

    name = Column(String(10), primary_key=True)
    users = relationship(
        "User",
        secondary=association_table,
        back_populates="roles",
    )

    def __repr__(self):
        return self.name


class Transaction(Base):
    __tablename__ = "transactions"

    type = Column(String(16), primary_key=True)
    id = Column(String(20), primary_key=True)
    ts = Column(DateTime)
    notify = Column(Boolean, server_default=false())
    receipt = Column(Boolean, server_default=false())
    income = Column(Boolean, server_default=false())


def init():
    engine = create_engine(f"sqlite:///checkbox451_bot.db")
    Base.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine))


Session = init()
