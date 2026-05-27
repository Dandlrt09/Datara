from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Optional

from models import ChatMessage
from services import CodeExecutor, FileService, LLMService


@dataclass
class SessionData:
    """Per-session state: services, messages, dashboard config.

    Each active browser session gets its own SessionData instance,
    allocated on first POST /api/session/reset and evicted after TTL.
    """

    file_service: FileService = field(default_factory=FileService)
    llm_service: LLMService = field(default_factory=LLMService)
    code_executor: Optional[CodeExecutor] = None
    chat_messages: list[ChatMessage] = field(default_factory=list)
    dashboard_items: list[dict] = field(default_factory=list)
    dashboard_filters: dict[str, list[str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time)
    last_active: float = field(default_factory=time)

    def __post_init__(self) -> None:
        """Lazy-init CodeExecutor once we have both LLMService and FileService."""
        if self.code_executor is None:
            self.code_executor = CodeExecutor(llm_service=self.llm_service)

    def touch(self) -> None:
        """Update last_active timestamp (called on every request)."""
        self.last_active = time()
