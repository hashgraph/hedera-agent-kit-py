"""Tool for minting a new ERC721 token (NFT) by executing a contract call.

This tool mirrors the structure of existing EVM tools (e.g., create_erc20)
and uses ContractExecuteTransaction to call the ERC721 contract's safeMint(to)
function on Hedera.
"""

from __future__ import annotations

from typing import cast

from hiero_sdk_python import Client
from hiero_sdk_python.transaction.transaction import Transaction

from hedera_agent_kit.shared.configuration import Context, AgentMode
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.hedera_utils.mirrornode import get_mirrornode_service
from hedera_agent_kit.shared.models import (
    ToolResponse,
    RawTransactionResponse,
    ExecutedTransactionToolResponse,
)
from hedera_agent_kit.shared.parameter_schemas import (
    MintERC721Parameters,
    ContractExecuteTransactionParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import handle_transaction
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator
from hedera_agent_kit.shared.utils import ledger_id_from_network


def mint_erc721_prompt(context: Context = {}) -> str:
    """Generate the tool prompt/description as provided in the issue."""
    context_snippet = PromptGenerator.get_context_snippet(context)
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()
    to_address_desc = PromptGenerator.get_any_address_parameter_description(
        "to_address", context, is_required=False
    )

    return f"""
{context_snippet}

This tool will mint a new ERC721 token on Hedera. ERC721 is an EVM compatible non fungible token (NFT).

Parameters:
- contract_id (str, required): The id of the ERC721 contract
- {to_address_desc}
{PromptGenerator.get_scheduled_transaction_params_description(context)}

{usage_instructions}

Example: "Mint ERC721 token 0.0.6486793 to 0xd94dc7f82f103757f715514e4a37186be6e4580b" means minting the ERC721 token with contract_id 0.0.6486793 to the 0xd94dc7f82f103757f715514e4a37186be6e4580b EVM address.
Example: "Mint ERC721 token 0.0.6486793 to Hedera account ID 0.0.2222222" means minting the ERC721 token with contract_id 0.0.6486793 to the Hedera account ID 0.0.2222222.
Example: "Mint ERC721 token 0.0.1234 to Hedera account ID 0.0.5678" means minting the ERC721 token with contract_id 0.0.1234 to the Hedera account ID 0.0.5678.
Example: "Mint ERC721 token 0.0.9999" means minting the ERC721 token with contract_id 0.0.9999 to the default account as per the context.

NOTE: the 'to_address' parameter is optional. If not provided, the minting will be performed to the default account as per the context.
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for ERC721 mint results."""
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled mint of ERC721 successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return (
        f"ERC721 token minted successfully.\nTransaction ID: {response.transaction_id}"
    )


async def mint_erc721(
    client: Client,
    context: Context,
    params: MintERC721Parameters,
) -> ToolResponse:
    """Execute ERC721 mint transaction by calling safeMint(to) on the contract."""
    try:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )
        normalised_params: ContractExecuteTransactionParametersNormalised = (
            await HederaParameterNormaliser.normalise_mint_erc721_params(
                params, context, mirrornode_service, client
            )
        )

        tx: Transaction = HederaBuilder.execute_transaction(normalised_params)
        result = await handle_transaction(tx, client, context)

        if context.mode == AgentMode.RETURN_BYTES:
            return result

        raw_tx_data = cast(ExecutedTransactionToolResponse, result).raw
        human_message = post_process(raw_tx_data)

        return ExecutedTransactionToolResponse(
            human_message=human_message,
            raw=raw_tx_data,
            extra={"raw": raw_tx_data},
        )

    except Exception as e:
        message = f"Failed to mint ERC721 token: {str(e)}"
        print("[mint_erc721_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


MINT_ERC721_TOOL = "mint_erc721_tool"


class MintERC721Tool(Tool):
    """Tool wrapper exposing ERC721 mint capability to the Agent runtime."""

    def __init__(self, context: Context):
        self.method: str = MINT_ERC721_TOOL
        self.name: str = "Mint ERC721"
        self.description: str = mint_erc721_prompt(context)
        self.parameters: type[MintERC721Parameters] = MintERC721Parameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: MintERC721Parameters
    ) -> ToolResponse:
        return await mint_erc721(client, context, params)
