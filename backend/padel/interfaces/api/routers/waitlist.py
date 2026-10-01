from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel

from padel.application.join_waitlist import join_waitlist
from padel.interfaces.api.dependencies import ClockDep, RepositoriesDep

router = APIRouter(tags=["waitlist"])


class JoinWaitlistRequest(BaseModel):
    member_id: int


class WaitlistEntryResponse(BaseModel):
    id: int
    time_slot_id: int
    member_id: int
    position: int
    created_at: datetime
    notified_at: datetime | None


@router.post(
    "/time-slots/{time_slot_id}/waitlist",
    status_code=status.HTTP_201_CREATED,
    response_model=WaitlistEntryResponse,
)
def join_waitlist_endpoint(
    time_slot_id: int, body: JoinWaitlistRequest, repos: RepositoriesDep, clock: ClockDep
) -> WaitlistEntryResponse:
    entry = join_waitlist(time_slot_id, body.member_id, repos, clock)
    assert entry.id is not None
    return WaitlistEntryResponse(
        id=entry.id,
        time_slot_id=entry.time_slot_id,
        member_id=entry.member_id,
        position=entry.position,
        created_at=entry.created_at,
        notified_at=entry.notified_at,
    )
