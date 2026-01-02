"""Utilities for building and executing ERC721 transfer operations via the Agent Kit.

This module exposes:
- transfer_erc721_prompt: Generate a prompt/description for the ERC721 transfer tool.
- transfer_erc721: Execute an ERC721 transfer transaction.
- TransferERC721Tool: Tool wrapper exposing the ERC721 transfer operation to the runtime.
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
    TransferERC721Parameters,
    ContractExecuteTransactionParametersNormalised,
)
from hedera_agent_kit.shared.strategies.tx_mode_strategy import (
    handle_transaction,
)
from hedera_agent_kit.shared.tool import Tool
from hedera_agent_kit.shared.utils import ledger_id_from_network
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)
from hedera_agent_kit.shared.utils.prompt_generator import PromptGenerator
from hedera_agent_kit.shared.constants.contracts import (
    ERC721_TRANSFER_FUNCTION_ABI,
    ERC721_TRANSFER_FUNCTION_NAME,
)


def transfer_erc721_prompt(context: Context = {}) -> str:
    """Generate a human-readable description of the transfer ERC721 tool."""
    context_snippet = PromptGenerator.get_context_snippet(context)
    from_address_desc = PromptGenerator.get_any_address_parameter_description(
        "from_address", context
    )
    usage_instructions = PromptGenerator.get_parameter_usage_instructions()
    scheduled_desc = PromptGenerator.get_scheduled_transaction_params_description(
        context
    )

    return f"""
{context_snippet}

This tool will transfer an existing ERC721 token on Hedera. ERC721 is an EVM compatible non-fungible token (NFT).

Use this tool ONLY when:
- The user explicitly mentions "ERC721" or "NFT" in the context of EVM contracts.
- The asset is identified by a Contract ID or EVM address.
- The user wants to transfer a specific token ID.

Do NOT use this tool for:
- Native Hedera Token Service (HTS) NFT transfers.
- Transferring tokens "on behalf of" another account (use the Allowance tool instead).

Parameters:
- contract_id (str, required): The id of the ERC721 contract. This can be the EVM address or the Hedera account id.
- {from_address_desc}
- to_address (str, required): The address to which the token will be transferred. This can be the EVM address or the Hedera account id.
- token_id (number, required): The ID of the transferred token.
- {scheduled_desc}

{usage_instructions}

Example: "Transfer ERC721 token 0.0.6486793 with id 0 from 0xd94...580b to 0.0.6486793"
Example: "Send NFT with token ID 5 from ERC721 contract 0.0.1234 to account 0.0.5678"
"""


def post_process(response: RawTransactionResponse) -> str:
    """Produce a human-readable summary for ERC721 transfer results."""
    if getattr(response, "schedule_id", None):
        return (
            f"Scheduled transfer of ERC721 successfully.\n"
            f"Transaction ID: {response.transaction_id}\n"
            f"Schedule ID: {response.schedule_id}"
        )
    return "ERC721 token transferred successfully."


async def transfer_erc721(
    client: Client,
    context: Context,
    params: TransferERC721Parameters,
) -> ToolResponse:
    """Execute ERC721 transfer transaction."""
    try:
        mirrornode_service = get_mirrornode_service(
            context.mirrornode_service, ledger_id_from_network(client.network)
        )

        normalised_params: ContractExecuteTransactionParametersNormalised = (
            await HederaParameterNormaliser.normalise_transfer_erc721_params(
                params,
                ERC721_TRANSFER_FUNCTION_ABI,
                ERC721_TRANSFER_FUNCTION_NAME,
                context,
                mirrornode_service,
                client,
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
        )

    except Exception as e:
        message = f"Failed to transfer ERC721: {str(e)}"
        print("[transfer_erc721_tool]", message)
        return ToolResponse(
            human_message=message,
            error=message,
        )


TRANSFER_ERC721_TOOL = "transfer_erc721_tool"


class TransferERC721Tool(Tool):
    """Tool wrapper exposing ERC721 transfer capability to the Agent runtime."""

    def __init__(self, context: Context):
        self.method: str = TRANSFER_ERC721_TOOL
        self.name: str = "Transfer ERC721 Token"
        self.description: str = transfer_erc721_prompt(context)
        self.parameters: type[TransferERC721Parameters] = TransferERC721Parameters
        self.outputParser = transaction_tool_output_parser

    async def execute(
        self, client: Client, context: Context, params: TransferERC721Parameters
    ) -> ToolResponse:
        return await transfer_erc721(client, context, params)
