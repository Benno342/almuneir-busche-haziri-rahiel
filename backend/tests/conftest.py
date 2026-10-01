import pytest

from padel.application.repositories import Repositories
from tests.builders import DEFAULT_NOW
from tests.fakes import FakeClock, in_memory_repositories


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(DEFAULT_NOW)


@pytest.fixture
def fake_repos() -> Repositories:
    return in_memory_repositories()
