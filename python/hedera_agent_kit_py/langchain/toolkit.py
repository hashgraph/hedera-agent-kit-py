from hiero_sdk_python import Client

from hedera_agent_kit_py import Configuration, Tool
from hedera_agent_kit_py.langchain.tool import HederaAgentKitTool
from hedera_agent_kit_py.shared import ToolDiscovery, HederaAgentAPI
from hedera_agent_kit_py.shared.configuration import Context


class HederaLangchainToolkit:
    """Wrapper to expose Hedera tools as LangChain-compatible tools.

    This class discovers all tools based on a configuration, creates a
    `HederaAgentAPI` instance for execution, and wraps each tool in a
    `HederaAgentKitTool` for LangChain compatibility.
    """

    def __init__(self, client: Client, configuration: Configuration):
        """
        Initialize the HederaLangchainToolkit.

        Args:
            client (Client): Hedera client instance connected to a network.
            configuration (Configuration): Configuration containing tools, plugins, and context.
        """
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
                name=tool.method, # langchain tools do not accept names with spaces
            )
            for tool in all_tools
        ]

    def get_tools(self) -> list[HederaAgentKitTool]:
        """
        Return all registered LangChain-compatible tools.

        Returns:
            list[HederaAgentKitTool]: List of tools wrapped for LangChain.
        """
        return self.tools

    def get_hedera_agentkit_api(self) -> HederaAgentAPI:
        """
        Return the underlying HederaAgentAPI instance.

        Returns:
            HederaAgentAPI: The API interface used by all tools.
        """
        return self._hedera_agentkit
