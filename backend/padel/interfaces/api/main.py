"""FastAPI application factory.

Run locally:  uvicorn padel.interfaces.api.main:create_app --factory --reload
Configuration via environment: DATABASE_URL, CORS_ORIGINS (comma separated).
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker

from padel.application.clock import Clock
from padel.infrastructure.clock import SystemClock
from padel.infrastructure.db.session import (
    create_db_engine,
    create_session_factory,
    database_url_from_env,
)
from padel.interfaces.api.errors import register_error_handlers
from padel.interfaces.api.routers import waitlist

DEFAULT_CORS_ORIGINS = "http://localhost:5173"


def create_app(
    session_factory: sessionmaker[Session] | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    app = FastAPI(title="Padel Court Booking", version="0.1.0")
    app.state.session_factory = session_factory or create_session_factory(
        create_db_engine(database_url_from_env())
    )
    app.state.clock = clock or SystemClock()

    origins = os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(waitlist.router)
    return app
