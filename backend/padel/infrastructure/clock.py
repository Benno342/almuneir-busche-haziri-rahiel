from datetime import UTC, datetime


class SystemClock:
    """Production Clock: the real current time in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)
