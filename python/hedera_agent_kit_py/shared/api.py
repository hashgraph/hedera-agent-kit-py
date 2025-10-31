from __future__ import annotations
from typing import Any, List, Optional
from hiero_sdk_python import Client
from .configuration import Context

from .models import ToolResponse


class HederaAgentAPI:
    """
    A wrapper for executing tools against a Hedera client within a given context.
    """

    from .tool import Tool

    def __init__(
        self,
        client: Client,
        context: Optional[Context] = None,
        tools: Optional[List[Tool]] = None,
    ):
        if client.network is None:
            raise ValueError("Client must be connected to a network")
        self.client = client
        self.context = context or Context()
        self.tools = tools or []

    async def run(self, method: str, arg: Any) -> ToolResponse:
        """
        Executes the specified tool by method name with the given argument.
        Returns a JSON-serialized string.
        """
        tool = next((t for t in self.tools if t.method == method), None)
        if tool is None:
            raise ValueError(f"Invalid method {method}")

        return await tool.execute(self.client, self.context, arg)
