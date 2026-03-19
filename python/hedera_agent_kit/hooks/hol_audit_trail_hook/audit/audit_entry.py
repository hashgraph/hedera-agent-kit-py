from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel

from .constants import (
    HOL_AUDIT_ENTRY_SOURCE,
    HOL_AUDIT_ENTRY_TYPE,
    HOL_AUDIT_ENTRY_VERSION,
)


class AuditEntryResult(BaseModel):
    raw: Dict[str, Any] = {}
    message: Optional[str] = None


class AuditEntry(BaseModel):
    type: Literal["hedera-agent-kit:audit-entry"] = HOL_AUDIT_ENTRY_TYPE
    version: Literal["1.0"] = HOL_AUDIT_ENTRY_VERSION
    source: str = HOL_AUDIT_ENTRY_SOURCE
    timestamp: str
    tool: str
    params: Dict[str, Any] = {}
    result: AuditEntryResult = AuditEntryResult()


def build_audit_entry(
    tool: str,
    params: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
) -> AuditEntry:
    result_raw = {}
    result_message = None

    if result is not None:
        result_raw = result.get("raw") or {}
        result_message = result.get("message")

    return AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        tool=tool,
        params=params or {},
        result=AuditEntryResult(raw=result_raw, message=result_message),
    )
