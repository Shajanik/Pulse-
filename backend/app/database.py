import logging

import redis.asyncio as aioredis
from pymongo import ASCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from .config import settings

log = logging.getLogger("pulse.db")

RESULTS_CHANNEL = "pulse:results"

# Populated by connect() during app startup (see main.lifespan).
mongo_client: AsyncMongoClient
database: AsyncDatabase
users: AsyncCollection
polls: AsyncCollection
votes: AsyncCollection
redis: aioredis.Redis


async def connect_mongo() -> None:
    global mongo_client, database, users, polls, votes

    # tz_aware=True so datetimes come back as UTC-aware (poll expiry math).
    mongo_client = AsyncMongoClient(
        settings.mongo_uri, tz_aware=True, serverSelectionTimeoutMS=10_000
    )
    await mongo_client.admin.command("ping")

    database = mongo_client[settings.mongo_db_name]
    users = database["users"]
    polls = database["polls"]
    votes = database["votes"]

    await users.create_index([("email", ASCENDING)], unique=True)
    await polls.create_index([("code", ASCENDING)], unique=True)
    # One vote per voter per poll: the hard backstop against duplicate voting.
    await votes.create_index([("pollId", ASCENDING), ("voterId", ASCENDING)], unique=True)

    log.info("connected to MongoDB")


async def connect_redis() -> None:
    global redis
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    await redis.ping()
    log.info("connected to Redis")


async def close() -> None:
    await redis.aclose()
    await mongo_client.close()
