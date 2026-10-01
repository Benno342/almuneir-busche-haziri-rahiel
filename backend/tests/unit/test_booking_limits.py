from datetime import UTC, date, datetime, time

from padel.application.booking_limits import count_upcoming_active_bookings, has_reached_limit
from padel.application.repositories import Repositories
from padel.domain.entities import BookingStatus
from tests.builders import add_booking, add_court, add_member, add_slot

NOW = datetime(2026, 10, 5, 16, 0, tzinfo=UTC)  # 18:00 in Zurich


def test_counts_only_active_bookings_for_slots_that_have_not_started(
    fake_repos: Repositories,
) -> None:
    repos = fake_repos
    member = add_member(repos)
    court = add_court(repos)
    past = add_slot(repos, court, day=date(2026, 10, 4))
    starting_now = add_slot(repos, court, day=date(2026, 10, 5), start=time(18, 0))
    future = add_slot(repos, court, day=date(2026, 10, 6))
    cancelled_slot = add_slot(repos, court, day=date(2026, 10, 7))

    add_booking(repos, past, member, status=BookingStatus.CONFIRMED)
    add_booking(repos, starting_now, member)
    add_booking(repos, future, member, status=BookingStatus.CONFIRMED)
    add_booking(repos, cancelled_slot, member, status=BookingStatus.CANCELLED)

    assert member.id is not None
    assert count_upcoming_active_bookings(member.id, repos.bookings, repos.time_slots, NOW) == 1
    assert not has_reached_limit(member.id, repos.bookings, repos.time_slots, NOW)


def test_limit_is_reached_with_two_upcoming_active_bookings(fake_repos: Repositories) -> None:
    repos = fake_repos
    member = add_member(repos)
    court = add_court(repos)
    add_booking(repos, add_slot(repos, court, day=date(2026, 10, 6)), member)
    add_booking(repos, add_slot(repos, court, day=date(2026, 10, 7)), member)
    assert member.id is not None
    assert has_reached_limit(member.id, repos.bookings, repos.time_slots, NOW)
