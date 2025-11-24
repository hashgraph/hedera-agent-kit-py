from hedera_agent_kit_py.plugins.core_token_plugin.create_fungible_token import (
    CreateFungibleTokenTool,
    CREATE_FUNGIBLE_TOKEN_TOOL,
)
from .associate_token import (
    AssociateTokenTool,
    ASSOCIATE_TOKEN_TOOL,
)

from .mint_fungible_token import MintFungibleTokenTool, MINT_FUNGIBLE_TOKEN_TOOL

from hedera_agent_kit_py.plugins.core_token_plugin.dissociate_token import (
    DissociateTokenTool,
    DISSOCIATE_TOKEN_TOOL,
)
from hedera_agent_kit_py.shared.plugin import Plugin

core_token_plugin = Plugin(
    name="core-token-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Token Service",
    tools=lambda context: [
        CreateFungibleTokenTool(context),
        AssociateTokenTool(context),
        MintFungibleTokenTool(context),
        DissociateTokenTool(context),
    ],
)

core_token_plugin_tool_names = {
    "CREATE_FUNGIBLE_TOKEN_TOOL": CREATE_FUNGIBLE_TOKEN_TOOL,
    "ASSOCIATE_TOKEN_TOOL": ASSOCIATE_TOKEN_TOOL,
    "MINT_FUNGIBLE_TOKEN_TOOL": MINT_FUNGIBLE_TOKEN_TOOL,
    "DISSOCIATE_TOKEN_TOOL": DISSOCIATE_TOKEN_TOOL,
}

__all__ = [
    "CreateFungibleTokenTool",
    "AssociateTokenTool",
    "DissociateTokenTool",
    "MintFungibleTokenTool",
    "core_token_plugin",
    "core_token_plugin_tool_names",
]
