"""JoinWaitlist: a member queues up for a slot that is currently booked.

Deliberately not one of the four use-case services, just validated repository CRUD.
"""

from padel.application.clock import Clock
from padel.application.repositories import Repositories
from padel.domain.entities import WaitlistEntry
from padel.domain.exceptions import NotEligibleForWaitlistError, NotFoundError


def join_waitlist(
    time_slot_id: int, member_id: int, repos: Repositories, clock: Clock
) -> WaitlistEntry:
    now = clock.now()
    if repos.members.get(member_id) is None:
        raise NotFoundError(f"member {member_id} not found")
    slot = repos.time_slots.get(time_slot_id)
    if slot is None:
        raise NotFoundError(f"time slot {time_slot_id} not found")
    if slot.starts_at <= now:
        raise NotEligibleForWaitlistError("time slot has already started")

    booking = repos.bookings.get_active_for_slot(time_slot_id)
    if booking is None or booking.id is None:
        raise NotEligibleForWaitlistError("time slot is free, book it directly")
    players = {p.member_id for p in repos.participants.list_by_booking(booking.id)}
    if member_id == booking.booked_by_member_id or member_id in players:
        raise NotEligibleForWaitlistError("member already plays in this slot")
    if any(e.member_id == member_id for e in repos.waitlist.list_waiting_for_slot(time_slot_id)):
        raise NotEligibleForWaitlistError("member is already on the waitlist")

    return repos.waitlist.add(
        WaitlistEntry(
            id=None,
            time_slot_id=time_slot_id,
            member_id=member_id,
            position=repos.waitlist.next_position(time_slot_id),
            created_at=now,
        )
    )
