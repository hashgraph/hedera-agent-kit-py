"""ADK tool wrapper for exposing Hedera Agent Kit tools.

This module provides a HederaAdkTool class that subclasses Google ADK's BaseTool,
building a FunctionDeclaration directly from the Pydantic schema. This gives full
control over nested types, field descriptions, and required/optional fields — without
relying on ADK's function introspection heuristics.
"""

from __future__ import annotations

from typing import (
    Any,
    Dict,
)

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types
from pydantic import BaseModel

from hedera_agent_kit import HederaAgentAPI
from hedera_agent_kit.shared import Tool
from hedera_agent_kit.shared.models import ToolResponse


class HederaAdkTool(BaseTool):
    """Google ADK BaseTool wrapper for a Hedera Agent Kit tool.

    Builds the FunctionDeclaration directly from the tool's Pydantic parameter
    schema, preserving:
    - Nested model structures (e.g. List[TransferHbarEntry])
    - Field descriptions from Field(description=...)
    - Required vs optional distinction
    - Recursive nesting (models inside models)
    """

    def __init__(self, hedera_api: HederaAgentAPI, tool: Tool) -> None:
        super().__init__(name=tool.method, description=tool.description)
        self._hedera_api = hedera_api
        self._tool = tool
        self._schema = tool.parameters
        self._declaration = self._get_declaration()

    # ADK calls this to get the FunctionDeclaration sent to Gemini
    def _get_declaration(self) -> genai_types.FunctionDeclaration:
        return genai_types.FunctionDeclaration(
            name=self._tool.method,
            description=self._tool.description,
            parameters_json_schema=self._schema.model_json_schema(),
        )

    async def run_async(
        self,
        *,
        args: Dict[str, Any],
        tool_context: ToolContext,
    ) -> Dict[str, Any]:
        """Execute the Hedera tool, coercing raw ADK args through Pydantic first."""
        # Coerce plain dicts / primitives from Gemini into validated Pydantic model
        validated: BaseModel = self._schema.model_validate(args)
        result: ToolResponse = await self._hedera_api.run(
            self._tool.method, validated.model_dump()
        )
        return result.to_dict()
