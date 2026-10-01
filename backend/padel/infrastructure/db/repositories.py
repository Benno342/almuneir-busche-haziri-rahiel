"""SQLAlchemy implementations of the repository protocols.

Each repository converts between ORM models and domain dataclasses, so entities
handed to services are detached copies. Repositories flush but never commit.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from padel.application.repositories import Repositories
from padel.domain.entities import (
    ACTIVE_BOOKING_STATUSES,
    Booking,
    BookingStatus,
    Court,
    Member,
    MembershipTier,
    Participant,
    TimeSlot,
    WaitlistEntry,
)
from padel.domain.exceptions import SlotUnavailableError
from padel.infrastructure.db.models import (
    ACTIVE_BOOKING_INDEX,
    BookingModel,
    CourtModel,
    MemberModel,
    ParticipantModel,
    TimeSlotModel,
    WaitlistEntryModel,
)

_ACTIVE = [s.value for s in ACTIVE_BOOKING_STATUSES]


def _require(model: object | None, kind: str, entity_id: int | None) -> object:
    if model is None:
        raise LookupError(f"{kind} {entity_id} does not exist")
    return model


# --- Member ---------------------------------------------------------------------------


def _member(m: MemberModel) -> Member:
    return Member(
        id=m.id,
        name=m.name,
        email=m.email,
        membership_tier=MembershipTier(m.membership_tier),
        joined_at=m.joined_at,
    )


class SqlMemberRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, member_id: int) -> Member | None:
        model = self._session.get(MemberModel, member_id)
        return _member(model) if model else None

    def add(self, member: Member) -> Member:
        model = MemberModel(
            name=member.name,
            email=member.email,
            membership_tier=member.membership_tier.value,
            joined_at=member.joined_at,
        )
        self._session.add(model)
        self._session.flush()
        return _member(model)

    def list_all(self) -> list[Member]:
        models = self._session.scalars(select(MemberModel).order_by(MemberModel.id))
        return [_member(m) for m in models]


# --- Court ----------------------------------------------------------------------------


def _court(m: CourtModel) -> Court:
    return Court(id=m.id, name=m.name, indoor=m.indoor)


class SqlCourtRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, court_id: int) -> Court | None:
        model = self._session.get(CourtModel, court_id)
        return _court(model) if model else None

    def add(self, court: Court) -> Court:
        model = CourtModel(name=court.name, indoor=court.indoor)
        self._session.add(model)
        self._session.flush()
        return _court(model)

    def list_all(self) -> list[Court]:
        models = self._session.scalars(select(CourtModel).order_by(CourtModel.id))
        return [_court(m) for m in models]


# --- TimeSlot -------------------------------------------------------------------------


def _time_slot(m: TimeSlotModel) -> TimeSlot:
    return TimeSlot(
        id=m.id, court_id=m.court_id, date=m.date, start_time=m.start_time, end_time=m.end_time
    )


class SqlTimeSlotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, time_slot_id: int) -> TimeSlot | None:
        model = self._session.get(TimeSlotModel, time_slot_id)
        return _time_slot(model) if model else None

    def add(self, time_slot: TimeSlot) -> TimeSlot:
        model = TimeSlotModel(
            court_id=time_slot.court_id,
            date=time_slot.date,
            start_time=time_slot.start_time,
            end_time=time_slot.end_time,
        )
        self._session.add(model)
        self._session.flush()
        return _time_slot(model)

    def list_by_date(self, day: date) -> list[TimeSlot]:
        stmt = (
            select(TimeSlotModel)
            .where(TimeSlotModel.date == day)
            .order_by(TimeSlotModel.court_id, TimeSlotModel.start_time)
        )
        return [_time_slot(m) for m in self._session.scalars(stmt)]


# --- Booking --------------------------------------------------------------------------


def _booking(m: BookingModel) -> Booking:
    return Booking(
        id=m.id,
        time_slot_id=m.time_slot_id,
        booked_by_member_id=m.booked_by_member_id,
        status=BookingStatus(m.status),
        total_price=m.total_price,
        created_at=m.created_at,
        confirmed_at=m.confirmed_at,
    )


def _is_active_slot_violation(error: IntegrityError) -> bool:
    # PostgreSQL names the index; SQLite only names the column.
    message = str(error.orig)
    return ACTIVE_BOOKING_INDEX in message or "bookings.time_slot_id" in message


class SqlBookingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, booking_id: int) -> Booking | None:
        model = self._session.get(BookingModel, booking_id)
        return _booking(model) if model else None

    def add(self, booking: Booking) -> Booking:
        model = BookingModel(
            time_slot_id=booking.time_slot_id,
            booked_by_member_id=booking.booked_by_member_id,
            status=booking.status.value,
            total_price=booking.total_price,
            created_at=booking.created_at,
            confirmed_at=booking.confirmed_at,
        )
        with self._active_slot_guard(booking.time_slot_id):
            self._session.add(model)
        return _booking(model)

    def update(self, booking: Booking) -> Booking:
        model = _require(self._session.get(BookingModel, booking.id), "Booking", booking.id)
        assert isinstance(model, BookingModel)
        with self._active_slot_guard(model.time_slot_id):
            model.status = booking.status.value
            model.total_price = booking.total_price
            model.confirmed_at = booking.confirmed_at
        return _booking(model)

    @contextmanager
    def _active_slot_guard(self, time_slot_id: int) -> Iterator[None]:
        """Run the write inside a SAVEPOINT, so a violation of the partial unique index
        only rolls back this write, and translate it into the domain error (ADR 001).

        Changes must be made *inside* the block: begin_nested() flushes pending changes
        before the SAVEPOINT is created.
        """
        try:
            with self._session.begin_nested():
                yield
        except IntegrityError as error:
            if _is_active_slot_violation(error):
                raise SlotUnavailableError(f"time slot {time_slot_id} is already booked") from error
            raise

    def get_active_for_slot(self, time_slot_id: int) -> Booking | None:
        stmt = select(BookingModel).where(
            BookingModel.time_slot_id == time_slot_id, BookingModel.status.in_(_ACTIVE)
        )
        model = self._session.scalars(stmt).first()
        return _booking(model) if model else None

    def list_active_by_member(self, member_id: int) -> list[Booking]:
        stmt = (
            select(BookingModel)
            .where(BookingModel.booked_by_member_id == member_id, BookingModel.status.in_(_ACTIVE))
            .order_by(BookingModel.id)
        )
        return [_booking(m) for m in self._session.scalars(stmt)]

    def list_by_status(self, status: BookingStatus) -> list[Booking]:
        stmt = select(BookingModel).where(BookingModel.status == status.value)
        stmt = stmt.order_by(BookingModel.id)
        return [_booking(m) for m in self._session.scalars(stmt)]


# --- Participant ----------------------------------------------------------------------


def _participant(m: ParticipantModel) -> Participant:
    return Participant(
        id=m.id,
        booking_id=m.booking_id,
        member_id=m.member_id,
        share_amount=m.share_amount,
        paid=m.paid,
        paid_at=m.paid_at,
    )


class SqlParticipantRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, participant: Participant) -> Participant:
        model = ParticipantModel(
            booking_id=participant.booking_id,
            member_id=participant.member_id,
            share_amount=participant.share_amount,
            paid=participant.paid,
            paid_at=participant.paid_at,
        )
        self._session.add(model)
        self._session.flush()
        return _participant(model)

    def update(self, participant: Participant) -> Participant:
        model = _require(
            self._session.get(ParticipantModel, participant.id), "Participant", participant.id
        )
        assert isinstance(model, ParticipantModel)
        model.share_amount = participant.share_amount
        model.paid = participant.paid
        model.paid_at = participant.paid_at
        self._session.flush()
        return _participant(model)

    def list_by_booking(self, booking_id: int) -> list[Participant]:
        stmt = (
            select(ParticipantModel)
            .where(ParticipantModel.booking_id == booking_id)
            .order_by(ParticipantModel.id)
        )
        return [_participant(m) for m in self._session.scalars(stmt)]


# --- WaitlistEntry --------------------------------------------------------------------


def _waitlist_entry(m: WaitlistEntryModel) -> WaitlistEntry:
    return WaitlistEntry(
        id=m.id,
        time_slot_id=m.time_slot_id,
        member_id=m.member_id,
        position=m.position,
        created_at=m.created_at,
        notified_at=m.notified_at,
    )


class SqlWaitlistRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, entry_id: int) -> WaitlistEntry | None:
        model = self._session.get(WaitlistEntryModel, entry_id)
        return _waitlist_entry(model) if model else None

    def add(self, entry: WaitlistEntry) -> WaitlistEntry:
        model = WaitlistEntryModel(
            time_slot_id=entry.time_slot_id,
            member_id=entry.member_id,
            position=entry.position,
            created_at=entry.created_at,
            notified_at=entry.notified_at,
        )
        self._session.add(model)
        self._session.flush()
        return _waitlist_entry(model)

    def update(self, entry: WaitlistEntry) -> WaitlistEntry:
        model = _require(self._session.get(WaitlistEntryModel, entry.id), "WaitlistEntry", entry.id)
        assert isinstance(model, WaitlistEntryModel)
        model.position = entry.position
        model.notified_at = entry.notified_at
        self._session.flush()
        return _waitlist_entry(model)

    def list_waiting_for_slot(self, time_slot_id: int) -> list[WaitlistEntry]:
        stmt = (
            select(WaitlistEntryModel)
            .where(
                WaitlistEntryModel.time_slot_id == time_slot_id,
                WaitlistEntryModel.notified_at.is_(None),
            )
            .order_by(WaitlistEntryModel.position, WaitlistEntryModel.created_at)
        )
        return [_waitlist_entry(m) for m in self._session.scalars(stmt)]

    def next_position(self, time_slot_id: int) -> int:
        stmt = select(func.coalesce(func.max(WaitlistEntryModel.position), 0)).where(
            WaitlistEntryModel.time_slot_id == time_slot_id
        )
        return int(self._session.scalar(stmt) or 0) + 1


def sql_repositories(session: Session) -> Repositories:
    return Repositories(
        members=SqlMemberRepository(session),
        courts=SqlCourtRepository(session),
        time_slots=SqlTimeSlotRepository(session),
        bookings=SqlBookingRepository(session),
        participants=SqlParticipantRepository(session),
        waitlist=SqlWaitlistRepository(session),
    )
