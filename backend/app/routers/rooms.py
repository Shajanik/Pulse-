import uuid
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pymongo.errors import DuplicateKeyError

from .. import database as db
from ..results import (
    build_results_from_redis,
    fetch_poll_by_code,
    redis_count_key,
    redis_total_key,
)
from ..schemas import (
    CastVoteRequest,
    JoinOut,
    JoinRequest,
    VoteOut,
    is_expired,
    options_out,
)

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("/{code}/join", response_model=JoinOut)
async def join_room(code: str, req: JoinRequest | None = None):
    """Validates the room and hands the audience member a fresh anonymous
    voterId. No account is created; the client holds on to the id."""
    nickname = (req.nickname if req else "").strip()
    if not nickname:
        raise HTTPException(400, "nickname is required")
    nickname = nickname[:24]

    poll = await fetch_poll_by_code(code)
    if poll is None:
        raise HTTPException(404, "room not found")
    if is_expired(poll):
        raise HTTPException(410, "this poll has expired")

    return JoinOut(
        voter_id=str(uuid.uuid4()),
        nickname=nickname,
        code=poll["code"],
        question=poll["question"],
        options=options_out(poll),
        expires_at=poll["expiresAt"],
    )


@router.post("/{code}/vote", response_model=VoteOut)
async def cast_vote(code: str, req: CastVoteRequest):
    """validate -> permanent MongoDB write -> Redis INCR live counters ->
    Redis PUBLISH -> (subscriber task) -> WebSocket broadcast."""
    if not req.voter_id or not req.option_id:
        raise HTTPException(400, "voterId and optionId are required")

    poll = await fetch_poll_by_code(code)
    if poll is None:
        raise HTTPException(404, "room not found")
    if is_expired(poll):
        raise HTTPException(410, "this poll has expired")

    try:
        option_oid = ObjectId(req.option_id)
    except (InvalidId, TypeError):
        raise HTTPException(400, "invalid option")

    # Server-side check: the option must actually belong to this poll.
    if not any(o["id"] == option_oid for o in poll["options"]):
        raise HTTPException(400, "that option does not belong to this poll")

    # 1. Permanent write. The unique (pollId, voterId) index is what actually
    #    stops duplicate votes, not just app logic.
    try:
        await db.votes.insert_one(
            {
                "pollId": poll["_id"],
                "optionId": option_oid,
                "voterId": req.voter_id,
                "nickname": req.nickname.strip(),
                "createdAt": datetime.now(timezone.utc),
            }
        )
    except DuplicateKeyError:
        raise HTTPException(409, "you have already voted in this poll")

    # 2. Redis INCR: live counters.
    try:
        async with db.redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_count_key(poll["code"], str(option_oid)))
            pipe.incr(redis_total_key(poll["code"]))
            await pipe.execute()
    except Exception:
        raise HTTPException(500, "failed to update live counter")

    # 3. Publish fresh standings. The subscriber task pushes them out over
    #    WebSocket; this handler never touches the hub. The vote is already
    #    durably stored, so a publish failure only delays the live update.
    payload = await build_results_from_redis(poll)
    try:
        await db.redis.publish(db.RESULTS_CHANNEL, payload.model_dump_json(by_alias=True))
    except Exception:
        pass

    return VoteOut()
