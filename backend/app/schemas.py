from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

PollStatus = Literal["active", "expired"]


class CamelModel(BaseModel):
    """snake_case in Python, camelCase on the wire (matches the frontend)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---- requests ---------------------------------------------------------------
# Fields default to empty so the handlers can return the same specific
# validation messages the Go backend did ("a valid email is required", ...).


class Credentials(CamelModel):
    email: str = ""
    password: str = ""


class CreatePollRequest(CamelModel):
    question: str = ""
    options: list[str] = []
    expires_in_minutes: int = 0


class JoinRequest(CamelModel):
    nickname: str = ""


class CastVoteRequest(CamelModel):
    option_id: str = ""
    voter_id: str = ""
    nickname: str = ""


# ---- responses --------------------------------------------------------------


class OptionOut(CamelModel):
    id: str
    text: str


class TokenOut(CamelModel):
    token: str
    email: str


class MeOut(CamelModel):
    user_id: str
    email: str


class PollOut(CamelModel):
    id: str
    host_id: str
    code: str
    question: str
    options: list[OptionOut]
    created_at: datetime
    expires_at: datetime


class PublicPollOut(CamelModel):
    code: str
    question: str
    options: list[OptionOut]
    status: PollStatus
    expires_at: datetime


class JoinOut(CamelModel):
    voter_id: str
    nickname: str
    code: str
    question: str
    options: list[OptionOut]
    expires_at: datetime


class OptionTally(CamelModel):
    id: str
    text: str
    votes: int
    percentage: float


class ResultsPayload(CamelModel):
    type: Literal["results"] = "results"
    code: str
    question: str
    options: list[OptionTally]
    total_votes: int
    status: PollStatus
    crowd_pulse: str


class VoteOut(CamelModel):
    success: bool = True


# ---- helpers for raw Mongo poll documents -----------------------------------


def is_expired(poll: dict) -> bool:
    return datetime.now(timezone.utc) > poll["expiresAt"]


def poll_status(poll: dict) -> PollStatus:
    return "expired" if is_expired(poll) else "active"


def options_out(poll: dict) -> list[OptionOut]:
    return [OptionOut(id=str(o["id"]), text=o["text"]) for o in poll["options"]]


def poll_out(poll: dict) -> PollOut:
    return PollOut(
        id=str(poll["_id"]),
        host_id=str(poll["hostId"]),
        code=poll["code"],
        question=poll["question"],
        options=options_out(poll),
        created_at=poll["createdAt"],
        expires_at=poll["expiresAt"],
    )
