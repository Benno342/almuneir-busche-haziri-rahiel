"""Helpers to create persisted test data with sensible defaults.

Work with any Repositories implementation (in-memory or SQL).
"""

from datetime import UTC, date, datetime, time
from decimal import Decimal

from padel.application.repositories import Repositories
from padel.domain.entities import (
    Booking,
    BookingStatus,
    Court,
    Member,
    MembershipTier,
    Participant,
    TimeSlot,
    WaitlistEntry,
)

DEFAULT_NOW = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)  # Thursday, 10:00 in Zurich


def add_member(
    repos: Repositories,
    name: str = "Alex",
    tier: MembershipTier = MembershipTier.STANDARD,
    email: str | None = None,
) -> Member:
    email = email or f"{name.lower()}@example.com"
    return repos.members.add(
        Member(id=None, name=name, email=email, membership_tier=tier, joined_at=DEFAULT_NOW)
    )


def add_court(repos: Repositories, name: str = "Court 1", indoor: bool = True) -> Court:
    return repos.courts.add(Court(id=None, name=name, indoor=indoor))


def add_slot(
    repos: Repositories,
    court: Court | None = None,
    day: date = date(2026, 10, 5),
    start: time = time(18, 0),
    end: time = time(19, 30),
) -> TimeSlot:
    court = court or add_court(repos)
    assert court.id is not None
    return repos.time_slots.add(
        TimeSlot(id=None, court_id=court.id, date=day, start_time=start, end_time=end)
    )


def add_booking(
    repos: Repositories,
    slot: TimeSlot,
    member: Member,
    status: BookingStatus = BookingStatus.PENDING_PAYMENT,
    total_price: Decimal = Decimal("90.00"),
    created_at: datetime = DEFAULT_NOW,
) -> Booking:
    assert slot.id is not None and member.id is not None
    return repos.bookings.add(
        Booking(
            id=None,
            time_slot_id=slot.id,
            booked_by_member_id=member.id,
            status=status,
            total_price=total_price,
            created_at=created_at,
        )
    )


def add_participant(
    repos: Repositories,
    booking: Booking,
    member: Member,
    share_amount: Decimal = Decimal("22.50"),
    paid: bool = False,
) -> Participant:
    assert booking.id is not None and member.id is not None
    return repos.participants.add(
        Participant(
            id=None,
            booking_id=booking.id,
            member_id=member.id,
            share_amount=share_amount,
            paid=paid,
            paid_at=DEFAULT_NOW if paid else None,
        )
    )


def add_waitlist_entry(
    repos: Repositories,
    slot: TimeSlot,
    member: Member,
    position: int | None = None,
    created_at: datetime = DEFAULT_NOW,
) -> WaitlistEntry:
    assert slot.id is not None and member.id is not None
    return repos.waitlist.add(
        WaitlistEntry(
            id=None,
            time_slot_id=slot.id,
            member_id=member.id,
            position=position or repos.waitlist.next_position(slot.id),
            created_at=created_at,
        )
    )
