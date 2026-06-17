"""Datara — FastAPI backend serving screens + REST API."""

from __future__ import annotations

import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

from dotenv import load_dotenv  # noqa: E402 — must load .env before any import reads env vars
load_dotenv()  # ← ANTES de cualquier import que lea env vars

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import HTMLResponse, RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from api.routers import api_router  # noqa: E402
from api.session_store import SessionStore  # noqa: E402
from services.archive_service import ArchiveService  # noqa: E402
from services.config_service import ConfigService  # noqa: E402


_HERE = Path(__file__).resolve().parent
_FRONTEND = _HERE.parent / "frontend"
_SCREENS = _FRONTEND / "screens"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── User config directory ─────────────────────────────────────
    config_dir = Path(os.getenv("CONFIG_DIR", str(_HERE.parent / "data")))
    config_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Config directory: %s", config_dir)
    config_service = ConfigService(config_dir)

    app.state.store = SessionStore(config_service=config_service)

    # ── Archive service ────────────────────────────────────────────
    archive_dir = Path(os.getenv("ARCHIVE_DIR", str(_HERE.parent / "archives")))
    app.state.archive_service = ArchiveService(archive_dir)
    logger.info("Archive directory: %s", archive_dir)

    # ── Uploads directory ──────────────────────────────────────────
    uploads_dir = Path(os.getenv("UPLOADS_DIR", str(_HERE.parent / "uploads")))
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.state.uploads_dir = uploads_dir
    logger.info("Uploads directory: %s", uploads_dir)

    yield
    app.state.config_service = None
    app.state.store = None
    app.state.archive_service = None


def _serve_screen(screen_name: str) -> HTMLResponse:
    """Serve a Stitch screen as a standalone page on a dark background."""
    path = _SCREENS / f"{screen_name}.html"
    if not path.is_file():
        return HTMLResponse("<h1>Screen not found</h1>", status_code=404)

    full = path.read_text(encoding="utf-8")

    # Extract <head> (Tailwind CDN + design tokens + fonts)
    h = re.search(r"<head>(.*?)</head>", full, re.DOTALL)
    head_content = h.group(1) if h else ""

    # Extract <body> content
    b = re.search(r"<body[^>]*>(.*?)</body>", full, re.DOTALL)
    body_content = b.group(1) if b else full

    return HTMLResponse(f"""<!DOCTYPE html>
<html class="dark" lang="es">
<head>
{head_content}
  <style>
    body {{
      background-color: #0D1117;
      margin: 0;
      padding: 0;
      min-height: 100vh;
      font-family: 'Geist', sans-serif;
    }}
  </style>
</head>
<body>
{body_content}
</body>
</html>""")


def create_app() -> FastAPI:
    app = FastAPI(title="Datara API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Session-Id"],
    )

    app.include_router(api_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "datara-api"}

    if _FRONTEND.is_dir():
        app.mount("/static", StaticFiles(directory=str(_FRONTEND)), name="static")

        # ── Serve Screens ────────────────────────────────────────
        @app.get("/", response_class=RedirectResponse)
        async def root():
            return RedirectResponse(url="/upload")

        @app.get("/upload", response_class=HTMLResponse)
        async def upload_page():
            return _serve_screen("upload")

        @app.get("/chat", response_class=HTMLResponse)
        async def chat_page():
            return _serve_screen("chat")

        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard_page():
            return _serve_screen("dashboard")

        @app.get("/settings", response_class=HTMLResponse)
        async def settings_page():
            return _serve_screen("settings")

    return app


app = create_app()
