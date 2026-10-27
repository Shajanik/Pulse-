import asyncio
import logging

from fastapi import WebSocket

log = logging.getLogger("pulse.ws")


class Hub:
    """Tracks which WebSocket connections belong to which room (poll code) and
    fans out broadcast messages to everyone in that room."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}

    def register(self, code: str, ws: WebSocket) -> None:
        self._rooms.setdefault(code, set()).add(ws)

    def unregister(self, code: str, ws: WebSocket) -> None:
        conns = self._rooms.get(code)
        if conns is None:
            return
        conns.discard(ws)
        if not conns:
            del self._rooms[code]

    async def broadcast(self, code: str, message: str) -> None:
        conns = list(self._rooms.get(code, ()))
        if not conns:
            return

        async def send(ws: WebSocket) -> None:
            try:
                await asyncio.wait_for(ws.send_text(message), timeout=5)
            except Exception as exc:  # dead or too-slow client: drop it
                log.info("ws write error, dropping client: %r", exc)
                self.unregister(code, ws)

        await asyncio.gather(*(send(ws) for ws in conns))


hub = Hub()
