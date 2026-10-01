import pytest

from padel.domain import exceptions


@pytest.mark.parametrize(
    "name",
    [
        "SlotUnavailableError",
        "BookingLimitExceededError",
        "BookingWindowExceededError",
        "InvalidCancellationError",
        "PaymentWindowExpiredError",
        "NotEligibleForWaitlistError",
        "NotFoundError",
        "NotAuthorizedError",
        "InvalidPaymentError",
    ],
)
def test_all_domain_errors_share_a_base_class(name: str) -> None:
    error_type = getattr(exceptions, name)
    assert issubclass(error_type, exceptions.DomainError)
    assert str(error_type("boom")) == "boom"
