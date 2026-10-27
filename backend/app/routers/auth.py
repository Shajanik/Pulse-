from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone

from .. import database as db
from ..deps import AuthUser, auth_required
from ..schemas import Credentials, MeOut, TokenOut
from ..security import check_password, generate_token, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=201, response_model=TokenOut)
async def signup(req: Credentials):
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "a valid email is required")
    if len(req.password) < 8:
        raise HTTPException(400, "password must be at least 8 characters")
    if len(req.password.encode()) > 72:  # bcrypt's hard limit
        raise HTTPException(400, "password must be at most 72 bytes")

    hashed = await hash_password(req.password)
    try:
        res = await db.users.insert_one(
            {"email": email, "passwordHash": hashed, "createdAt": datetime.now(timezone.utc)}
        )
    except DuplicateKeyError:
        raise HTTPException(409, "an account with that email already exists")

    return TokenOut(token=generate_token(str(res.inserted_id), email), email=email)


@router.post("/login", response_model=TokenOut)
async def login(req: Credentials):
    email = req.email.strip().lower()
    user = await db.users.find_one({"email": email})

    # Same generic error for "no such user" and "wrong password" so we don't
    # leak which emails are registered.
    if user is None or not await check_password(user["passwordHash"], req.password):
        raise HTTPException(401, "invalid email or password")

    return TokenOut(token=generate_token(str(user["_id"]), user["email"]), email=user["email"])


@router.get("/me", response_model=MeOut)
async def me(user: AuthUser = Depends(auth_required)):
    return MeOut(user_id=user.user_id, email=user.email)
