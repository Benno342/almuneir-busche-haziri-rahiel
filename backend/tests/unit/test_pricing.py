"""Pricing formula (see docstring of padel.application.pricing).

Reference dates: 2026-10-05 is a Monday, 2026-10-10 a Saturday.
"""

from datetime import date, time
from decimal import Decimal

import pytest

from padel.application.pricing import PricingPolicy, split_evenly
from padel.domain.entities import MembershipTier, TimeSlot

MONDAY = date(2026, 10, 5)
SATURDAY = date(2026, 10, 10)
STANDARD = MembershipTier.STANDARD
PREMIUM = MembershipTier.PREMIUM


def slot(day: date, start: time, end: time) -> TimeSlot:
    return TimeSlot(id=1, court_id=1, date=day, start_time=start, end_time=end)


@pytest.fixture
def policy() -> PricingPolicy:
    return PricingPolicy()


@pytest.mark.parametrize(
    ("day", "start", "end", "tier", "expected"),
    [
        # weekday off-peak: 40 CHF/h
        (MONDAY, time(10, 0), time(11, 30), STANDARD, "60.00"),
        (MONDAY, time(10, 0), time(11, 0), STANDARD, "40.00"),
        # weekday peak (start 17:00-21:59): 60 CHF/h
        (MONDAY, time(18, 0), time(19, 30), STANDARD, "90.00"),
        # premium: 20 % discount
        (MONDAY, time(10, 0), time(11, 30), PREMIUM, "48.00"),
        (MONDAY, time(18, 0), time(19, 30), PREMIUM, "72.00"),
        # weekends are peak all day
        (SATURDAY, time(9, 0), time(10, 30), STANDARD, "90.00"),
    ],
)
def test_calculate_price(
    policy: PricingPolicy, day: date, start: time, end: time, tier: MembershipTier, expected: str
) -> None:
    assert policy.calculate_price(slot(day, start, end), tier) == Decimal(expected)


@pytest.mark.parametrize(
    ("start", "end", "is_peak"),
    [
        (time(16, 30), time(18, 0), False),  # starts before peak -> off-peak, start decides
        (time(17, 0), time(18, 30), True),  # boundary: 17:00 inclusive
        (time(21, 30), time(23, 0), True),
        (time(22, 0), time(23, 0), False),  # boundary: 22:00 exclusive
    ],
)
def test_peak_boundaries_on_weekdays(
    policy: PricingPolicy, start: time, end: time, is_peak: bool
) -> None:
    assert policy.is_peak(slot(MONDAY, start, end)) is is_peak


def test_price_is_rounded_to_cents(policy: PricingPolicy) -> None:
    # 50 min off-peak premium: 40 * 50/60 * 0.8 = 26.666...
    price = policy.calculate_price(slot(MONDAY, time(10, 0), time(10, 50)), PREMIUM)
    assert price == Decimal("26.67")
    assert price.as_tuple().exponent == -2


@pytest.mark.parametrize(
    ("total", "parts", "expected"),
    [
        ("90.00", 1, ["90.00"]),
        ("90.00", 4, ["22.50", "22.50", "22.50", "22.50"]),
        ("100.00", 3, ["33.34", "33.33", "33.33"]),
        ("72.00", 4, ["18.00", "18.00", "18.00", "18.00"]),
        ("26.67", 4, ["6.69", "6.66", "6.66", "6.66"]),
    ],
)
def test_split_evenly_puts_remainder_on_first_share(
    total: str, parts: int, expected: list[str]
) -> None:
    shares = split_evenly(Decimal(total), parts)
    assert shares == [Decimal(s) for s in expected]
    assert sum(shares) == Decimal(total)


def test_split_evenly_rejects_zero_parts() -> None:
    with pytest.raises(ValueError):
        split_evenly(Decimal("10.00"), 0)
