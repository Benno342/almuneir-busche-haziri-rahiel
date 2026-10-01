"""Contract tests every Repositories implementation must pass.

Run against the in-memory fakes, SQLite and (integration job only) PostgreSQL, so the
fakes used in unit tests are guaranteed to behave like the real database.
"""

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest

from padel.application.repositories import Repositories
from padel.domain.entities import BookingStatus, MembershipTier
from padel.domain.exceptions import SlotUnavailableError
from tests.builders import (
    DEFAULT_NOW,
    add_booking,
    add_court,
    add_member,
    add_participant,
    add_slot,
    add_waitlist_entry,
)
from tests.fakes import in_memory_repositories


@pytest.fixture(params=["memory"])
def repos(request: pytest.FixtureRequest) -> Iterator[Repositories]:
    yield in_memory_repositories()


def test_member_roundtrip(repos: Repositories) -> None:
    member = add_member(repos, "Maria", MembershipTier.PREMIUM)
    assert member.id is not None
    loaded = repos.members.get(member.id)
    assert loaded == member
    assert loaded is not None and loaded.joined_at.tzinfo is not None
    assert repos.members.get(9999) is None
    assert [m.name for m in repos.members.list_all()] == ["Maria"]


def test_court_roundtrip(repos: Repositories) -> None:
    court = add_court(repos, "Center", indoor=False)
    assert court.id is not None
    assert repos.courts.get(court.id) == court
    assert repos.courts.list_all() == [court]


def test_time_slots_by_date_are_ordered(repos: Repositories) -> None:
    court = add_court(repos)
    late = add_slot(repos, court, start=time(20, 0), end=time(21, 30))
    early = add_slot(repos, court, start=time(8, 0), end=time(9, 30))
    add_slot(repos, court, day=date(2026, 10, 6))
    assert repos.time_slots.list_by_date(date(2026, 10, 5)) == [early, late]
    assert early.id is not None and repos.time_slots.get(early.id) == early


def test_time_slot_is_unique_per_court_date_and_start(repos: Repositories) -> None:
    court = add_court(repos)
    add_slot(repos, court)
    with pytest.raises(Exception):  # noqa: B017 - ValueError (fake) / IntegrityError (SQL)
        add_slot(repos, court)


def test_returned_entities_are_detached_copies(repos: Repositories) -> None:
    booking = add_booking(repos, add_slot(repos), add_member(repos))
    booking.status = BookingStatus.CONFIRMED  # no update() call
    assert booking.id is not None
    loaded = repos.bookings.get(booking.id)
    assert loaded is not None and loaded.status == BookingStatus.PENDING_PAYMENT


def test_booking_roundtrip_and_update(repos: Repositories) -> None:
    booking = add_booking(repos, add_slot(repos), add_member(repos), total_price=Decimal("72.00"))
    assert booking.id is not None
    assert repos.bookings.get(booking.id) == booking

    confirmed_at = DEFAULT_NOW + timedelta(hours=1)
    repos.bookings.update(replace(booking, status=BookingStatus.CONFIRMED, confirmed_at=confirmed_at))
    loaded = repos.bookings.get(booking.id)
    assert loaded is not None
    assert loaded.status == BookingStatus.CONFIRMED
    assert loaded.confirmed_at == confirmed_at
    assert loaded.total_price == Decimal("72.00")


def test_timestamps_roundtrip_as_same_instant(repos: Repositories) -> None:
    created = datetime(2026, 10, 1, 23, 30, tzinfo=UTC)
    booking = add_booking(repos, add_slot(repos), add_member(repos), created_at=created)
    assert booking.id is not None
    loaded = repos.bookings.get(booking.id)
    assert loaded is not None and loaded.created_at == created


def test_second_active_booking_for_slot_is_rejected(repos: Repositories) -> None:
    slot = add_slot(repos)
    add_booking(repos, slot, add_member(repos, "A"))
    with pytest.raises(SlotUnavailableError):
        add_booking(repos, slot, add_member(repos, "B"), status=BookingStatus.CONFIRMED)


def test_inactive_bookings_do_not_block_the_slot(repos: Repositories) -> None:
    slot = add_slot(repos)
    member = add_member(repos)
    add_booking(repos, slot, member, status=BookingStatus.CANCELLED)
    add_booking(repos, slot, member, status=BookingStatus.EXPIRED)
    active = add_booking(repos, slot, member)
    assert repos.bookings.get_active_for_slot(slot.id or 0) == active


def test_booking_queries(repos: Repositories) -> None:
    member, other = add_member(repos, "A"), add_member(repos, "B")
    court = add_court(repos)
    s1 = add_slot(repos, court, start=time(8, 0), end=time(9, 0))
    s2 = add_slot(repos, court, start=time(9, 0), end=time(10, 0))
    s3 = add_slot(repos, court, start=time(10, 0), end=time(11, 0))
    pending = add_booking(repos, s1, member)
    confirmed = add_booking(repos, s2, member, status=BookingStatus.CONFIRMED)
    add_booking(repos, s3, member, status=BookingStatus.CANCELLED)
    add_booking(repos, s3, other)

    assert repos.bookings.get_active_for_slot(s1.id or 0) == pending
    assert {b.id for b in repos.bookings.list_active_by_member(member.id or 0)} == {
        pending.id,
        confirmed.id,
    }
    assert len(repos.bookings.list_by_status(BookingStatus.PENDING_PAYMENT)) == 2
    assert repos.bookings.list_by_status(BookingStatus.CONFIRMED) == [confirmed]


def test_participants(repos: Repositories) -> None:
    booker, friend = add_member(repos, "A"), add_member(repos, "B")
    booking = add_booking(repos, add_slot(repos), booker)
    p1 = add_participant(repos, booking, booker, Decimal("45.00"))
    p2 = add_participant(repos, booking, friend, Decimal("45.00"))
    assert repos.participants.list_by_booking(booking.id or 0) == [p1, p2]

    paid_at = DEFAULT_NOW + timedelta(minutes=5)
    repos.participants.update(replace(p2, paid=True, paid_at=paid_at))
    loaded = repos.participants.list_by_booking(booking.id or 0)[1]
    assert loaded.paid is True and loaded.paid_at == paid_at
    assert loaded.share_amount == Decimal("45.00")


def test_waitlist(repos: Repositories) -> None:
    slot = add_slot(repos)
    assert slot.id is not None
    assert repos.waitlist.next_position(slot.id) == 1
    first = add_waitlist_entry(repos, slot, add_member(repos, "A"))
    second = add_waitlist_entry(repos, slot, add_member(repos, "B"))
    assert (first.position, second.position) == (1, 2)
    assert repos.waitlist.list_waiting_for_slot(slot.id) == [first, second]

    repos.waitlist.update(replace(first, notified_at=DEFAULT_NOW))
    assert repos.waitlist.list_waiting_for_slot(slot.id) == [second]
    assert repos.waitlist.next_position(slot.id) == 3  # positions are never reused
    loaded = repos.waitlist.get(first.id or 0)
    assert loaded is not None and loaded.notified_at == DEFAULT_NOW
