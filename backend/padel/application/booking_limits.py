"""Shared rule: how many active bookings a member currently holds.

Used by several services (BookCourt, PromoteFromWaitlist), which must not import each
other, so it lives here.

Only bookings for slots that have not started yet count: an already played CONFIRMED
booking stays CONFIRMED forever and must not block the member from booking again.
"""

from datetime import datetime

from padel.application.repositories import BookingRepository, TimeSlotRepository
from padel.domain.entities import MAX_ACTIVE_BOOKINGS_PER_MEMBER


def count_upcoming_active_bookings(
    member_id: int,
    bookings: BookingRepository,
    time_slots: TimeSlotRepository,
    now: datetime,
) -> int:
    count = 0
    for booking in bookings.list_active_by_member(member_id):
        slot = time_slots.get(booking.time_slot_id)
        if slot is not None and slot.starts_at > now:
            count += 1
    return count


def has_reached_limit(
    member_id: int,
    bookings: BookingRepository,
    time_slots: TimeSlotRepository,
    now: datetime,
) -> bool:
    count = count_upcoming_active_bookings(member_id, bookings, time_slots, now)
    return count >= MAX_ACTIVE_BOOKINGS_PER_MEMBER
