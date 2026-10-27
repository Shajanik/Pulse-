from . import database as db
from .schemas import OptionTally, ResultsPayload, poll_status
from .utils import crowd_pulse_message


def redis_count_key(code: str, option_id: str) -> str:
    return f"pulse:{code}:option:{option_id}"


def redis_total_key(code: str) -> str:
    return f"pulse:{code}:total"


def _payload(poll: dict, counts: list[int]) -> ResultsPayload:
    total = sum(counts)
    tallies = [
        OptionTally(
            id=str(opt["id"]),
            text=opt["text"],
            votes=n,
            percentage=(n / total * 100) if total else 0.0,
        )
        for opt, n in zip(poll["options"], counts)
    ]
    return ResultsPayload(
        code=poll["code"],
        question=poll["question"],
        options=tallies,
        total_votes=total,
        status=poll_status(poll),
        crowd_pulse=crowd_pulse_message([o["text"] for o in poll["options"]], counts),
    )


async def build_results_from_redis(poll: dict) -> ResultsPayload:
    """Fast path: read the live counters out of Redis."""
    keys = [redis_count_key(poll["code"], str(o["id"])) for o in poll["options"]]
    raw = await db.redis.mget(keys)
    counts = [int(v) if v is not None else 0 for v in raw]  # unset key == zero votes
    return _payload(poll, counts)


async def build_results_from_mongo(poll: dict) -> ResultsPayload:
    """Recompute tallies from the permanent vote records (MongoDB is the
    source of truth). Not used by any route today, same as in the Go version;
    handy as a fallback if Redis is ever flushed."""
    cursor = await db.votes.aggregate(
        [
            {"$match": {"pollId": poll["_id"]}},
            {"$group": {"_id": "$optionId", "count": {"$sum": 1}}},
        ]
    )
    by_option = {str(row["_id"]): row["count"] async for row in cursor}
    counts = [by_option.get(str(o["id"]), 0) for o in poll["options"]]
    return _payload(poll, counts)


async def fetch_poll_by_code(code: str) -> dict | None:
    return await db.polls.find_one({"code": code})
