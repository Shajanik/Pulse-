import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import settings
from ..results import fetch_poll_by_code
from ..ws_hub import hub

log = logging.getLogger("pulse.ws")
router = APIRouter()

_ALLOWED_ORIGINS = set(settings.allowed_origins)


@router.websocket("/ws/room/{code}")
async def room_socket(ws: WebSocket, code: str):
    """Joins the caller to the room identified by the code. Expired rooms can
    still be watched (late viewers see final results); votes are blocked
    separately in cast_vote."""
    poll = await fetch_poll_by_code(code)
    origin = ws.headers.get("origin")
    if poll is None or (origin and origin not in _ALLOWED_ORIGINS):
        # Closing before accept() rejects the handshake (HTTP 403).
        await ws.close(code=1008)
        return

    await ws.accept()
    room = poll["code"]
    hub.register(room, ws)
    try:
        # Broadcast-only: keep reading (and discarding) so we notice disconnects.
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.info("ws closed: %r", exc)
    finally:
        hub.unregister(room, ws)
