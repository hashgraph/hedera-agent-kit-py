from __future__ import annotations

from abc import ABC, abstractmethod

from ..audit_entry import AuditEntry


class AuditWriter(ABC):
    """Base interface for audit writers."""

    @abstractmethod
    async def initialize(self) -> str:
        """One-time setup: create resources (e.g. registry topic). Returns session identifier."""
        ...

    @abstractmethod
    async def write(self, entry: AuditEntry) -> None:
        """Write a single audit entry."""
        ...


class SessionAwareWriter(AuditWriter):
    """An AuditWriter that can receive a session ID."""

    @abstractmethod
    def set_session_id(self, session_id: str) -> None: ...


def is_session_aware(writer: AuditWriter) -> bool:
    return hasattr(writer, "set_session_id")
