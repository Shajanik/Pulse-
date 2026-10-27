from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from .. import database as db
from ..deps import AuthUser, auth_required
from ..results import build_results_from_redis, fetch_poll_by_code
from ..schemas import (
    CreatePollRequest,
    PollOut,
    PublicPollOut,
    ResultsPayload,
    options_out,
    poll_out,
    poll_status,
)
from ..utils import generate_room_code

router = APIRouter(prefix="/polls", tags=["polls"])

VALID_EXPIRATIONS = {5, 15, 30}


@router.post("", status_code=201, response_model=PollOut)
async def create_poll(req: CreatePollRequest, user: AuthUser = Depends(auth_required)):
    host_oid = user.oid

    question = req.question.strip()
    if not question:
        raise HTTPException(400, "question cannot be empty")

    options = [o.strip() for o in req.options if o.strip()]
    if not 2 <= len(options) <= 4:
        raise HTTPException(400, "a poll needs 2 to 4 non-empty options")

    if req.expires_in_minutes not in VALID_EXPIRATIONS:
        raise HTTPException(400, "expiration must be 5, 15, or 30 minutes")

    now = datetime.now(timezone.utc)
    doc = {
        "hostId": host_oid,
        "question": question,
        "options": [{"id": ObjectId(), "text": text} for text in options],
        "createdAt": now,
        "expiresAt": now + timedelta(minutes=req.expires_in_minutes),
    }

    # Generate a unique 6-digit code, retrying on the rare collision. The
    # unique index on polls.code makes the insert itself the atomic check.
    for _ in range(10):
        doc["code"] = generate_room_code()
        try:
            await db.polls.insert_one(doc)  # also sets doc["_id"]
            return poll_out(doc)
        except DuplicateKeyError:
            doc.pop("_id", None)
            continue

    raise HTTPException(500, "could not allocate a room code, please try again")


# NOTE: declared before "/{code}" so "mine" isn't captured as a room code.
@router.get("/mine", response_model=list[PollOut])
async def my_polls(user: AuthUser = Depends(auth_required)):
    cursor = db.polls.find({"hostId": user.oid}).sort("createdAt", -1)
    return [poll_out(doc) async for doc in cursor]


@router.get("/{code}", response_model=PublicPollOut)
async def get_poll_by_code(code: str):
    """Public: anyone with a room code can look up the question/options.
    Intentionally omits the host ID."""
    poll = await fetch_poll_by_code(code)
    if poll is None:
        raise HTTPException(404, "room not found")
    return PublicPollOut(
        code=poll["code"],
        question=poll["question"],
        options=options_out(poll),
        status=poll_status(poll),
        expires_at=poll["expiresAt"],
    )


@router.get("/{code}/results", response_model=ResultsPayload)
async def get_results(code: str):
    """Public live standings, served from the Redis counters."""
    poll = await fetch_poll_by_code(code)
    if poll is None:
        raise HTTPException(404, "room not found")
    return await build_results_from_redis(poll)
