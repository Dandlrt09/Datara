"""Persistent configuration storage (survives server restarts).

Reads/writes ``data/config.json`` so user preferences (API key, model)
survive server restarts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigService:
    """Thin JSON persistence for runtime user config.

    Properties trigger a disk write on every set, so the file stays
    in sync with what the user last entered in Settings.
    """

    def __init__(self, config_dir: str | Path) -> None:
        self._path = Path(config_dir) / "config.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, str] = self._load()

    # ── Load / Save ──────────────────────────────────────────────

    def _load(self) -> dict[str, str]:
        if self._path.is_file():
            try:
                raw = self._path.read_text(encoding="utf-8")
                data: dict[str, str] = json.loads(raw)
                return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Corrupt config file %s: %s", self._path, exc)
        return {}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Properties ───────────────────────────────────────────────

    @property
    def api_key(self) -> str:
        return self._data.get("api_key", "")

    @api_key.setter
    def api_key(self, value: str) -> None:
        self._data["api_key"] = value
        self._save()

    def clear_api_key(self) -> None:
        """Remove the API key from persistent config entirely."""
        self._data.pop("api_key", None)
        self._save()

    @property
    def model(self) -> str:
        return self._data.get("model", "")

    @model.setter
    def model(self, value: str) -> None:
        self._data["model"] = value
        self._save()
