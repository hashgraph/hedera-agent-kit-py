from typing import Any, List, Optional
from hiero_sdk_python import Client
from .configuration import Context
from .tool import Tool
import json


class HederaAgentAPI:
    """
    A wrapper for executing tools against a Hedera client within a given context.
    """

    def __init__(
        self,
        client: Client,
        context: Optional[Context] = None,
        tools: Optional[List[Tool]] = None,
    ):
        self.client = client
        if self.client.network is None:
            raise ValueError("Client must be connected to a network")
        self.context = context or Context()
        self.tools = tools or []

    async def run(self, method: str, arg: Any) -> str:
        """
        Executes the specified tool by method name with the given argument.
        Returns the JSON-serialized output.
        """
        tool = next((t for t in self.tools if t.method == method), None)
        if tool is None:
            raise ValueError(f"Invalid method {method}")
        output = await tool.execute(self.client, self.context, arg)
        return json.dumps(output)
