from hedera_agent_kit_py.shared.plugin import Plugin
from .mint_fungible_token import MintFungibleTokenTool, MINT_FUNGIBLE_TOKEN_TOOL

core_token_plugin = Plugin(
    name="core-token-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Token Service",
    tools=lambda context: [
        MintFungibleTokenTool(context),
    ],
)

core_token_plugin_tool_names = {
    "MINT_FUNGIBLE_TOKEN_TOOL": MINT_FUNGIBLE_TOKEN_TOOL,
}

__all__ = [
    "core_token_plugin",
    "core_token_plugin_tool_names",
    "MintFungibleTokenTool",
]
