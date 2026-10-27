import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

# The production frontend is always allowed, even if ALLOWED_ORIGINS forgets it.
PRODUCTION_FRONTEND = "https://pulse-live-poll.vercel.app"


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db_name: str
    redis_url: str
    jwt_secret: str
    port: int
    allowed_origins: list[str]


def _env(key: str, fallback: str = "") -> str:
    value = os.environ.get(key, "")
    return value if value else fallback


def load_settings() -> Settings:
    # Fine if .env doesn't exist (e.g. in production on Render).
    load_dotenv()

    missing = [k for k in ("MONGODB_URI", "REDIS_URL", "JWT_SECRET") if not _env(k)]
    if missing:
        sys.exit(f"missing required environment variable(s): {', '.join(missing)}")

    origins = [
        o.strip()
        for o in _env("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    if PRODUCTION_FRONTEND not in origins:
        origins.append(PRODUCTION_FRONTEND)

    return Settings(
        mongo_uri=_env("MONGODB_URI"),
        mongo_db_name=_env("MONGODB_DB_NAME", "pulse"),
        redis_url=_env("REDIS_URL"),
        jwt_secret=_env("JWT_SECRET"),
        port=int(_env("PORT", "8080")),
        allowed_origins=origins,
    )


settings = load_settings()
