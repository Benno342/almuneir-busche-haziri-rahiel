import pytest
from fastapi.testclient import TestClient

from padel.domain import exceptions
from padel.interfaces.api.errors import ERROR_STATUS_CODES


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _all_subclasses(cls: type) -> set[type]:
    direct = set(cls.__subclasses__())
    return direct.union(*(_all_subclasses(c) for c in direct))


def test_every_domain_error_has_an_explicit_http_status() -> None:
    """Add new exceptions from domain/exceptions.py to ERROR_STATUS_CODES."""
    assert _all_subclasses(exceptions.DomainError) <= set(ERROR_STATUS_CODES)


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (exceptions.NotFoundError, 404),
        (exceptions.NotAuthorizedError, 403),
        (exceptions.SlotUnavailableError, 409),
        (exceptions.BookingLimitExceededError, 409),
        (exceptions.BookingWindowExceededError, 422),
        (exceptions.InvalidCancellationError, 409),
        (exceptions.PaymentWindowExpiredError, 409),
        (exceptions.InvalidPaymentError, 422),
        (exceptions.NotEligibleForWaitlistError, 409),
    ],
)
def test_status_codes(error: type[exceptions.DomainError], status: int) -> None:
    assert ERROR_STATUS_CODES[error] == status
