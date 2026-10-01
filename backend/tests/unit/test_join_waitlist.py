from datetime import date, timedelta

import pytest

from padel.application.join_waitlist import join_waitlist
from padel.application.repositories import Repositories
from padel.domain.entities import BookingStatus
from padel.domain.exceptions import NotEligibleForWaitlistError, NotFoundError
from tests.builders import add_booking, add_member, add_participant, add_slot
from tests.fakes import FakeClock


@pytest.fixture
def repos(fake_repos: Repositories) -> Repositories:
    return fake_repos


def test_joins_waitlist_of_booked_slot(repos: Repositories, clock: FakeClock) -> None:
    slot = add_slot(repos)
    add_booking(repos, slot, add_member(repos, "Booker"))
    waiting = add_member(repos, "Waiting")
    assert slot.id is not None and waiting.id is not None

    entry = join_waitlist(slot.id, waiting.id, repos, clock)

    assert entry.id is not None
    assert (entry.time_slot_id, entry.member_id, entry.position) == (slot.id, waiting.id, 1)
    assert entry.created_at == clock.now()
    assert entry.notified_at is None
    assert repos.waitlist.list_waiting_for_slot(slot.id) == [entry]


def test_positions_are_assigned_in_joining_order(repos: Repositories, clock: FakeClock) -> None:
    slot = add_slot(repos)
    add_booking(repos, slot, add_member(repos, "Booker"))
    assert slot.id is not None
    first = join_waitlist(slot.id, add_member(repos, "A").id or 0, repos, clock)
    clock.advance(timedelta(minutes=1))
    second = join_waitlist(slot.id, add_member(repos, "B").id or 0, repos, clock)
    assert (first.position, second.position) == (1, 2)


def test_unknown_member_or_slot(repos: Repositories, clock: FakeClock) -> None:
    slot = add_slot(repos)
    member = add_member(repos)
    with pytest.raises(NotFoundError):
        join_waitlist(slot.id or 0, 999, repos, clock)
    with pytest.raises(NotFoundError):
        join_waitlist(999, member.id or 0, repos, clock)


@pytest.mark.parametrize("status", [BookingStatus.CANCELLED, BookingStatus.EXPIRED, None])
def test_free_slot_must_be_booked_directly(
    repos: Repositories, clock: FakeClock, status: BookingStatus | None
) -> None:
    slot = add_slot(repos)
    if status is not None:
        add_booking(repos, slot, add_member(repos, "Old"), status=status)
    with pytest.raises(NotEligibleForWaitlistError, match="free"):
        join_waitlist(slot.id or 0, add_member(repos).id or 0, repos, clock)


def test_slot_in_the_past(repos: Repositories, clock: FakeClock) -> None:
    slot = add_slot(repos, day=date(2026, 9, 30))
    add_booking(repos, slot, add_member(repos, "Booker"))
    with pytest.raises(NotEligibleForWaitlistError, match="started"):
        join_waitlist(slot.id or 0, add_member(repos).id or 0, repos, clock)


def test_booker_and_participants_cannot_join(repos: Repositories, clock: FakeClock) -> None:
    slot = add_slot(repos)
    booker, friend = add_member(repos, "Booker"), add_member(repos, "Friend")
    booking = add_booking(repos, slot, booker)
    add_participant(repos, booking, booker)
    add_participant(repos, booking, friend)
    for member in (booker, friend):
        with pytest.raises(NotEligibleForWaitlistError, match="already plays"):
            join_waitlist(slot.id or 0, member.id or 0, repos, clock)


def test_cannot_join_twice(repos: Repositories, clock: FakeClock) -> None:
    slot = add_slot(repos)
    add_booking(repos, slot, add_member(repos, "Booker"))
    member = add_member(repos)
    join_waitlist(slot.id or 0, member.id or 0, repos, clock)
    with pytest.raises(NotEligibleForWaitlistError, match="already on the waitlist"):
        join_waitlist(slot.id or 0, member.id or 0, repos, clock)
