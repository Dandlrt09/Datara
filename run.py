#!/usr/bin/env python3
"""Uvicorn entry point for the FastAPI backend.

Usage:
    python run.py
"""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
