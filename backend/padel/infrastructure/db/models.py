"""SQLAlchemy ORM models (persistence only, no business logic).

Mapping to/from the domain dataclasses happens in repositories.py. Schema changes
always need an Alembic migration (padel/infrastructure/db/migrations).
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Dialect,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

# Deterministic constraint names, so migrations are identical on SQLite and PostgreSQL.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Partial unique index predicate, see docs/adr/001-double-booking.md.
ACTIVE_BOOKING_PREDICATE = "status IN ('PENDING_PAYMENT', 'CONFIRMED')"
ACTIVE_BOOKING_INDEX = "uq_bookings_active_time_slot"

CENT = Decimal("0.01")


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware timestamps on every backend.

    PostgreSQL stores `timestamptz` and returns aware datetimes. SQLite has no
    timezone support and returns naive values, so we store UTC and re-attach UTC
    on read. Naive datetimes are rejected to catch missing Clock usage early.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime given; use timezone-aware datetimes (Clock)")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Money(TypeDecorator[Decimal]):
    """CHF amount with two decimals. SQLite stores NUMERIC as float, so we re-quantize."""

    impl = Numeric(10, 2)
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Any:
        return None if value is None else value.quantize(CENT)

    def process_result_value(self, value: Any, dialect: Dialect) -> Decimal | None:
        return None if value is None else Decimal(str(value)).quantize(CENT)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class MemberModel(Base):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint("membership_tier IN ('STANDARD', 'PREMIUM')", name="membership_tier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    membership_tier: Mapped[str] = mapped_column(String(20))
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime())


class CourtModel(Base):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    indoor: Mapped[bool]


class TimeSlotModel(Base):
    __tablename__ = "time_slots"
    __table_args__ = (
        UniqueConstraint("court_id", "date", "start_time"),
        CheckConstraint("end_time > start_time", name="end_after_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"))
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)


class BookingModel(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING_PAYMENT', 'CONFIRMED', 'CANCELLED', 'EXPIRED')", name="status"
        ),
        # Second line of defence against double bookings (ADR 001).
        Index(
            ACTIVE_BOOKING_INDEX,
            "time_slot_id",
            unique=True,
            postgresql_where=text(ACTIVE_BOOKING_PREDICATE),
            sqlite_where=text(ACTIVE_BOOKING_PREDICATE),
        ),
        Index("ix_bookings_booked_by_member_id_status", "booked_by_member_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"))
    booked_by_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    status: Mapped[str] = mapped_column(String(20))
    total_price: Mapped[Decimal] = mapped_column(Money())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class ParticipantModel(Base):
    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("booking_id", "member_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    share_amount: Mapped[Decimal] = mapped_column(Money())
    paid: Mapped[bool] = mapped_column(default=False)
    paid_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class WaitlistEntryModel(Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (UniqueConstraint("time_slot_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"))
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"))
    position: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    notified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
