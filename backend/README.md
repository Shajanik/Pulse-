# Pulse backend (FastAPI)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in MONGODB_URI, REDIS_URL, JWT_SECRET
uvicorn app.main:app --reload --port 8080
```

Interactive API docs: http://localhost:8080/docs

**Render:** build command `pip install -r requirements.txt`,
start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

**Tests** (need a local MongoDB and Redis running):
`pip install pytest httpx && pytest -q`
