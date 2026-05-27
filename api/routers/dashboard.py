"""Dashboard router — KPI + chart items management.

Endpoints
---------
- ``GET    /api/dashboard``              → all items (with optional filter)
- ``POST   /api/dashboard``              → add an item (chart or KPI)
- ``DELETE /api/dashboard/{item_id}``    → remove an item
"""

from __future__ import annotations

from time import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_session
from api.models import DashboardItem, DashboardResponse
from api.session_data import SessionData

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_session)],
)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    session: SessionData = Depends(get_session),
    filter_col: Optional[str] = Query(None, description="Column to filter on"),
    filter_vals: Optional[str] = Query(None, description="Comma-separated filter values"),
) -> DashboardResponse:
    """Return all dashboard items.

    Optional query parameters ``filter_col`` and ``filter_vals`` are
    stored in ``dashboard_filters`` for the session so the frontend
    can re-apply them when rebuilding figures.
    """
    # Persist filter (frontend will re-render with filter applied)
    if filter_col and filter_vals:
        session.dashboard_filters[filter_col] = [v.strip() for v in filter_vals.split(",")]

    items = [
        DashboardItem(
            id=item.get("id", ""),
            title=item.get("title", "Untitled"),
            chart_type=item.get("chart_type", ""),
            figure_html=item.get("figure_html"),
            kpi_value=item.get("kpi_value"),
        )
        for item in session.dashboard_items
    ]

    return DashboardResponse(items=items)


@router.post("", status_code=201, response_model=DashboardItem)
async def add_dashboard_item(
    body: dict,
    session: SessionData = Depends(get_session),
) -> DashboardItem:
    """Add a new dashboard item.

    Expected body::

        {"file": "filename", "title": "...", "config": {...}}

    The ``config`` dict is stored as-is and can contain chart type,
    column mappings, aggregation, etc.
    """
    item_id = f"item_{int(time() * 1000)}"

    entry: dict = {
        "id": item_id,
        "title": body.get("title", "Untitled"),
        "chart_type": body.get("chart_type", ""),
        "file": body.get("file", ""),
        "config": body.get("config", {}),
    }
    session.dashboard_items.append(entry)

    return DashboardItem(
        id=item_id,
        title=entry["title"],
        chart_type=entry["chart_type"],
    )


@router.delete("/{item_id}", status_code=204)
async def delete_dashboard_item(
    item_id: str,
    session: SessionData = Depends(get_session),
) -> None:
    """Remove a dashboard item by ID.  Returns ``404`` if not found."""
    for idx, existing in enumerate(session.dashboard_items):
        if existing.get("id") == item_id:
            session.dashboard_items.pop(idx)
            return

    raise HTTPException(
        status_code=404,
        detail=f"Dashboard item '{item_id}' not found",
    )
