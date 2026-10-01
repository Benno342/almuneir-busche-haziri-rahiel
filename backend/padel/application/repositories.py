"""Repository protocols for all entities.

Services depend only on these Protocols. Implementations:
- padel.infrastructure.db.repositories (SQLAlchemy, production + integration tests)
- tests/fakes.py (in-memory, unit tests)

Rules for all implementations:
- `add` returns the entity with its `id` assigned.
- Returned entities are detached copies: changing one has NO effect until it is passed
  to `update`. Services must therefore always call `update` after mutating an entity.
- Repositories never commit. The transaction boundary is the API request
  (see padel.interfaces.api.dependencies.get_session).
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from padel.domain.entities import (
    Booking,
    BookingStatus,
    Court,
    Member,
    Participant,
    TimeSlot,
    WaitlistEntry,
)


class MemberRepository(Protocol):
    def get(self, member_id: int) -> Member | None: ...
    def add(self, member: Member) -> Member: ...
    def list_all(self) -> list[Member]: ...


class CourtRepository(Protocol):
    def get(self, court_id: int) -> Court | None: ...
    def add(self, court: Court) -> Court: ...
    def list_all(self) -> list[Court]: ...


class TimeSlotRepository(Protocol):
    def get(self, time_slot_id: int) -> TimeSlot | None: ...
    def add(self, time_slot: TimeSlot) -> TimeSlot: ...
    def list_by_date(self, day: date) -> list[TimeSlot]:
        """All slots on `day`, ordered by court_id and start_time."""
        ...


class BookingRepository(Protocol):
    def get(self, booking_id: int) -> Booking | None: ...

    def add(self, booking: Booking) -> Booking:
        """Persist a new booking.

        Raises SlotUnavailableError if the booking is active and the slot already has
        an active booking (enforced by a partial unique index, see ADR 001).
        """
        ...

    def update(self, booking: Booking) -> Booking: ...

    def get_active_for_slot(self, time_slot_id: int) -> Booking | None:
        """The PENDING_PAYMENT/CONFIRMED booking of the slot, if any."""
        ...

    def list_active_by_member(self, member_id: int) -> list[Booking]:
        """Active bookings made by the member (regardless of whether the slot is past)."""
        ...

    def list_by_status(self, status: BookingStatus) -> list[Booking]: ...


class ParticipantRepository(Protocol):
    def add(self, participant: Participant) -> Participant: ...
    def update(self, participant: Participant) -> Participant: ...
    def list_by_booking(self, booking_id: int) -> list[Participant]:
        """Participants of the booking, ordered by id (the booking member comes first)."""
        ...


class WaitlistRepository(Protocol):
    def get(self, entry_id: int) -> WaitlistEntry | None: ...
    def add(self, entry: WaitlistEntry) -> WaitlistEntry: ...
    def update(self, entry: WaitlistEntry) -> WaitlistEntry: ...

    def list_waiting_for_slot(self, time_slot_id: int) -> list[WaitlistEntry]:
        """Entries with notified_at IS NULL, ordered by position, then created_at."""
        ...

    def next_position(self, time_slot_id: int) -> int:
        """1 + highest position used for the slot so far (1 for an empty waitlist)."""
        ...


@dataclass(frozen=True)
class Repositories:
    """All repositories bundled, for convenient injection."""

    members: MemberRepository
    courts: CourtRepository
    time_slots: TimeSlotRepository
    bookings: BookingRepository
    participants: ParticipantRepository
    waitlist: WaitlistRepository
