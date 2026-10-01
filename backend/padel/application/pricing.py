"""Pricing of time slots.

Formula (all amounts in CHF):

    price = hourly_rate(slot) * duration_in_hours * tier_factor   (rounded half-up to 0.01)

    hourly_rate:  60.00 during peak hours, 40.00 otherwise
    peak hours:   Mon-Fri, slot *starts* between 17:00 (incl.) and 22:00 (excl.);
                  Saturday and Sunday all day
    tier_factor:  STANDARD 1.00, PREMIUM 0.80 (20 % discount)

The tier is the one of the booking member; all participants share that price.
Examples for a 90-minute slot: off-peak 60.00 / 48.00, peak 90.00 / 72.00
(STANDARD / PREMIUM).
"""

from datetime import time
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from padel.domain.entities import MembershipTier, TimeSlot

CENT = Decimal("0.01")


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


class PricingPolicy:
    OFF_PEAK_HOURLY_RATE = Decimal("40.00")
    PEAK_HOURLY_RATE = Decimal("60.00")
    PEAK_START = time(17, 0)
    PEAK_END = time(22, 0)
    TIER_FACTORS = {
        MembershipTier.STANDARD: Decimal("1.00"),
        MembershipTier.PREMIUM: Decimal("0.80"),
    }

    def is_peak(self, time_slot: TimeSlot) -> bool:
        if time_slot.date.weekday() >= 5:  # Saturday, Sunday
            return True
        return self.PEAK_START <= time_slot.start_time < self.PEAK_END

    def calculate_price(self, time_slot: TimeSlot, tier: MembershipTier) -> Decimal:
        rate = self.PEAK_HOURLY_RATE if self.is_peak(time_slot) else self.OFF_PEAK_HOURLY_RATE
        hours = Decimal(int(time_slot.duration.total_seconds())) / Decimal(3600)
        return _round(rate * hours * self.TIER_FACTORS[tier])


def split_evenly(total: Decimal, parts: int) -> list[Decimal]:
    """Split `total` into `parts` shares that add up exactly to `total`.

    The rounding remainder goes to the first share (by convention the booking member).
    """
    if parts < 1:
        raise ValueError("parts must be at least 1")
    base = (total / parts).quantize(CENT, rounding=ROUND_DOWN)
    first = total - base * (parts - 1)
    return [first] + [base] * (parts - 1)
