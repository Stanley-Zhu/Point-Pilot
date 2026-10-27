"""FastAPI entrypoint. Run from api/ with the venv active: dev (or uvicorn app.main:app --reload)"""

from fastapi import FastAPI

from app.routes import programs

app = FastAPI(title="Point Pilot API")
app.include_router(programs.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Smoke check: the server is up. Does not touch the database."""
    return {"status": "ok"}
