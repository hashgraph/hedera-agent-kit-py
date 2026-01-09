from typing import Any, List
from mcp.server.fastmcp import FastMCP
from hiero_sdk_python import Client
from hedera_agent_kit.shared.api import HederaAgentAPI
from hedera_agent_kit.shared.configuration import Configuration
from hedera_agent_kit.shared.tool_discovery import ToolDiscovery

class HederaMCPToolkit:
    def __init__(self, client: Client, configuration: Configuration):
        self.server = FastMCP("Hedera Agent Kit", dependencies=["hedera-agent-kit"])
        
        context = configuration.context
        tool_discovery = ToolDiscovery.create_from_configuration(configuration)
        all_tools = tool_discovery.get_all_tools(context, configuration)
        self._hedera_agent_kit = HederaAgentAPI(client, context, all_tools)

        for tool in all_tools:
            self._register_tool(tool)

    def _register_tool(self, tool):
        @self.server.tool(name=tool.method, description=tool.description)
        async def handler(**kwargs: Any) -> str:
            params = kwargs
            if "kwargs" in kwargs and len(kwargs) == 1 and isinstance(kwargs["kwargs"], dict):
                params = kwargs["kwargs"]
            result = await self._hedera_agent_kit.run(tool.method, params)
            return str(result)

    def run(self):
        """Run the MCP server (blocking)"""
        self.server.run(transport="stdio")
