from __future__ import annotations

import asyncio
from typing import Optional

from .audit_entry import AuditEntry
from .writers.types import AuditWriter, is_session_aware


class AuditSession:
    def __init__(self, writer: AuditWriter, session_id: Optional[str] = None):
        self._writer = writer
        self._session_id: Optional[str] = session_id
        self._lock = asyncio.Lock()
        self._initialized = False

        if self._session_id and is_session_aware(writer):
            writer.set_session_id(self._session_id)

    def get_session_id(self) -> Optional[str]:
        return self._session_id

    async def write_entry(self, entry: AuditEntry) -> None:
        await self._ensure_initialized()
        await self._writer.write(entry)

    async def _ensure_initialized(self) -> None:
        if self._session_id:
            return

        async with self._lock:
            # Double-check inside lock
            if self._session_id:
                return
            self._session_id = await self._writer.initialize()
            if is_session_aware(self._writer):
                self._writer.set_session_id(self._session_id)
