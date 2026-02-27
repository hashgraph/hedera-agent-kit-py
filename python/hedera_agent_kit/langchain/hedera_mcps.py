from typing import List

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from hedera_agent_kit.shared.configuration import HederaMCPServer
from hedera_agent_kit.shared.mcp_configs import MCP_SERVER_CONFIGS


async def load_multiple_mcp_tools(
    server_names: List[HederaMCPServer],
) -> List[BaseTool]:
    """
    Loads tools from multiple MCP servers using langchain-mcp-adapters.
    """
    mcp_servers_config = {}

    for name in server_names:
        config = MCP_SERVER_CONFIGS.get(name)
        if not config:
            raise ValueError(f"Unknown MCP server: {name}")

        if config["type"] == "http":
            mcp_servers_config[name] = {
                "transport": "http",
                "url": config["url"],
            }
        elif config["type"] == "stdio":
            mcp_servers_config[name] = {
                "transport": "stdio",
                "command": config["command"],
                "args": config["args"],
                "env": config.get("env"),
            }

    client = MultiServerMCPClient(mcp_servers_config)

    tools = await client.get_tools()
    return tools
