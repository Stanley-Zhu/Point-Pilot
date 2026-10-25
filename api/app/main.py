"""FastAPI entrypoint. Run from api/ with: uv run uvicorn app.main:app --reload"""

from fastapi import FastAPI

app = FastAPI(title="Point Pilot API")


@app.get("/health")
def health() -> dict[str, str]:
    """Smoke check: the server is up. Does not touch the database."""
    return {"status": "ok"}
