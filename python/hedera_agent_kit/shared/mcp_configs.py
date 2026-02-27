from typing import TypedDict, Optional, Dict
import os

from hedera_agent_kit.shared.configuration import HederaMCPServer


class MCPServerConfigSTDIO(TypedDict):
    type: str
    command: str
    args: list[str]
    env: Optional[Dict[str, str]]


class MCPServerConfigHTTP(TypedDict):
    type: str
    url: str


MCPServerConfig = MCPServerConfigSTDIO | MCPServerConfigHTTP

MCP_SERVER_CONFIGS: Dict[HederaMCPServer, MCPServerConfig] = {
    HederaMCPServer.HEDERION_MCP_MAINNET: MCPServerConfigHTTP(
        type="http",
        url="https://hederion.com/mcp",
    ),
    HederaMCPServer.HGRAPH_MCP_MAINNET: MCPServerConfigHTTP(
        type="http",
        url=f"https://mainnet.hedera.api.hgraph.io/v1/{os.environ.get('HGRAPH_API_KEY', '')}/mcp",
    ),
}
