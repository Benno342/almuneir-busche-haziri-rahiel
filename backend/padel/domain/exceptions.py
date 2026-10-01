"""Domain errors.

Every business-rule violation raises a subclass of DomainError. The API layer maps
them to HTTP status codes in one place (padel/interfaces/api/errors.py), so services
never deal with HTTP.
"""


class DomainError(Exception):
    """Base class for all business-rule violations."""


class NotFoundError(DomainError):
    """A referenced entity (member, slot, booking, ...) does not exist."""


class NotAuthorizedError(DomainError):
    """The requesting member is not allowed to perform this action."""


class SlotUnavailableError(DomainError):
    """The time slot already has an active booking (or lies in the past)."""


class BookingLimitExceededError(DomainError):
    """The member already holds the maximum number of active bookings."""


class BookingWindowExceededError(DomainError):
    """The slot lies too far in the future for the member's tier."""


class InvalidCancellationError(DomainError):
    """The booking cannot be cancelled in its current state."""


class PaymentWindowExpiredError(DomainError):
    """The payment deadline of the booking has passed."""


class InvalidPaymentError(DomainError):
    """The payment does not match the booking (wrong member, already paid, wrong amount)."""


class NotEligibleForWaitlistError(DomainError):
    """The member cannot join the waitlist of this slot."""
