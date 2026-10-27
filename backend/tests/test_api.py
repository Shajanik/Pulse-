"""End-to-end tests against a real MongoDB + Redis (see README / CI setup).

Run:  MONGODB_URI=... REDIS_URL=... JWT_SECRET=... pytest -q
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")
os.environ["MONGODB_DB_NAME"] = f"pulse_test_{uuid.uuid4().hex[:8]}"

from app.main import app  # noqa: E402
from app import database as db  # noqa: E402

ORIGIN = "http://localhost:5173"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
        c.portal.call(db.mongo_client.drop_database, os.environ["MONGODB_DB_NAME"])
        c.portal.call(db.redis.flushdb)


@pytest.fixture(scope="module")
def host(client):
    r = client.post("/api/auth/signup", json={"email": " Host@Example.com ", "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def poll(client, host):
    r = client.post("/api/polls", headers=host,
                    json={"question": "Tabs or spaces?", "options": ["Tabs", " Spaces ", ""], "expiresInMinutes": 15})
    assert r.status_code == 201, r.text
    return r.json()


# ---- misc / error shape ------------------------------------------------------

def test_root_and_health(client):
    assert client.get("/").json() == {"message": "Pulse backend is running"}
    assert client.get("/health").json() == {"status": "ok"}


def test_errors_use_error_key_not_detail(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and "error" in r.json()
    r = client.post("/api/auth/login", content="not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400 and r.json() == {"error": "invalid request body"}


def test_cors(client):
    r = client.options("/api/polls", headers={
        "Origin": ORIGIN, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,authorization"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == ORIGIN
    assert r.headers["access-control-allow-credentials"] == "true"
    r = client.options("/api/polls", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
    r = client.get("/health", headers={"Origin": "https://pulse-live-poll.vercel.app"})
    assert r.headers["access-control-allow-origin"] == "https://pulse-live-poll.vercel.app"


# ---- auth --------------------------------------------------------------------

def test_signup_validation_and_duplicate(client, host):
    assert client.post("/api/auth/signup", json={"email": "nope", "password": "password123"}).json() == {"error": "a valid email is required"}
    assert client.post("/api/auth/signup", json={"email": "a@b.co", "password": "short"}).json() == {"error": "password must be at least 8 characters"}
    r = client.post("/api/auth/signup", json={"email": "host@example.com", "password": "password123"})
    assert r.status_code == 409 and r.json() == {"error": "an account with that email already exists"}


def test_login_and_me(client):
    r = client.post("/api/auth/login", json={"email": "HOST@example.com", "password": "password123"})
    assert r.status_code == 200 and r.json()["email"] == "host@example.com"
    token = r.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "host@example.com" and len(me["userId"]) == 24
    bad = client.post("/api/auth/login", json={"email": "host@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401 and bad.json() == {"error": "invalid email or password"}
    unknown = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "password123"})
    assert unknown.status_code == 401 and unknown.json() == bad.json()


def test_auth_required(client):
    assert client.get("/api/auth/me").json() == {"error": "missing or invalid authorization header"}
    r = client.get("/api/polls/mine", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and r.json() == {"error": "invalid or expired token"}


def test_go_compatible_bcrypt_hash_and_token(client):
    """Users/tokens created by the old Go backend must keep working."""
    import bcrypt, jwt, time
    from bson import ObjectId
    oid = ObjectId()
    # Go's bcrypt emits $2a$ hashes
    h = bcrypt.hashpw(b"gopassword1", bcrypt.gensalt(prefix=b"2a")).decode()
    assert h.startswith("$2a$")
    client.portal.call(db.users.insert_one, {"_id": oid, "email": "go@example.com", "passwordHash": h})
    assert client.post("/api/auth/login", json={"email": "go@example.com", "password": "gopassword1"}).status_code == 200
    tok = jwt.encode({"userId": str(oid), "email": "go@example.com", "exp": int(time.time()) + 600}, os.environ["JWT_SECRET"], algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["userId"] == str(oid)


# ---- polls -------------------------------------------------------------------

def test_create_poll_shape(poll):
    assert set(poll) == {"id", "hostId", "code", "question", "options", "createdAt", "expiresAt"}
    assert len(poll["code"]) == 6 and poll["code"].isdigit()
    assert [o["text"] for o in poll["options"]] == ["Tabs", "Spaces"]
    assert all(len(o["id"]) == 24 for o in poll["options"])


def test_create_poll_validation(client, host):
    def post(body):
        r = client.post("/api/polls", headers=host, json=body)
        return r.status_code, r.json()
    assert post({"question": " ", "options": ["a", "b"], "expiresInMinutes": 5}) == (400, {"error": "question cannot be empty"})
    assert post({"question": "q", "options": ["a"], "expiresInMinutes": 5}) == (400, {"error": "a poll needs 2 to 4 non-empty options"})
    assert post({"question": "q", "options": list("abcde"), "expiresInMinutes": 5})[0] == 400
    assert post({"question": "q", "options": ["a", "b"], "expiresInMinutes": 10}) == (400, {"error": "expiration must be 5, 15, or 30 minutes"})
    assert client.post("/api/polls", json={}).status_code == 401


def test_get_poll_public(client, poll):
    r = client.get(f"/api/polls/{poll['code']}")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"code", "question", "options", "status", "expiresAt"}  # no hostId leak
    assert body["status"] == "active"
    r = client.get("/api/polls/000000x")
    assert r.status_code == 404 and r.json() == {"error": "room not found"}


def test_my_polls_sorted_and_scoped(client, host, poll):
    r2 = client.post("/api/polls", headers=host, json={"question": "Second", "options": ["x", "y"], "expiresInMinutes": 5}).json()
    mine = client.get("/api/polls/mine", headers=host).json()
    assert [p["id"] for p in mine][:2] == [r2["id"], poll["id"]]  # newest first
    other = client.post("/api/auth/signup", json={"email": "other@example.com", "password": "password123"}).json()["token"]
    assert client.get("/api/polls/mine", headers={"Authorization": f"Bearer {other}"}).json() == []


# ---- join / vote / results / websocket --------------------------------------

def test_join_validation(client, poll):
    code = poll["code"]
    assert client.post(f"/api/rooms/{code}/join", json={}).json() == {"error": "nickname is required"}
    assert client.post(f"/api/rooms/{code}/join").json() == {"error": "nickname is required"}
    assert client.post("/api/rooms/999999/join", json={"nickname": "x"}).status_code == 404
    j = client.post(f"/api/rooms/{code}/join", json={"nickname": "n" * 40}).json()
    assert len(j["nickname"]) == 24 and len(j["voterId"]) == 36
    assert set(j) == {"voterId", "nickname", "code", "question", "options", "expiresAt"}


def test_vote_flow_results_and_websocket(client, poll):
    code = poll["code"]
    a, b = poll["options"][0]["id"], poll["options"][1]["id"]

    r = client.get(f"/api/polls/{code}/results").json()
    assert r["totalVotes"] == 0 and r["crowdPulse"] == "Waiting for the first vote..." and r["type"] == "results"

    with client.websocket_connect(f"/ws/room/{code}", headers={"Origin": ORIGIN}) as ws1, \
         client.websocket_connect(f"/ws/room/{code}") as ws2:  # no Origin header is allowed
        v1 = str(uuid.uuid4())
        assert client.post(f"/api/rooms/{code}/vote", json={"optionId": a, "voterId": v1, "nickname": "Ann"}).json() == {"success": True}

        # Pub/Sub -> subscriber -> hub -> both sockets
        for ws in (ws1, ws2):
            msg = ws.receive_json()
            assert msg["type"] == "results" and msg["code"] == code
            assert msg["totalVotes"] == 1
            assert msg["options"][0] == {"id": a, "text": "Tabs", "votes": 1, "percentage": 100.0}
            assert msg["crowdPulse"] == "Tabs is dominating!"

        # duplicate vote -> 409 and no extra count
        dup = client.post(f"/api/rooms/{code}/vote", json={"optionId": b, "voterId": v1})
        assert dup.status_code == 409 and dup.json() == {"error": "you have already voted in this poll"}

        client.post(f"/api/rooms/{code}/vote", json={"optionId": b, "voterId": "v2"})
        msg = ws1.receive_json()
        assert msg["totalVotes"] == 2 and msg["options"][1]["percentage"] == 50.0
        assert msg["crowdPulse"] == "The crowd is divided!"

    final = client.get(f"/api/polls/{code}/results").json()
    assert final["totalVotes"] == 2

    # Mongo fallback path agrees with Redis counters
    from app.results import build_results_from_mongo
    doc = client.portal.call(db.polls.find_one, {"code": code})
    m = client.portal.call(build_results_from_mongo, doc)
    assert [o.votes for o in m.options] == [o["votes"] for o in final["options"]]


def test_vote_validation(client, poll):
    code = poll["code"]
    opt = poll["options"][0]["id"]
    assert client.post(f"/api/rooms/{code}/vote", json={"optionId": opt}).json() == {"error": "voterId and optionId are required"}
    assert client.post(f"/api/rooms/{code}/vote", json={"optionId": "zzz", "voterId": "q"}).json() == {"error": "invalid option"}
    other = "a" * 24
    assert client.post(f"/api/rooms/{code}/vote", json={"optionId": other, "voterId": "q"}).json() == {"error": "that option does not belong to this poll"}
    assert client.post("/api/rooms/000001/vote", json={"optionId": opt, "voterId": "q"}).status_code == 404


def test_ws_rejections(client, poll):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/room/424242"):
            pass
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/room/{poll['code']}", headers={"Origin": "https://evil.example"}):
            pass


def test_expired_poll_blocks_join_and_vote_but_results_work(client, poll, host):
    from datetime import datetime, timedelta, timezone
    code = poll["code"]
    client.portal.call(db.polls.update_one, {"code": code}, {"$set": {"expiresAt": datetime.now(timezone.utc) - timedelta(seconds=1)}})
    assert client.post(f"/api/rooms/{code}/join", json={"nickname": "late"}).status_code == 410
    r = client.post(f"/api/rooms/{code}/vote", json={"optionId": poll["options"][0]["id"], "voterId": "late"})
    assert r.status_code == 410 and r.json() == {"error": "this poll has expired"}
    assert client.get(f"/api/polls/{code}").json()["status"] == "expired"
    assert client.get(f"/api/polls/{code}/results").json()["status"] == "expired"


# ---- crowd pulse unit tests --------------------------------------------------

def test_crowd_pulse_rules():
    from app.utils import crowd_pulse_message as m
    assert m(["A", "B"], [0, 0]) == "Waiting for the first vote..."
    assert m(["A", "B"], [8, 2]) == "A is dominating!"        # gap 60
    assert m(["A", "B", "C"], [5, 4, 4]) == "The crowd is divided!"   # spread < 15
    assert m(["A", "B", "C"], [10, 8, 2]) == "It's getting competitive!"
    assert m(["A"], [3]) == "A is dominating!"
