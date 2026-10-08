from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
import uuid
from typing import Any

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

_CENTS = Decimal("0.01")


class GUID(TypeDecorator[uuid.UUID]):
    """UUID stored as a portable 36-char string.

    SQLite has no native UUID type: SQLAlchemy's generic ``UUID`` emits a
    literal UUID column that SQLite reflects back as NUMERIC (unknown type →
    NUMERIC affinity), which makes alembic autogenerate see phantom type
    changes. A plain VARCHAR(36) reflects exactly.
    """

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> uuid.UUID | None:
        if value is None:
            return None
        return uuid.UUID(value)


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetimes on top of SQLite's naive storage.

    SQLite has no timezone support: values are serialized as naive UTC
    strings. This decorator normalizes on the way in and re-attaches UTC on
    the way out, so application code can keep comparing aware datetimes
    (``datetime.now(timezone.utc)``) without TypeError.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Money(TypeDecorator[Decimal]):
    """Exact money stored as integer cents.

    SQLite has no fixed-precision NUMERIC: a plain ``Numeric(12, 2)`` column
    round-trips through floats. Storing cents as integers keeps SUM(),
    comparisons and equality exact, and the result processor keeps the ORM
    surface as ``Decimal`` so existing schemas/services are unchanged.
    """

    impl = BigInteger
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> int | None:
        if value is None:
            return None
        amount = Decimal(str(value)).quantize(_CENTS, rounding=ROUND_HALF_UP)
        return int(amount * 100)

    def process_result_value(
        self, value: int | None, dialect: Dialect
    ) -> Decimal | None:
        if value is None:
            return None
        return (Decimal(value) / 100).quantize(_CENTS)
