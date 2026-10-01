"""FastAPI dependencies: one DB session (= one transaction) per request.

The session commits when the endpoint returns normally and rolls back on any
exception, so services and repositories never commit themselves.

Service factories (e.g. `get_book_court_service`) belong next to their router and are
built from `RepositoriesDep` and `ClockDep`. Orchestration across services (cancel ->
promote from waitlist) also happens in the routers, never inside a service.
"""

from collections.abc import Iterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from padel.application.clock import Clock
from padel.application.pricing import PricingPolicy
from padel.application.repositories import Repositories
from padel.infrastructure.db.repositories import sql_repositories


def get_session(request: Request) -> Iterator[Session]:
    factory = cast(sessionmaker[Session], request.app.state.session_factory)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_repositories(session: Annotated[Session, Depends(get_session)]) -> Repositories:
    return sql_repositories(session)


def get_clock(request: Request) -> Clock:
    return cast(Clock, request.app.state.clock)


def get_pricing_policy() -> PricingPolicy:
    return PricingPolicy()


RepositoriesDep = Annotated[Repositories, Depends(get_repositories)]
ClockDep = Annotated[Clock, Depends(get_clock)]
PricingDep = Annotated[PricingPolicy, Depends(get_pricing_policy)]
