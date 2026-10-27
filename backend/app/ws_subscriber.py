import asyncio
import json
import logging

from . import database as db
from .ws_hub import hub

log = logging.getLogger("pulse.ws")


async def run_redis_subscriber() -> None:
    """The "server receives Redis event" leg of the real-time pipeline.

    Subscribes to the shared results channel and forwards every published
    payload to the right WebSocket room. Vote handlers never touch the hub:
    they only publish to Redis, which also makes this work with several
    server workers (each worker relays to its own connected clients).
    Reconnects with a short backoff if the Redis connection drops.
    """
    while True:
        pubsub = db.redis.pubsub()
        try:
            await pubsub.subscribe(db.RESULTS_CHANNEL)
            log.info("redis subscriber listening on %s", db.RESULTS_CHANNEL)
            async for msg in pubsub.listen():
                if msg["type"] != "message":
                    continue
                try:
                    code = json.loads(msg["data"])["code"]
                except (ValueError, KeyError, TypeError):
                    log.warning("failed to parse results payload")
                    continue
                await hub.broadcast(code, msg["data"])
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("redis subscriber error; retrying in 1s")
            await asyncio.sleep(1)
        finally:
            try:
                await pubsub.aclose()
            except Exception:
                pass
