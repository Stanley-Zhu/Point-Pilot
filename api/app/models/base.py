"""Declarative base shared by every model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, MetaData, Text
from sqlalchemy.orm import DeclarativeBase

# Every constraint gets a predictable name, so later migrations can drop or alter it by name.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # The plan's units rule: points and cents are BIGINT, moments are timestamptz.
    type_annotation_map = {
        int: BigInteger,
        str: Text,
        datetime: DateTime(timezone=True),
    }
