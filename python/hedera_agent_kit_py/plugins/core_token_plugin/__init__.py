from hedera_agent_kit_py.plugins.core_token_plugin.create_fungible_token import (
    CreateFungibleTokenTool,
    CREATE_FUNGIBLE_TOKEN_TOOL,
)
from hedera_agent_kit_py.shared.plugin import Plugin

core_token_plugin = Plugin(
    name="core-token-plugin",
    version="1.0.0",
    description="A plugin for the HTS service",
    tools=lambda context: [
        CreateFungibleTokenTool(context),
    ],
)

core_token_plugin_tool_names = {
    "CREATE_FUNGIBLE_TOKEN_TOOL": CREATE_FUNGIBLE_TOKEN_TOOL
}

__all__ = [
    "CreateFungibleTokenTool",
    "core_token_plugin",
    "core_token_plugin_tool_names",
]
