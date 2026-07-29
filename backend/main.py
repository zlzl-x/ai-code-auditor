from __future__ import annotations

from pathlib import Path

from backend.core.env import load_env_file
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router
from backend.core.env import load_env_file
from backend.core.path_validation import get_repo_root
from backend.models.database import init_db

env_path = get_repo_root() / ".env"
load_env_file()

app = FastAPI(title="AI Code Auditor", version="0.1.0")
app.include_router(router)

frontend_dir = get_repo_root() / "frontend"
if frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def create_app() -> FastAPI:
    return app
