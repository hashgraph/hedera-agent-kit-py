from hedera_agent_kit.plugins.core_token_plugin.create_fungible_token import (
    CreateFungibleTokenTool,
    CREATE_FUNGIBLE_TOKEN_TOOL,
)
from .associate_token import (
    AssociateTokenTool,
    ASSOCIATE_TOKEN_TOOL,
)
from .create_non_fungible_token import (
    CreateNonFungibleTokenTool,
    CREATE_NON_FUNGIBLE_TOKEN_TOOL,
)
from .mint_fungible_token import MintFungibleTokenTool, MINT_FUNGIBLE_TOKEN_TOOL

from .mint_non_fungible_token import (
    MintNonFungibleTokenTool,
    MINT_NON_FUNGIBLE_TOKEN_TOOL,
)

from hedera_agent_kit.plugins.core_token_plugin.dissociate_token import (
    DissociateTokenTool,
    DISSOCIATE_TOKEN_TOOL,
)
from hedera_agent_kit.plugins.core_token_plugin.transfer_fungible_token_with_allowance import (
    TransferFungibleTokenWithAllowanceTool,
    TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL,
)
from hedera_agent_kit.plugins.core_token_plugin.airdrop_fungible_token import (
    AirdropFungibleTokenTool,
    AIRDROP_FUNGIBLE_TOKEN_TOOL,
)
from hedera_agent_kit.plugins.core_token_plugin.delete_token_allowance import (
    DeleteTokenAllowanceTool,
    DELETE_TOKEN_ALLOWANCE_TOOL,
)
from hedera_agent_kit.plugins.core_token_plugin.transfer_non_fungible_token_with_allowance import (
    TransferNftWithAllowanceTool,
    TRANSFER_NFT_WITH_ALLOWANCE_TOOL,
)
from .transfer_non_fungible_token import (
    TransferNonFungibleTokenTool,
    TRANSFER_NON_FUNGIBLE_TOKEN_TOOL,
)
from hedera_agent_kit.plugins.core_token_plugin.delete_non_fungible_token_allowance import (
    DeleteNonFungibleTokenAllowanceTool,
    DELETE_NON_FUNGIBLE_TOKEN_ALLOWANCE_TOOL,
)
from hedera_agent_kit.shared.plugin import Plugin

core_token_plugin = Plugin(
    name="core-token-plugin",
    version="1.0.0",
    description="A plugin for the Hedera Token Service",
    tools=lambda context: [
        CreateFungibleTokenTool(context),
        AssociateTokenTool(context),
        MintFungibleTokenTool(context),
        DissociateTokenTool(context),
        AirdropFungibleTokenTool(context),
        CreateNonFungibleTokenTool(context),
        MintNonFungibleTokenTool(context),
        TransferFungibleTokenWithAllowanceTool(context),
        TransferNftWithAllowanceTool(context),
        TransferNonFungibleTokenTool(context),
        DeleteTokenAllowanceTool(context),
        DeleteNonFungibleTokenAllowanceTool(context),
    ],
)

core_token_plugin_tool_names = {
    "CREATE_FUNGIBLE_TOKEN_TOOL": CREATE_FUNGIBLE_TOKEN_TOOL,
    "ASSOCIATE_TOKEN_TOOL": ASSOCIATE_TOKEN_TOOL,
    "MINT_FUNGIBLE_TOKEN_TOOL": MINT_FUNGIBLE_TOKEN_TOOL,
    "DISSOCIATE_TOKEN_TOOL": DISSOCIATE_TOKEN_TOOL,
    "CREATE_NON_FUNGIBLE_TOKEN_TOOL": CREATE_NON_FUNGIBLE_TOKEN_TOOL,
    "TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL": TRANSFER_FUNGIBLE_TOKEN_WITH_ALLOWANCE_TOOL,
    "TRANSFER_NFT_WITH_ALLOWANCE_TOOL": TRANSFER_NFT_WITH_ALLOWANCE_TOOL,
    "TRANSFER_NON_FUNGIBLE_TOKEN_TOOL": TRANSFER_NON_FUNGIBLE_TOKEN_TOOL,
    "AIRDROP_FUNGIBLE_TOKEN_TOOL": AIRDROP_FUNGIBLE_TOKEN_TOOL,
    "DELETE_TOKEN_ALLOWANCE_TOOL": DELETE_TOKEN_ALLOWANCE_TOOL,
    "MINT_NON_FUNGIBLE_TOKEN_TOOL": MINT_NON_FUNGIBLE_TOKEN_TOOL,
    "DELETE_NON_FUNGIBLE_TOKEN_ALLOWANCE_TOOL": DELETE_NON_FUNGIBLE_TOKEN_ALLOWANCE_TOOL,
}

__all__ = [
    "CreateFungibleTokenTool",
    "AssociateTokenTool",
    "DissociateTokenTool",
    "MintFungibleTokenTool",
    "AirdropFungibleTokenTool",
    "CreateNonFungibleTokenTool",
    "MintNonFungibleTokenTool",
    "TransferFungibleTokenWithAllowanceTool",
    "TransferNftWithAllowanceTool",
    "TransferNonFungibleTokenTool",
    "DeleteTokenAllowanceTool",
    "DeleteNonFungibleTokenAllowanceTool",
    "core_token_plugin",
    "core_token_plugin_tool_names",
]
