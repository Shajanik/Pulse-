import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import database as db
from .config import settings
from .routers import auth, polls, rooms, ws
from .ws_subscriber import run_redis_subscriber

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pulse")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect_mongo()
    await db.connect_redis()
    subscriber = asyncio.create_task(run_redis_subscriber())
    log.info("Pulse backend ready")
    try:
        yield
    finally:
        subscriber.cancel()
        await asyncio.gather(subscriber, return_exceptions=True)
        await db.close()


app = FastAPI(title="Pulse", lifespan=lifespan)

# The frontend reads `body.error`, so keep the Go backend's error shape
# instead of FastAPI's default {"detail": ...}.


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, __: RequestValidationError):
    return JSONResponse({"error": "invalid request body"}, status_code=400)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Origin", "Content-Type", "Authorization"],
    allow_credentials=True,
)


@app.get("/")
async def root():
    return {"message": "Pulse backend is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(polls.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(ws.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port)
