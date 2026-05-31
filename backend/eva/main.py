from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .api.websocket import websocket_router
from .core.config import load_project_env, load_settings
from .memory.store import MemoryStore


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"


def create_app() -> FastAPI:
    load_project_env(ROOT)
    settings = load_settings(ROOT / "config" / "eva.toml")
    app = FastAPI(title="Eva Agent", version="0.1.0")
    app.state.settings = settings
    app.state.memory = MemoryStore(ROOT / "data" / "eva.sqlite3")
    app.include_router(router, prefix="/api")
    app.include_router(websocket_router)
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()
