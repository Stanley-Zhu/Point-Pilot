"""Command-line entry points, registered under [project.scripts] in pyproject.toml."""

import uvicorn

def dev() -> None:
    """Run the API with auto-reload. Usage: dev"""
    uvicorn.run("app.main:app", reload=True)