"""Aggregate all routers into a single ``api_router``.

Usage::

    from api.routers import api_router
    app.include_router(api_router)
"""

from fastapi import APIRouter

from .archive import router as archive_router
from .chat import router as chat_router
from .dashboard import router as dashboard_router
from .export import router as export_router
from .files import router as files_router
from .session import router as session_router
from .settings import router as settings_router

api_router = APIRouter()

api_router.include_router(session_router)
api_router.include_router(files_router)
api_router.include_router(chat_router)
api_router.include_router(dashboard_router)
api_router.include_router(settings_router)
api_router.include_router(export_router)
api_router.include_router(archive_router)

__all__ = ["api_router"]
