"""Settings router — LLM configuration.

Endpoints
---------
- ``GET /api/settings``  → current LLM config
- ``PUT /api/settings``  → update API key and/or model
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.dependencies import get_session
from api.models import SettingsRequest, SettingsResponse
from api.session_data import SessionData
from api.session_store import SessionStore
from services import CodeExecutor

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(get_session)],
)


@router.get("", response_model=SettingsResponse)
async def get_settings(
    session: SessionData = Depends(get_session),
) -> SettingsResponse:
    """Return the current LLM provider, model, and configuration status."""
    llm = session.llm_service
    return SettingsResponse(
        model=llm.model,
        provider=llm.provider_info,
        is_configured=llm.is_configured,
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsRequest,
    request: Request,
    session: SessionData = Depends(get_session),
) -> SettingsResponse:
    """Update the LLM API key and/or model.

    A new ``CodeExecutor`` is built with the updated ``LLMService``
    so that subsequent chat calls use the new configuration.

    Changes are also saved as **global defaults** in the SessionStore
    so they survive session resets (archive, restore, refresh).
    """
    llm = session.llm_service
    store: SessionStore = request.app.state.store

    if body.api_key is not None:
        llm.api_key = body.api_key
        llm._client = None  # force lazy-rebuild on next access
        store.set_global_api_key(body.api_key)

    if body.model is not None:
        llm.model = body.model
        store.set_global_model(body.model)

    # Rebuild executor with the updated LLM
    session.code_executor = CodeExecutor(llm_service=llm)

    return SettingsResponse(
        model=llm.model,
        provider=llm.provider_info,
        is_configured=llm.is_configured,
    )
