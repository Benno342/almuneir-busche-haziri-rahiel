"""ADR 001: the partial unique index stops double bookings even when two requests pass
the service-side check at the same time (classic check-then-insert race)."""

import pytest
from sqlalchemy import Engine

from padel.domain.exceptions import SlotUnavailableError
from padel.infrastructure.db.repositories import sql_repositories
from tests.builders import add_booking, add_member, add_slot
from tests.conftest import open_session

pytestmark = pytest.mark.integration


def test_concurrent_bookings_of_the_same_slot(postgres_engine: Engine) -> None:
    with open_session(postgres_engine) as setup:
        repos = sql_repositories(setup)
        slot = add_slot(repos)
        alice, bob = add_member(repos, "Alice"), add_member(repos, "Bob")
        setup.commit()

    with open_session(postgres_engine) as first, open_session(postgres_engine) as second:
        repos_a, repos_b = sql_repositories(first), sql_repositories(second)
        assert slot.id is not None

        # Both requests see a free slot ...
        assert repos_a.bookings.get_active_for_slot(slot.id) is None
        assert repos_b.bookings.get_active_for_slot(slot.id) is None

        # ... the first one wins ...
        add_booking(repos_a, slot, alice)
        first.commit()

        # ... and the database rejects the second one.
        with pytest.raises(SlotUnavailableError):
            add_booking(repos_b, slot, bob)
