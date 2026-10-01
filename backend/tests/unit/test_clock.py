from datetime import UTC, datetime, timedelta

import pytest

from padel.application.clock import Clock
from padel.infrastructure.clock import SystemClock
from tests.fakes import FakeClock


def test_system_clock_returns_aware_utc_now() -> None:
    clock: Clock = SystemClock()
    before = datetime.now(UTC)
    now = clock.now()
    assert now.tzinfo is not None
    assert before <= now <= datetime.now(UTC)


def test_fake_clock_is_fixed_and_can_advance() -> None:
    start = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    clock: Clock = FakeClock(start)
    assert clock.now() == start
    assert clock.now() == start
    assert isinstance(clock, FakeClock)
    clock.advance(timedelta(hours=12))
    assert clock.now() == start + timedelta(hours=12)


def test_fake_clock_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError):
        FakeClock(datetime(2026, 10, 1, 8, 0))
