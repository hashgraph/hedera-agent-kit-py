from hedera_agent_kit.plugins.core_evm_plugin.create_erc20 import (
    CreateERC20Tool,
    CREATE_ERC20_TOOL,
)
from hedera_agent_kit.plugins.core_evm_plugin.create_erc721 import (
    CreateERC721Tool,
    CREATE_ERC721_TOOL,
)
from hedera_agent_kit.plugins.core_evm_plugin.mint_erc721 import (
    MintERC721Tool,
    MINT_ERC721_TOOL,
)
from hedera_agent_kit.plugins.core_evm_plugin.transfer_erc20 import (
    TransferERC20Tool,
    TRANSFER_ERC20_TOOL,
)
from hedera_agent_kit.plugins.core_evm_plugin.transfer_erc20 import (
    TransferERC20Tool,
    TRANSFER_ERC20_TOOL,
)
from hedera_agent_kit.plugins.core_evm_plugin.create_erc721 import (
    CreateERC721Tool,
    CREATE_ERC721_TOOL,
)
from hedera_agent_kit.plugins.core_evm_plugin.transfer_erc721 import (
    TransferERC721Tool,
    TRANSFER_ERC721_TOOL,
)
from hedera_agent_kit.shared.plugin import Plugin

core_evm_plugin = Plugin(
    name="core-evm-plugin",
    version="1.0.0",
    description="A plugin for the EVM services",
    tools=lambda context: [
        CreateERC20Tool(context),
        TransferERC20Tool(context),
        CreateERC721Tool(context),
        MintERC721Tool(context),
        TransferERC721Tool(context),
    ],
)

core_evm_plugin_tool_names = {
    "CREATE_ERC20_TOOL": CREATE_ERC20_TOOL,
    "TRANSFER_ERC20_TOOL": TRANSFER_ERC20_TOOL,
    "CREATE_ERC721_TOOL": CREATE_ERC721_TOOL,
    "MINT_ERC721_TOOL": MINT_ERC721_TOOL,
    "TRANSFER_ERC721_TOOL": TRANSFER_ERC721_TOOL,
}

__all__ = [
    "core_evm_plugin",
    "core_evm_plugin_tool_names",
    CreateERC20Tool,
    TransferERC20Tool,
    CreateERC721Tool,
    MintERC721Tool,
    TransferERC721Tool,
]
