from fastapi.testclient import TestClient

from padel.domain.entities import BookingStatus
from tests.api.conftest import Seed
from tests.builders import add_booking, add_member, add_slot


def test_join_waitlist(client: TestClient, seed: Seed) -> None:
    with seed() as repos:
        slot = add_slot(repos)
        add_booking(repos, slot, add_member(repos, "Booker"))
        member = add_member(repos, "Waiting")

    response = client.post(f"/time-slots/{slot.id}/waitlist", json={"member_id": member.id})

    assert response.status_code == 201
    body = response.json()
    assert body["time_slot_id"] == slot.id
    assert body["member_id"] == member.id
    assert body["position"] == 1
    assert body["created_at"].startswith("2026-10-01T08:00:00")
    with seed() as repos:  # committed by the request
        assert [e.member_id for e in repos.waitlist.list_waiting_for_slot(slot.id or 0)] == [
            member.id
        ]


def test_join_waitlist_of_free_slot_is_a_conflict(client: TestClient, seed: Seed) -> None:
    with seed() as repos:
        slot = add_slot(repos)
        add_booking(repos, slot, add_member(repos, "Old"), status=BookingStatus.CANCELLED)
        member = add_member(repos, "Waiting")

    response = client.post(f"/time-slots/{slot.id}/waitlist", json={"member_id": member.id})

    assert response.status_code == 409
    assert response.json() == {
        "error": "NotEligibleForWaitlistError",
        "detail": "time slot is free, book it directly",
    }


def test_join_waitlist_of_unknown_slot(client: TestClient, seed: Seed) -> None:
    with seed() as repos:
        member = add_member(repos)
    response = client.post("/time-slots/999/waitlist", json={"member_id": member.id})
    assert response.status_code == 404
    assert response.json()["error"] == "NotFoundError"


def test_join_waitlist_validates_body(client: TestClient) -> None:
    assert client.post("/time-slots/1/waitlist", json={}).status_code == 422
