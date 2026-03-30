from __future__ import annotations

from enum import Enum
from typing import Optional, List

from .hedera_utils.mirrornode.hedera_mirrornode_service_interface import (
    IHederaMirrornodeService,
)

if False:  # TYPE_CHECKING
    from hedera_agent_kit.hooks.abstract_hook import AbstractHook


class AgentMode(str, Enum):
    """Enumeration representing the agent execution mode."""

    AUTONOMOUS = "autonomous"
    """The agent executes transactions automatically."""

    RETURN_BYTES = "returnBytes"
    """The agent returns raw transaction bytes instead of executing."""


class Context:
    """Represents the runtime context for the agent, including account info and services."""

    def __init__(
        self,
        account_id: Optional[str] = None,
        account_public_key: Optional[str] = None,
        mode: Optional[AgentMode] = None,
        mirrornode_service: Optional[IHederaMirrornodeService] = None,
        hooks: Optional[List[AbstractHook]] = None,
    ):
        """
        Args:
            account_id (Optional[str]): The connected Hedera account ID for the agent.
            account_public_key (Optional[str]): The public key for the account. If not provided,
                it may be fetched based on `account_id`.
            mode (Optional[AgentMode]): Execution mode of the agent (AUTONOMOUS or RETURN_BYTES).
            mirrornode_service (Optional[IHederaMirrornodeService]): Optional service for
                interacting with Hedera Mirror Node.
            hooks (Optional[List[AbstractHook]]): List of hooks to enforce.
        """
        # Account is a Connected Account ID.
        self.account_id = account_id

        # Account Public Key is either passed in configuration or fetched based on the passed accountId
        self.account_public_key = account_public_key

        # Defines if the agent executes the transactions or returns the raw transaction bytes
        self.mode = mode

        # Mirrornode service
        self.mirrornode_service = mirrornode_service

        # Hooks
        self.hooks = hooks or []


class HederaMCPServer(str, Enum):
    """Enumeration of preconfigured Hedera MCP servers."""

    HEDERION_MCP_MAINNET = "HEDERION_MCP_MAINNET"
    HGRAPH_MCP_MAINNET = "HGRAPH_MCP_MAINNET"


class Configuration:
    """Represents the agent configuration, including tools, plugins, and runtime context."""

    from .plugin import Plugin

    def __init__(
        self,
        tools: Optional[List[str]] = None,
        plugins: Optional[List[Plugin]] = None,
        context: Optional[Context] = None,
        mcp_servers: Optional[List[HederaMCPServer]] = None,
    ):
        """
        Args:
            tools (Optional[List[str]]): List of tools to enable for the agent. If None or empty,
                all tools are considered enabled.
            plugins (Optional[List[Plugin]]): External plugins to load.
            context (Optional[Context]): Runtime context containing account info and services.
            mcp_servers (Optional[List[HederaMCPServer]]): List of MCP servers to connect to.
        """
        self.tools = tools  # If empty, all tools will be used.
        self.plugins = plugins  # External plugins to load.
        self.context = context
        self.mcp_servers = mcp_servers
