"""Shared test doubles: FakeClock and in-memory repositories.

Used by all unit/application tests so they run without a database. The in-memory
repositories implement the Protocols from padel.application.repositories and mimic
the database constraints that matter for the business rules (see ADR 001).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Protocol

from padel.application.repositories import Repositories
from padel.domain.entities import (
    Booking,
    BookingStatus,
    Court,
    Member,
    Participant,
    TimeSlot,
    WaitlistEntry,
)
from padel.domain.exceptions import SlotUnavailableError


class FakeClock:
    def __init__(self, now: datetime) -> None:
        if now.tzinfo is None:
            raise ValueError("FakeClock needs a timezone-aware datetime")
        self._now = now

    def now(self) -> datetime:
        return self._now

    def set(self, now: datetime) -> None:
        if now.tzinfo is None:
            raise ValueError("FakeClock needs a timezone-aware datetime")
        self._now = now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


class _HasId(Protocol):
    id: int | None


# --------------------------------------------------------------------------------------
# In-memory repositories
# --------------------------------------------------------------------------------------

class _InMemoryStore[T: _HasId]:
    """Stores copies so that mutating a returned entity without `update` has no effect,
    exactly like the SQL repositories."""

    def __init__(self) -> None:
        self._items: dict[int, T] = {}
        self._next_id = 1

    def _get(self, entity_id: int) -> T | None:
        item = self._items.get(entity_id)
        return replace(item) if item is not None else None

    def _add(self, entity: T) -> T:
        stored = replace(entity, id=self._next_id)
        self._next_id += 1
        self._items[stored.id] = stored  # type: ignore[index]
        return replace(stored)

    def _update(self, entity: T) -> T:
        if entity.id is None or entity.id not in self._items:
            raise LookupError(f"{type(entity).__name__} {entity.id} does not exist")
        self._items[entity.id] = replace(entity)
        return replace(entity)

    def _all(self) -> list[T]:
        return [replace(item) for item in self._items.values()]


class InMemoryMemberRepository(_InMemoryStore[Member]):
    def get(self, member_id: int) -> Member | None:
        return self._get(member_id)

    def add(self, member: Member) -> Member:
        return self._add(member)

    def list_all(self) -> list[Member]:
        return self._all()


class InMemoryCourtRepository(_InMemoryStore[Court]):
    def get(self, court_id: int) -> Court | None:
        return self._get(court_id)

    def add(self, court: Court) -> Court:
        return self._add(court)

    def list_all(self) -> list[Court]:
        return self._all()


class InMemoryTimeSlotRepository(_InMemoryStore[TimeSlot]):
    def get(self, time_slot_id: int) -> TimeSlot | None:
        return self._get(time_slot_id)

    def add(self, time_slot: TimeSlot) -> TimeSlot:
        duplicate = any(
            (s.court_id, s.date, s.start_time)
            == (time_slot.court_id, time_slot.date, time_slot.start_time)
            for s in self._items.values()
        )
        if duplicate:
            raise ValueError("time slot already exists for court/date/start_time")
        return self._add(time_slot)

    def list_by_date(self, day: date) -> list[TimeSlot]:
        slots = [s for s in self._all() if s.date == day]
        return sorted(slots, key=lambda s: (s.court_id, s.start_time))


class InMemoryBookingRepository(_InMemoryStore[Booking]):
    def get(self, booking_id: int) -> Booking | None:
        return self._get(booking_id)

    def add(self, booking: Booking) -> Booking:
        self._check_slot_free(booking)
        return self._add(booking)

    def update(self, booking: Booking) -> Booking:
        self._check_slot_free(booking)
        return self._update(booking)

    def get_active_for_slot(self, time_slot_id: int) -> Booking | None:
        return next(
            (b for b in self._all() if b.time_slot_id == time_slot_id and b.is_active), None
        )

    def list_active_by_member(self, member_id: int) -> list[Booking]:
        return [b for b in self._all() if b.booked_by_member_id == member_id and b.is_active]

    def list_by_status(self, status: BookingStatus) -> list[Booking]:
        return [b for b in self._all() if b.status == status]

    def _check_slot_free(self, booking: Booking) -> None:
        """Mimics the partial unique index uq_bookings_active_time_slot (ADR 001)."""
        if not booking.is_active:
            return
        current = self.get_active_for_slot(booking.time_slot_id)
        if current is not None and current.id != booking.id:
            raise SlotUnavailableError(f"time slot {booking.time_slot_id} is already booked")


class InMemoryParticipantRepository(_InMemoryStore[Participant]):
    def add(self, participant: Participant) -> Participant:
        return self._add(participant)

    def update(self, participant: Participant) -> Participant:
        return self._update(participant)

    def list_by_booking(self, booking_id: int) -> list[Participant]:
        return sorted(
            (p for p in self._all() if p.booking_id == booking_id),
            key=lambda p: p.id or 0,
        )


class InMemoryWaitlistRepository(_InMemoryStore[WaitlistEntry]):
    def get(self, entry_id: int) -> WaitlistEntry | None:
        return self._get(entry_id)

    def add(self, entry: WaitlistEntry) -> WaitlistEntry:
        return self._add(entry)

    def update(self, entry: WaitlistEntry) -> WaitlistEntry:
        return self._update(entry)

    def list_waiting_for_slot(self, time_slot_id: int) -> list[WaitlistEntry]:
        entries = [e for e in self._all() if e.time_slot_id == time_slot_id and e.is_waiting]
        return sorted(entries, key=lambda e: (e.position, e.created_at))

    def next_position(self, time_slot_id: int) -> int:
        positions = [e.position for e in self._all() if e.time_slot_id == time_slot_id]
        return max(positions, default=0) + 1


def in_memory_repositories() -> Repositories:
    return Repositories(
        members=InMemoryMemberRepository(),
        courts=InMemoryCourtRepository(),
        time_slots=InMemoryTimeSlotRepository(),
        bookings=InMemoryBookingRepository(),
        participants=InMemoryParticipantRepository(),
        waitlist=InMemoryWaitlistRepository(),
    )
