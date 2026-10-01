"""Shared test doubles: FakeClock and in-memory repositories.

Used by all unit/application tests so they run without a database. The in-memory
repositories implement the Protocols from padel.application.repositories and mimic
the database constraints that matter for the business rules (see ADR 001).
"""

from __future__ import annotations

from datetime import datetime, timedelta


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
