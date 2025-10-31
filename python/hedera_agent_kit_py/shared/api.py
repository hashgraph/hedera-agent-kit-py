from __future__ import annotations
from typing import Any, List, Optional

from hiero_sdk_python import Client

from .configuration import Context
from .models import ToolResponse


class HederaAgentAPI:
    """Wrapper for executing tools against a Hedera client within a given context.

    This class allows invoking tools by method name and manages the
    Hedera client and execution context.
    """

    from .tool import Tool

    def __init__(
        self,
        client: Client,
        context: Optional[Context] = None,
        tools: Optional[List[Tool]] = None,
    ):
        """
        Initialize the HederaAgentAPI instance.

        Args:
            client (Client): An instance of the Hedera Client. Must be connected to a network.
            context (Optional[Context]): Optional execution context containing account info and services.
            tools (Optional[List[Tool]]): Optional list of Tool instances that can be executed.

        Raises:
            ValueError: If the client is not connected to a network.
        """
        if client.network is None:
            raise ValueError("Client must be connected to a network")
        self.client = client
        self.context = context or Context()
        self.tools = tools or []

    async def run(self, method: str, arg: Any) -> ToolResponse:
        """
        Execute a tool by its method name with the provided argument.

        Args:
            method (str): The method name of the tool to execute.
            arg (Any): Argument(s) to pass to the tool.

        Returns:
            ToolResponse: The result of the tool execution, typically JSON-serializable.

        Raises:
            ValueError: If the specified method does not match any registered tool.
        """
        tool = next((t for t in self.tools if t.method == method), None)
        if tool is None:
            raise ValueError(f"Invalid method {method}")

        return await tool.execute(self.client, self.context, arg)
