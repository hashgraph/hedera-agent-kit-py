"""ADK toolkit for exposing Hedera tools as Google ADK-compatible functions.

This module provides `HederaADKToolkit`, which discovers Hedera tools based on
a configuration and generates async Python functions that can be used directly
with Google ADK agents.
"""

from __future__ import annotations

from typing import Any, Callable, Coroutine, Dict, List

from hiero_sdk_python import Client

from hedera_agent_kit import Configuration, Tool
from hedera_agent_kit.adk.tool import create_adk_tool_function
from hedera_agent_kit.shared import ToolDiscovery, HederaAgentAPI
from hedera_agent_kit.shared.configuration import Context


# Type alias for ADK tool functions
ADKToolFunction = Callable[..., Coroutine[Any, Any, Dict[str, Any]]]


class HederaADKToolkit:
    """Wrapper to expose Hedera tools as Google ADK-compatible function tools.

    This class discovers all tools based on a configuration, creates a
    `HederaAgentAPI` instance for execution, and generates async Python
    functions for each tool that ADK can automatically wrap as FunctionTools.

    Example:
        ```python
        from google.adk.agents import Agent
        from hedera_agent_kit.adk import HederaADKToolkit

        toolkit = HederaADKToolkit(client, configuration)
        agent = Agent(
            model='gemini-2.0-flash',
            name='hedera_agent',
            tools=toolkit.get_tools(),  # Pass functions directly
        )
        ```
    """

    def __init__(self, client: Client, configuration: Configuration):
        """Initialize the HederaADKToolkit.

        Args:
            client: Hedera client instance connected to a network.
            configuration: Configuration containing tools, plugins, and context.
        """
        context: Context = configuration.context or {}

        # Discover tools based on configuration
        tool_discovery: ToolDiscovery = ToolDiscovery.create_from_configuration(
            configuration
        )
        all_tools: list[Tool] = tool_discovery.get_all_tools(context, configuration)

        # Create API wrapper
        self._hedera_agentkit = HederaAgentAPI(client, context, all_tools)

        # Generate ADK-compatible functions for each tool
        self._tools: List[ADKToolFunction] = [
            create_adk_tool_function(
                hedera_api=self._hedera_agentkit,
                tool=tool,
            )
            for tool in all_tools
        ]

    def get_tools(self) -> List[ADKToolFunction]:
        """Return all registered ADK-compatible tool functions.

        Returns:
            List of async functions that can be passed to an ADK Agent's tools list.
        """
        return self._tools

    def get_hedera_agentkit_api(self) -> HederaAgentAPI:
        """Return the underlying HederaAgentAPI instance.

        Returns:
            The API interface used by all tools.
        """
        return self._hedera_agentkit
