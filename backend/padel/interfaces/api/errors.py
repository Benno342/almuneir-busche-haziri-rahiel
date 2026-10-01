"""Single place where domain errors become HTTP responses.

Response body for every domain error: {"error": "<ExceptionClass>", "detail": "<message>"}.
New exceptions in padel/domain/exceptions.py must be added here (a test enforces it).
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from padel.domain import exceptions as e

ERROR_STATUS_CODES: dict[type[e.DomainError], int] = {
    e.NotFoundError: status.HTTP_404_NOT_FOUND,
    e.NotAuthorizedError: status.HTTP_403_FORBIDDEN,
    e.SlotUnavailableError: status.HTTP_409_CONFLICT,
    e.BookingLimitExceededError: status.HTTP_409_CONFLICT,
    e.BookingWindowExceededError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    e.InvalidCancellationError: status.HTTP_409_CONFLICT,
    e.PaymentWindowExpiredError: status.HTTP_409_CONFLICT,
    e.InvalidPaymentError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    e.NotEligibleForWaitlistError: status.HTTP_409_CONFLICT,
}


def status_code_for(error: e.DomainError) -> int:
    for cls in type(error).__mro__:
        if cls in ERROR_STATUS_CODES:
            return ERROR_STATUS_CODES[cls]
    return status.HTTP_400_BAD_REQUEST


async def _handle_domain_error(_request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, e.DomainError)
    return JSONResponse(
        status_code=status_code_for(error),
        content={"error": type(error).__name__, "detail": str(error)},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(e.DomainError, _handle_domain_error)
