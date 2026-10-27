import asyncio
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

TOKEN_TTL = timedelta(days=7)
ALGORITHM = "HS256"


def generate_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    # Same claim names as the Go backend, so previously issued tokens stay valid.
    return jwt.encode(
        {"userId": user_id, "email": email, "iat": now, "exp": now + TOKEN_TTL},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


def parse_token(token: str) -> dict:
    """Return the claims, or raise jwt.InvalidTokenError."""
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    if not claims.get("userId"):
        raise jwt.InvalidTokenError("missing userId")
    return claims


# bcrypt is CPU-bound, so run it off the event loop.
async def hash_password(plain: str) -> str:
    return await asyncio.to_thread(
        lambda: bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    )


async def check_password(hashed: str, plain: str) -> bool:
    def _check() -> bool:
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except ValueError:
            return False

    return await asyncio.to_thread(_check)
