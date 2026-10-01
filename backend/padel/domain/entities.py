"""Domain entities as plain dataclasses.

This module must stay free of framework imports (no SQLAlchemy, FastAPI, Pydantic).
Only the standard library is allowed here.

Conventions:
- `id` is `None` until the entity has been persisted by a repository.
- All `datetime` values are timezone-aware. TimeSlot.date/start_time/end_time are
  wall-clock times of the club (CLUB_TIMEZONE); use `TimeSlot.starts_at` to compare
  them with `Clock.now()`.
- Money is always `Decimal` with two decimal places (CHF).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

CLUB_TIMEZONE = ZoneInfo("Europe/Zurich")

# A booking that is not fully paid within this window expires (see split-payment spec).
PAYMENT_WINDOW = timedelta(hours=12)

# A member may hold at most this many active bookings for upcoming slots.
MAX_ACTIVE_BOOKINGS_PER_MEMBER = 2

MAX_PARTICIPANTS_PER_BOOKING = 4


class MembershipTier(StrEnum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"


class BookingStatus(StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


# Statuses that block a time slot (mirrored by the partial unique index, see ADR 001).
ACTIVE_BOOKING_STATUSES = frozenset({BookingStatus.PENDING_PAYMENT, BookingStatus.CONFIRMED})


@dataclass
class Member:
    id: int | None
    name: str
    email: str
    membership_tier: MembershipTier
    joined_at: datetime


@dataclass
class Court:
    id: int | None
    name: str
    indoor: bool


@dataclass
class TimeSlot:
    id: int | None
    court_id: int
    date: date
    start_time: time
    end_time: time

    def __post_init__(self) -> None:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")

    @property
    def starts_at(self) -> datetime:
        return datetime.combine(self.date, self.start_time, tzinfo=CLUB_TIMEZONE)

    @property
    def ends_at(self) -> datetime:
        return datetime.combine(self.date, self.end_time, tzinfo=CLUB_TIMEZONE)

    @property
    def duration(self) -> timedelta:
        return self.ends_at - self.starts_at


@dataclass
class Booking:
    id: int | None
    time_slot_id: int
    booked_by_member_id: int
    status: BookingStatus
    total_price: Decimal
    created_at: datetime
    confirmed_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_BOOKING_STATUSES

    def payment_deadline(self, time_slot: TimeSlot) -> datetime:
        """Latest moment at which the booking must be fully paid.

        12h after creation, but never later than the start of the slot: a booking made
        shortly before the game must not stay PENDING_PAYMENT until after it was played.
        """
        return min(self.created_at + PAYMENT_WINDOW, time_slot.starts_at)


@dataclass
class Participant:
    id: int | None
    booking_id: int
    member_id: int
    share_amount: Decimal
    paid: bool = False
    paid_at: datetime | None = None


@dataclass
class WaitlistEntry:
    """A member waiting for a slot.

    Entries are never deleted on promotion: `notified_at` is set instead, so the
    history stays traceable. Only entries with `notified_at is None` are still waiting.
    """

    id: int | None
    time_slot_id: int
    member_id: int
    position: int
    created_at: datetime
    notified_at: datetime | None = None

    @property
    def is_waiting(self) -> bool:
        return self.notified_at is None
