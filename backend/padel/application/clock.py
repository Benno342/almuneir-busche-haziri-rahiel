"""Clock abstraction.

Services must never call `datetime.now()` directly. They receive a Clock via
constructor injection: SystemClock (padel.infrastructure.clock) in production,
FakeClock (tests/fakes.py) in tests.
"""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time as a timezone-aware datetime."""
        ...
