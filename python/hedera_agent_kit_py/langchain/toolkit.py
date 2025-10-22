from typing import List, Any

from hedera_agent_kit_py import Configuration
from hedera_agent_kit_py.langchain.tool import HederaAgentKitTool
from hedera_agent_kit_py.shared import ToolDiscovery, HederaAgentAPI


class HederaLangchainToolkit:

    def __init__(self, client: Any, configuration: Configuration):
        context = configuration.context or {}

        # Discover tools based on configuration
        tool_discovery = ToolDiscovery.create_from_configuration(configuration)
        all_tools = tool_discovery.get_all_tools(context, configuration)

        # Create API wrapper and LangChain-compatible tools
        self._hedera_agentkit = HederaAgentAPI(client, context, all_tools)
        self.tools: List[HederaAgentKitTool] = [
            HederaAgentKitTool(
                hedera_api=self._hedera_agentkit,
                method=tool.method,
                description=tool.description,
                schema=tool.parameters,
            )
            for tool in all_tools
        ]

    def get_tools(self) -> List[HederaAgentKitTool]:
        """Return all registered LangChain-compatible tools."""
        return self.tools

    def get_hedera_agentkit_api(self) -> HederaAgentAPI:
        """Return the API interface."""
        return self._hedera_agentkit
