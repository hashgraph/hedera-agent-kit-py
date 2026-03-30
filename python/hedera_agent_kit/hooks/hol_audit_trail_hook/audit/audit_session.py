from __future__ import annotations

from .audit_entry import AuditEntry
from .writers.types import AuditWriter, is_session_aware


class AuditSession:
    def __init__(self, writer: AuditWriter, session_id: str):
        self._writer = writer
        self._session_id: str = session_id

        if is_session_aware(writer):
            writer.set_session_id(self._session_id)

    def get_session_id(self) -> str:
        return self._session_id

    async def write_entry(self, entry: AuditEntry) -> None:
        await self._writer.write(entry)
