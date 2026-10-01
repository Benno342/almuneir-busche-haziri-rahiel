from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest

from padel.domain.entities import (
    ACTIVE_BOOKING_STATUSES,
    CLUB_TIMEZONE,
    PAYMENT_WINDOW,
    Booking,
    BookingStatus,
    MembershipTier,
    TimeSlot,
)


def make_slot(day: date = date(2026, 10, 5), start: time = time(18, 0)) -> TimeSlot:
    return TimeSlot(id=1, court_id=1, date=day, start_time=start, end_time=time(19, 30))


def make_booking(status: BookingStatus, created_at: datetime) -> Booking:
    return Booking(
        id=1,
        time_slot_id=1,
        booked_by_member_id=1,
        status=status,
        total_price=Decimal("60.00"),
        created_at=created_at,
    )


def test_membership_tiers() -> None:
    assert {t.value for t in MembershipTier} == {"STANDARD", "PREMIUM"}


def test_time_slot_starts_at_is_timezone_aware_in_club_timezone() -> None:
    slot = make_slot()
    assert slot.starts_at == datetime(2026, 10, 5, 18, 0, tzinfo=CLUB_TIMEZONE)
    assert slot.starts_at.utcoffset() == timedelta(hours=2)  # CEST


def test_time_slot_duration() -> None:
    assert make_slot().duration == timedelta(minutes=90)


def test_time_slot_end_must_be_after_start() -> None:
    with pytest.raises(ValueError):
        TimeSlot(id=None, court_id=1, date=date(2026, 10, 5), start_time=time(18), end_time=time(18))


@pytest.mark.parametrize(
    ("status", "active"),
    [
        (BookingStatus.PENDING_PAYMENT, True),
        (BookingStatus.CONFIRMED, True),
        (BookingStatus.CANCELLED, False),
        (BookingStatus.EXPIRED, False),
    ],
)
def test_booking_is_active(status: BookingStatus, active: bool) -> None:
    booking = make_booking(status, datetime(2026, 10, 1, 8, tzinfo=UTC))
    assert booking.is_active is active
    assert (status in ACTIVE_BOOKING_STATUSES) is active


def test_payment_deadline_is_twelve_hours_after_creation() -> None:
    created = datetime(2026, 10, 1, 8, tzinfo=UTC)
    booking = make_booking(BookingStatus.PENDING_PAYMENT, created)
    assert PAYMENT_WINDOW == timedelta(hours=12)
    assert booking.payment_deadline(make_slot()) == created + timedelta(hours=12)


def test_payment_deadline_is_capped_at_slot_start() -> None:
    slot = make_slot(day=date(2026, 10, 1), start=time(12, 0))  # 10:00 UTC
    booking = make_booking(BookingStatus.PENDING_PAYMENT, datetime(2026, 10, 1, 8, tzinfo=UTC))
    assert booking.payment_deadline(slot) == slot.starts_at
