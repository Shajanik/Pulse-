from dataclasses import dataclass

import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Header, HTTPException

from .security import parse_token


@dataclass
class AuthUser:
    user_id: str
    email: str

    @property
    def oid(self) -> ObjectId:
        try:
            return ObjectId(self.user_id)
        except (InvalidId, TypeError):
            raise HTTPException(401, "invalid session")


async def auth_required(authorization: str | None = Header(default=None)) -> AuthUser:
    """Protects host-only routes. Identity always comes from a verified JWT,
    never from a request body or query param."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing or invalid authorization header")
    try:
        claims = parse_token(authorization.removeprefix("Bearer "))
    except jwt.InvalidTokenError:
        raise HTTPException(401, "invalid or expired token")
    return AuthUser(user_id=claims["userId"], email=claims.get("email", ""))
