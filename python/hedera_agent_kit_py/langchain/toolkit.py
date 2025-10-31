from hiero_sdk_python import Client

from hedera_agent_kit_py import Configuration, Tool
from hedera_agent_kit_py.langchain.tool import HederaAgentKitTool
from hedera_agent_kit_py.shared import ToolDiscovery, HederaAgentAPI
from hedera_agent_kit_py.shared.configuration import Context


class HederaLangchainToolkit:

    def __init__(self, client: Client, configuration: Configuration):
        context: Context = configuration.context or {}

        # Discover tools based on configuration
        tool_discovery: ToolDiscovery = ToolDiscovery.create_from_configuration(
            configuration
        )
        all_tools: list[Tool] = tool_discovery.get_all_tools(context, configuration)

        # Create API wrapper and LangChain-compatible tools
        self._hedera_agentkit = HederaAgentAPI(client, context, all_tools)
        self.tools: list[HederaAgentKitTool] = [
            HederaAgentKitTool(
                hedera_api=self._hedera_agentkit,
                method=tool.method,
                description=tool.description,
                schema=tool.parameters,
                name=tool.name,
            )
            for tool in all_tools
        ]

    def get_tools(self) -> list[HederaAgentKitTool]:
        """Return all registered LangChain-compatible tools."""
        return self.tools

    def get_hedera_agentkit_api(self) -> HederaAgentAPI:
        """Return the API interface."""
        return self._hedera_agentkit
