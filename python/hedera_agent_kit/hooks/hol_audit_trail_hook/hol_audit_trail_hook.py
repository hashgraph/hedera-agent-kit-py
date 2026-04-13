from __future__ import annotations

import re
from typing import Any, List, Optional

from hedera_agent_kit.shared.hook import (
    AbstractHook,
    PostSecondaryActionParams,
    PreToolExecutionParams,
)
from ..utils import stringify_recursive
from hedera_agent_kit.shared.configuration import AgentMode, Context
from .audit.audit_entry import build_audit_entry
from .audit.audit_session import AuditSession
from .audit.writers.hol_audit_writer import HolAuditWriter

SESSION_ID_PATTERN = re.compile(r"^0\.0\.\d+$")


class HolAuditTrailHook(AbstractHook):
    """
    Hook that writes HOL-standards-compliant audit trails to an HCS session topic.

    Uses an HCS-2 INDEXED registry as the session topic to list audit entries.
    Delegates to AuditSession + HolAuditWriter for all write operations.
    """

    def __init__(
        self,
        relevant_tools: List[str],
        session_id: str,
    ):
        """
        Args:
            relevant_tools: List of tool names that trigger audit trail logging.
            session_id: Hedera topic ID (format ``0.0.xxx``) used as the audit session registry.
                The topic should be created with memo ``hcs-2:0:0`` to be fully compliant
                with the HCS-2 standard. See https://hol.org/docs/standards/hcs-2/
        """
        if not SESSION_ID_PATTERN.match(session_id):
            raise ValueError(
                "session_id must be a valid Hedera topic ID in format 0.0.xxx"
            )
        self._relevant_tools = relevant_tools
        self._name = "HOL Audit Trail Hook"
        self._description = "Hook to add HOL-standards-compliant audit trail to HCS topics. Available only in Agent Mode AUTONOMOUS."
        self._session_id = session_id
        self._session: Optional[AuditSession] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def relevant_tools(self) -> List[str]:
        return self._relevant_tools

    def get_session_id(self) -> str:
        if self._session:
            return self._session.get_session_id()
        return self._session_id

    async def pre_tool_execution_hook(
        self, context: Context, params: PreToolExecutionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

        if context.mode == AgentMode.RETURN_BYTES:
            raise RuntimeError(
                f"Unsupported hook: HolAuditTrailHook is available only in Agent Mode AUTONOMOUS. Stopping the agent execution before tool {method} is executed."
            )

    async def post_secondary_action_hook(
        self, _context: Context, params: PostSecondaryActionParams, method: str
    ) -> Any:
        if method not in self.relevant_tools:
            return

        try:
            if not self._session:
                writer = HolAuditWriter(params.client)
                self._session = AuditSession(writer, self._session_id)

            loggable_params = stringify_recursive(params.normalized_params)

            raw_result = {}
            human_message = None
            if hasattr(params.tool_result, "raw"):
                raw_result = stringify_recursive(params.tool_result.raw)
                if not isinstance(raw_result, dict):
                    raw_result = {}
            if hasattr(params.tool_result, "human_message"):
                human_message = params.tool_result.human_message

            entry = build_audit_entry(
                tool=method,
                params=loggable_params if isinstance(loggable_params, dict) else {},
                result={
                    "raw": raw_result,
                    "message": human_message,
                },
            )

            await self._session.write_entry(entry)
        except Exception as error:
            print(
                f"HolAuditTrailHook: Failed to log audit entry for tool {method}: {error}"
            )
